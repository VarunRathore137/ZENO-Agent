# zeno/__main__.py
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from zeno.logging_setup import configure_logging
import os
configure_logging(debug=os.environ.get("ZENO_DEBUG", "").lower() in ("1", "true"))

import asyncio
import queue
import sys
import threading
import time
import logging
import numpy as np
from pathlib import Path

from zeno.api.server import ZenoDaemonAPI
from zeno.monitor.ws_server import BrowserWebSocketServer
from zeno.voice.hotkeys import create_listener
from zeno.voice.capture import MicrophoneStream
from zeno.voice.wake_word import create_detector, ZENO_WAKE_PHRASES, _matches_transcript
from zeno.voice.transcriber import WhisperTranscriber
from zeno.nlp.classifier import get_classifier
from zeno.dispatcher.router import dispatch

"""ZENO entry point."""

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# TTS — dedicated thread with its own pyttsx3 engine.
#
# pyttsx3 on Windows uses COM (Component Object Model) objects.  COM objects
# must be used from the thread that called CoInitialize().  Calling pyttsx3
# from a generic daemon thread (like ZenoVoiceLoop) causes silent failures or
# "CoInitialize has not been called" errors.
#
# Fix: a single TTS thread owns the engine for its entire lifetime.  _speak()
# just enqueues text; the thread drains the queue and calls runAndWait().
# ---------------------------------------------------------------------------
_tts_queue: queue.Queue = queue.Queue()
_tts_ready  = threading.Event()


def _tts_worker() -> None:
    """Long-lived TTS thread.  Owns the pyttsx3 engine for its lifetime."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        _tts_ready.set()
        logger.info("TTS worker ready (pyttsx3 engine initialised in dedicated thread)")
    except Exception as e:
        logger.warning("TTS unavailable: %s", e)
        _tts_ready.set()   # unblock callers even if TTS failed
        return

    while True:
        try:
            text = _tts_queue.get(timeout=1.0)
            if text is None:   # sentinel: shut down
                break
            engine.say(text)
            engine.runAndWait()
        except queue.Empty:
            pass
        except Exception as e:
            logger.warning("TTS error (non-fatal): %s", e)


# Start the TTS thread immediately at module load so the engine is warm
# before the first voice command arrives.
_tts_thread = threading.Thread(target=_tts_worker, daemon=True, name="ZenoTTS")
_tts_thread.start()


def _speak(text: str) -> None:
    """Enqueue text for the dedicated TTS thread.  Non-blocking."""
    if text:
        _tts_queue.put(text)



# ---------------------------------------------------------------------------
# Gemini conversational fallback
# Called when NLP fuzzy-match finds no structured intent.
# Enables: jokes, greetings, open-ended questions, engineering Q&A.
# ---------------------------------------------------------------------------
_ZENO_SYSTEM_PROMPT = (
    "You are ZENO, a smart personal AI assistant for a software engineer. "
    "You are concise, friendly, and helpful. Keep responses under 3 sentences for voice output. "
    "You can answer questions, tell jokes, have casual conversations, and assist with engineering tasks. "
    "If the user asks you to do something that requires a structured voice command (like open apps "
    "or manage tasks), tell them the exact phrase they should say to ZENO instead."
)


_gemini_client = None   # module-level cache to avoid re-init on each call

def _gemini_converse(user_text: str) -> str:
    """
    Call Gemini synchronously from the VoiceLoop background thread.

    The google-genai SDK's generate_content() is already a blocking HTTP call —
    it does NOT need an asyncio event loop.  Wrapping it in asyncio.run() inside
    a daemon thread caused "source code string cannot contain null bytes" on
    Windows because the SDK internally calls asyncio.get_event_loop(), which
    conflicts with the thread's event loop state under Python 3.12.
    """
    global _gemini_client
    try:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        if _gemini_client is None:
            from google import genai  # type: ignore[import]
            _gemini_client = genai.Client(api_key=api_key)

        # Build a single prompt string — Gemini 1.5 Flash handles system +
        # user content in one string perfectly fine for short voice replies.
        prompt = (
            f"System instruction: {_ZENO_SYSTEM_PROMPT}\n\n"
            f"User: {user_text}"
        )
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return (response.text or "").strip()

    except Exception as e:
        logger.warning("Gemini fallback error: %s", e)
        return "I heard you, but I ran into a hiccup reaching Gemini. Try again in a moment."



# ---------------------------------------------------------------------------
# VoiceLoop
#
# Dual-path wake detection:
#
#   Path A (acoustic, fast):
#     ZenoMicPump  -->  wake_queue  -->  WakeWordDetector (alexa model)
#                                          --> ZenoAcousticBridge sets _wake_event
#
#   Path B (transcript, reliable for "Hey Zeno"):
#     ZenoVadScanner reads mic every 2.5 s, transcribes with Whisper-tiny,
#     checks _matches_transcript() --> sets _wake_event if matched
#
#   Main loop blocks on _wake_event.wait(), then:
#     collect 6 s command audio --> Whisper-base STT
#       --> IntentClassifier (fuzzy NLP)
#             hit  --> dispatcher.dispatch() --> _speak()
#             miss --> _gemini_converse()    --> _speak()
# ---------------------------------------------------------------------------

class VoiceLoop:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._wake_event = threading.Event()

    def _run(self) -> None:
        logger.info("VoiceLoop: initialising components...")

        # Whisper base -- full-quality command transcription
        try:
            transcriber = WhisperTranscriber(model_name="base")
        except Exception as e:
            logger.error("VoiceLoop: could not load Whisper base -- voice disabled: %s", e)
            return

        # Whisper tiny -- fast wake-phrase scanning in VAD thread
        try:
            tiny_transcriber = WhisperTranscriber(model_name="tiny")
        except Exception as e:
            logger.warning("VoiceLoop: Whisper tiny unavailable, using base for VAD scan: %s", e)
            tiny_transcriber = transcriber

        # Acoustic wake-word detector
        detector = create_detector()

        # NLP classifier
        classifier = get_classifier()

        # Microphone
        logger.info("VoiceLoop: opening microphone...")
        try:
            mic = MicrophoneStream()
            mic.start()
        except Exception as e:
            logger.error("VoiceLoop: could not open microphone -- voice disabled: %s", e)
            return

        # ------------------------------------------------------------------
        # Subscribe each consumer to the mic fan-out.
        # Every frame the mic captures is delivered to ALL queues.
        # No frame-stealing race conditions.
        # ------------------------------------------------------------------
        wake_queue = mic.subscribe()        # for the acoustic wake-word detector
        vad_queue  = mic.subscribe()        # for the Whisper-tiny VAD scanner
        cmd_queue  = mic.subscribe()        # for command audio after wake fires

        detector.start(wake_queue)

        # -- Bridge: acoustic model fires -> set shared wake_event --
        def _acoustic_bridge() -> None:
            while not self._stop.is_set():
                if detector.wait_for_wake(timeout=1.0):
                    logger.info("VoiceLoop: acoustic model triggered")
                    detector.detected.clear()
                    self._wake_event.set()

        threading.Thread(target=_acoustic_bridge, daemon=True, name="ZenoAcousticBridge").start()

        # -- Thread 2: ZenoVadScanner --
        # Every ~2.5 s, grabs a clip and checks it for ZENO wake phrases via Whisper-tiny.
        # Uses webrtcvad to distinguish real speech from background noise by analysing
        # speech frequency patterns (formants/harmonics) — NOT volume levels.
        # This is necessary because this mic's DSP normalises all audio to similar RMS.
        VAD_CLIP_SECS    = 1.5    # shorter window = faster detection
        WEBRTC_VAD_MODE  = 2      # 0=least aggressive, 3=most aggressive
                                  # Mode 2 is much better for laptop mics with DSP/AGC
                                  # (mode 1 was firing on keyboard noise and ambient audio)
        SPEECH_FRAME_MIN = 6      # need ≥6 CONSECUTIVE speech frames (~120ms of real speech)
                                  # Was 4 — too low, caught keyboard clatter and TV noise

        # Initialise webrtcvad — fall back to RMS if unavailable
        _webrtc_vad = None
        try:
            import webrtcvad
            _webrtc_vad = webrtcvad.Vad(WEBRTC_VAD_MODE)
            logger.info("VoiceLoop: webrtcvad loaded (mode=%d)", WEBRTC_VAD_MODE)
        except Exception as e:
            logger.warning("VoiceLoop: webrtcvad unavailable (%s) — falling back to RMS gating", e)

        def _has_speech_webrtc(audio_f32: np.ndarray) -> bool:
            """Return True if webrtcvad detects SPEECH_FRAME_MIN consecutive speech frames."""
            # webrtcvad needs int16 PCM at 16kHz in exact 10/20/30ms frames
            FRAME_MS      = 20                   # 20 ms frames
            FRAME_SAMPLES = 16000 * FRAME_MS // 1000   # = 320 samples
            pcm = (np.clip(audio_f32, -1.0, 1.0) * 32767).astype(np.int16)
            speech_count = 0
            for i in range(0, len(pcm) - FRAME_SAMPLES, FRAME_SAMPLES):
                frame_bytes = pcm[i:i + FRAME_SAMPLES].tobytes()
                try:
                    if _webrtc_vad.is_speech(frame_bytes, 16000):
                        speech_count += 1
                        if speech_count >= SPEECH_FRAME_MIN:
                            return True
                    else:
                        speech_count = 0  # reset — require CONSECUTIVE frames
                except Exception:
                    pass
            return False

        def _vad_scanner() -> None:
            while not self._stop.is_set():
                # Don't scan while a command is already being processed
                if self._wake_event.is_set():
                    time.sleep(0.2)
                    continue

                frames: list[np.ndarray] = []
                deadline = time.monotonic() + VAD_CLIP_SECS
                while time.monotonic() < deadline and not self._stop.is_set():
                    try:
                        frame = vad_queue.get(timeout=0.1)
                        frames.append(frame)
                    except queue.Empty:
                        pass

                if not frames:
                    continue

                clip = np.concatenate(frames)

                # Gate: must pass speech detection before hitting Whisper
                if _webrtc_vad is not None:
                    if not _has_speech_webrtc(clip):
                        continue  # no speech patterns detected — skip Whisper call
                else:
                    # Fallback: plain RMS gate (less accurate)
                    # 0.003 is 10x tighter than the old value — prevents Intel Smart Sound
                    # mic's AGC from normalizing keyboard noise up to voice levels
                    if float(np.sqrt(np.mean(clip ** 2))) < 0.003:
                        continue

                try:
                    # initial_prompt biases Whisper vocabulary toward wake phrases,
                    # reducing mis-transcriptions like "you know" instead of "Zeno"
                    text = tiny_transcriber.transcribe(
                        clip,
                        initial_prompt="Hey Zeno, Okay Zeno, Hi Zen, Hello Zeno, Hey Zen",
                    )
                except Exception:
                    continue

                # Drain frames that piled up in vad_queue during inference.
                # Whisper-tiny takes 1-3s on CPU. Without draining, the next
                # 2.5s collection window immediately fills with stale audio,
                # compounding detection latency to 6-7s per attempt.
                drained = 0
                while True:
                    try:
                        vad_queue.get_nowait()
                        drained += 1
                    except queue.Empty:
                        break
                if drained > 0:
                    logger.debug("VAD: drained %d stale frames after inference", drained)

                if not text:
                    continue

                logger.debug("VoiceLoop VAD scan: %r", text)

                if _matches_transcript(text):
                    logger.info("VoiceLoop: transcript wake matched --> %r", text)
                    print(f"[ZENO] Wake phrase detected: {text!r}", flush=True)
                    self._wake_event.set()

        threading.Thread(target=_vad_scanner, daemon=True, name="ZenoVadScanner").start()

        logger.info(
            "VoiceLoop: ready. Wake phrases: %s ...",
            ", ".join(f'"{p}"' for p in ZENO_WAKE_PHRASES[:4]),
        )
        print(
            "[ZENO] Listening for wake word...\n"
            "       Say: 'Hey Zeno', 'Okay Zeno', 'Hi Zen', or 'Hello Zeno'",
            flush=True,
        )

        try:
            while not self._stop.is_set():

                # STAGE 1: wait for wake (either path)
                if not self._wake_event.wait(timeout=1.0):
                    continue

                self._wake_event.clear()
                _broadcast_state("listening")
                # Audio feedback: user MUST hear this to know when to speak.
                # Without it, they keep repeating the wake phrase (no idea it fired).
                _speak("Ready!")
                print("[ZENO] 🔊 Ready — listening for your command...", flush=True)
                logger.info("VoiceLoop: wake confirmed -- collecting command audio...")

                # Drain stale frames from cmd_queue (accumulated during the 1.5s
                # VAD window + Whisper inference).  These are pre-wake audio we
                # don't want to include in the command clip.  We drain BEFORE the
                # patience window so the 3s budget counts fresh audio only.
                drained = 0
                while True:
                    try:
                        cmd_queue.get_nowait()
                        drained += 1
                    except queue.Empty:
                        break
                if drained:
                    logger.debug("cmd_queue: drained %d stale pre-wake frames", drained)

                # STAGE 2: Give 3 s patience — longer than before so the user
                # has time to hear the "Ready!" TTS prompt and start speaking.
                COMMAND_SECS      = 6.0
                PATIENCE_BEFORE   = 3.0   # wait up to 3 s for speech to start
                SILENCE_AFTER     = 1.0   # stop after 1 s of trailing silence
                chunks: list[np.ndarray] = []
                deadline          = time.monotonic() + COMMAND_SECS
                speech_started    = False
                silent_for        = 0.0

                while time.monotonic() < deadline:
                    try:
                        frame = cmd_queue.get(timeout=0.15)
                        if frame.size > 0:
                            is_speech = float(np.sqrt(np.mean(frame ** 2))) >  0.0003
                            if is_speech:
                                chunks.append(frame)
                                speech_started = True
                                silent_for = 0.0
                            elif speech_started:
                                # trailing silence after speech — count toward budget
                                chunks.append(frame)   # keep for Whisper context
                                silent_for += 0.15
                                if silent_for >= SILENCE_AFTER:
                                    break
                            else:
                                # pre-speech silence — burn the patience budget
                                silent_for += 0.15
                                if silent_for >= PATIENCE_BEFORE:
                                    break  # user never started speaking
                    except queue.Empty:
                        silent_for += 0.15
                        if speech_started and silent_for >= SILENCE_AFTER:
                            break
                        if not speech_started and silent_for >= PATIENCE_BEFORE:
                            break

                if not chunks:
                    logger.warning("VoiceLoop: no command audio collected")
                    continue

                command_audio = np.concatenate(chunks)
                logger.info("VoiceLoop: collected %.1f s of audio", len(command_audio) / 16000)

                # STAGE 3: STT with base model
                _broadcast_state("thinking")
                transcript = transcriber.transcribe(command_audio)
                logger.info("VoiceLoop: transcript --> %r", transcript)
                if not transcript:
                    _broadcast_state("idle")
                    continue

                # Strip wake phrase prefix so the command is clean
                clean = transcript.strip()
                for phrase in ZENO_WAKE_PHRASES:
                    if clean.lower().startswith(phrase):
                        clean = clean[len(phrase):].lstrip(",. ").strip()
                        break

                print(f"[ZENO] Heard: {clean!r}", flush=True)

                if not clean:
                    # User said only the wake phrase — ask what they need
                    _broadcast_state("speaking")
                    _speak("Yes, I'm listening. What can I do for you?")
                    _broadcast_state("idle")
                    continue

                # STAGE 4: NLP fuzzy intent classification
                intent = classifier.classify(clean)

                if intent is not None:
                    logger.info(
                        "VoiceLoop: intent=%s (%.0f%%) slots=%s",
                        intent.intent_name, intent.confidence * 100, intent.slots,
                    )
                    # STAGE 5a: structured dispatch
                    response = dispatch(intent, db_path=self._db_path)
                else:
                    # STAGE 5b: Gemini conversational fallback
                    logger.info("VoiceLoop: no intent match for %r -- routing to Gemini", clean)
                    print("[ZENO] No structured intent -- asking Gemini...", flush=True)
                    response = _gemini_converse(clean)

                logger.info("VoiceLoop: response --> %r", response)
                _broadcast_state("speaking")
                _speak(response)
                _broadcast_state("idle")

        except Exception as e:
            logger.error("VoiceLoop crashed: %s", e, exc_info=True)
        finally:
            mic.stop()
            detector.stop()
            logger.info("VoiceLoop: shut down cleanly.")

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="ZenoVoiceLoop"
        )
        self._thread.start()
        logger.info("VoiceLoop thread started.")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)


# ---------------------------------------------------------------------------
# WebSocket state broadcaster
# Pushes {type: "zeno_state", state: "idle"|"listening"|"thinking"|"speaking"}
# to all React frontend clients connected on ws://localhost:8767.
# ---------------------------------------------------------------------------
from zeno.monitor.ws_server import broadcast_state as _broadcast_state, broadcast_event as _broadcast_event


# ---------------------------------------------------------------------------
# OS Agent subprocess launcher
# ---------------------------------------------------------------------------
import subprocess as _subprocess

_agent_proc: "_subprocess.Popen | None" = None


def _start_os_agent() -> None:
    """Launch the ZENO OS Agent as a background subprocess on port 8765."""
    global _agent_proc
    import sys as _sys
    import time as _time

    agent_port = os.environ.get("ZENO_AGENT_PORT", "8765")
    agent_host = os.environ.get("ZENO_AGENT_HOST", "127.0.0.1")

    logger.info("Starting ZENO OS Agent on %s:%s ...", agent_host, agent_port)
    try:
        _agent_proc = _subprocess.Popen(
            [
                _sys.executable, "-m", "uvicorn",
                "zeno.agent.server:app",
                "--host", agent_host,
                "--port", agent_port,
                "--log-level", "warning",
            ],
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.PIPE,
        )
        _time.sleep(1.5)

        from zeno.agent.dispatch import is_agent_available
        if is_agent_available():
            logger.info("OS Agent ready on port %s.", agent_port)
            print(f"[ZENO] 🛠️  OS Agent running on port {agent_port} — 91 tools available.", flush=True)
        else:
            logger.warning("OS Agent health check failed. Some tools may be unavailable.")
    except Exception as e:
        logger.error("Failed to start OS Agent: %s", e)
        print(f"[ZENO] ⚠️  OS Agent failed to start: {e}", flush=True)


def _stop_os_agent() -> None:
    """Stop the OS agent subprocess."""
    global _agent_proc
    if _agent_proc is not None:
        try:
            _agent_proc.terminate()
            _agent_proc.wait(timeout=5)
        except Exception:
            _agent_proc.kill()
        _agent_proc = None
        logger.info("OS Agent stopped.")


# ---------------------------------------------------------------------------
# Daemon entry point
# ---------------------------------------------------------------------------
async def run_daemon(live_mode: bool = False) -> None:
    db_path = str(Path.home() / "Zeno" / "Zeno.db")
    os.environ["ZENO_DB_PATH"] = db_path

    # 0. Start OS Agent subprocess (91 desktop tools on port 8765)
    _start_os_agent()

    # 1. FastAPI REST API (port 8766)
    stop_event = threading.Event()
    api = ZenoDaemonAPI(db_path=db_path, stop_event=stop_event)
    api.start()

    # 2. WebSocket server for browser extension (port 8767)
    ws = BrowserWebSocketServer(db_path=db_path, send_page_title=True)
    await ws.start()

    # 3. Global hotkeys
    loop = asyncio.get_running_loop()
    hotkeys = create_listener(ws_server=ws, event_loop=loop)
    hotkeys.start()

    # Wire module-level refs so _broadcast_state() works from any thread
    global _ws_server_ref, _ws_loop_ref
    _ws_server_ref = ws
    _ws_loop_ref   = loop

    # 4a. LIVE mode: Gemini Live bidirectional audio streaming
    if live_mode:
        from zeno.voice.gemini_live import GeminiLiveSession
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        live_session = GeminiLiveSession(api_key=api_key, db_path=db_path)
        logger.info("ZENO Daemon started in LIVE mode.")
        print(
            "[ZENO] Running in LIVE mode.\n"
            "  OS Agent: port 8765  |  API: port 8766  |  WS: port 8767\n"
            "  Press Ctrl+C to stop.",
            flush=True,
        )
        try:
            await live_session.run()
        except KeyboardInterrupt:
            pass
        finally:
            live_session.stop()

    # 4b. WHISPER mode: local offline pipeline (default / privacy mode)
    else:
        voice = VoiceLoop(db_path=db_path)
        voice.start()
        logger.info("ZENO Daemon fully started in WHISPER mode.")
        print(
            "[ZENO] Running in WHISPER mode.\n"
            "  OS Agent: port 8765  |  API: port 8766  |  WS: port 8767\n"
            "  Say 'Hey Zeno' to give a voice command. Press Ctrl+C to stop.",
            flush=True,
        )
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
        voice.stop()

    await ws.stop()
    hotkeys.stop()
    _stop_os_agent()
    logger.info("ZENO Daemon shutdown complete.")


def main() -> None:
    """Start the ZENO assistant daemon.

    Flags:
        --live      Use Gemini Live streaming voice (default: Whisper offline)
        --no-agent  Skip starting the OS Agent subprocess
    """
    import argparse
    parser = argparse.ArgumentParser(description="ZENO Personal AI Assistant")
    parser.add_argument("--live", action="store_true",
                        help="Gemini Live real-time voice (requires GOOGLE_API_KEY)")
    args, _ = parser.parse_known_args()

    live_mode = args.live or os.environ.get("ZENO_VOICE_MODE", "").lower() == "live"
    mode_label = "LIVE" if live_mode else "WHISPER"
    print(f"ZENO daemon initializing... [{mode_label} MODE]", flush=True)

    try:
        asyncio.run(run_daemon(live_mode=live_mode))
    except KeyboardInterrupt:
        print("\nShutting down due to KeyboardInterrupt...")


if __name__ == "__main__":
    main()
