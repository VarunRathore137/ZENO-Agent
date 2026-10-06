import threading
import queue
import time
import sys
import numpy as np

DEFAULT_THRESHOLD = 0.5
FRAME_SAMPLES = 1280  # 80ms at 16kHz

# Acoustic model shipped with openwakeword that works out-of-the-box.
# "alexa" is included in the default bundle and fires reliably.
# The transcript-based fallback (see _matches_transcript) handles
# "Hey Zeno" / "Okay Zeno" etc. via Whisper — no custom model needed.
DEFAULT_MODEL = "alexa"

# These phrases are matched against the Whisper transcript AFTER wake-word
# detection fires (or as a standalone fallback when the acoustic model
# produces a low score).  All comparisons are lower-case and prefix-matched
# so "hey zeno what's the time" still counts as a wake phrase.
ZENO_WAKE_PHRASES = [
    "hey zeno",
    "okay zeno",
    "ok zeno",
    "yo zeno",
    "hey zen",
    "hi zen",
    "hi zeno",
    "hello zeno",
    "wake up zeno",
    "zeno wake up",
    "zen wake up",
    "hey zenith",
    "okay zenith",
    "ok zenith",
    "hi zenith",
    "zenith",
]


def _matches_transcript(transcript: str) -> bool:
    """
    Return True if the transcript matches any configured wake phrase.

    Two-stage check:
      1. Exact prefix match  — fast, zero dependencies
      2. Fuzzy match         — catches Whisper mis-transcriptions like
                               "you know" for "Zeno", "hey zen oh" for "Hey Zeno"
    """
    t = transcript.lower().strip()
    if not t:
        return False

    # Stage 1: exact prefix match (fast path)
    if any(t.startswith(p) for p in ZENO_WAKE_PHRASES):
        return True

    # Stage 2: fuzzy match via rapidfuzz (handles mis-transcriptions)
    try:
        from rapidfuzz import fuzz
        for phrase in ZENO_WAKE_PHRASES:
            # partial_ratio: checks if phrase appears as a fuzzy substring
            # 85 is much tighter than 70 — prevents TV audio, keyboard noise,
            # or random words from fuzzy-matching wake phrases
            if fuzz.partial_ratio(phrase, t) >= 85:
                return True
        # Word-level zeno variant check — only fire on strong matches
        # Removed "you know", "is it no", "it no", "lino" — too ambiguous
        zeno_variants = ["zeno", "zen", "xeno", "zenith"]
        words = t.split()
        for word in words:
            for variant in zeno_variants:
                if fuzz.ratio(word, variant) >= 80:
                    return True
        # Exact substring check for the unambiguous core variants only
        for variant in zeno_variants:
            if variant in t:
                return True
    except ImportError:
        pass

    return False


class WakeWordDetector:
    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        model_name: str = DEFAULT_MODEL,
    ):
        """
        Initialize the wake word detector.
        Downloads models on first run via lazy-import.

        Args:
            threshold:  Acoustic confidence threshold (0–1).  0.5 is default.
            model_name: openwakeword model to load.  Defaults to "alexa".
        """
        self._model = None
        try:
            import openwakeword
            openwakeword.utils.download_models()
            from openwakeword.model import Model
            self._model = Model(wakeword_models=[model_name], inference_framework="onnx")
            print(f"[ZENO] Wake-word model '{model_name}' loaded.", file=sys.stderr)
        except Exception as e:
            # Degrade gracefully: acoustic model unavailable, transcript fallback still works.
            print(
                f"[ZENO] Warning: could not load wake-word model '{model_name}': {e}\n"
                "       Transcript-based wake detection will be used instead.",
                file=sys.stderr,
            )

        self.threshold = threshold
        self.detected = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _score_frame(self, audio_frame: np.ndarray) -> float:
        """
        Convert float32 audio frame to int16 and score it.
        Returns 0.0 if model is unavailable.
        """
        if self._model is None:
            return 0.0

        # openwakeword requires int16 PCM
        frame_int16 = (audio_frame * 32768).astype(np.int16)

        # predict returns a dict of {model_name: score}
        scores = self._model.predict(frame_int16)

        if not scores:
            return 0.0

        return max(scores.values())

    def check_transcript(self, transcript: str) -> bool:
        """
        Check if a Whisper transcript matches a ZENO wake phrase.
        Call this AFTER transcribing audio to provide a reliable fallback.
        Returns True if matched (and sets the detected event).
        """
        if _matches_transcript(transcript):
            self.detected.set()
            return True
        return False

    def run_loop(self, audio_queue: queue.Queue) -> None:
        """
        Background loop consuming audio frames and checking for wake word.
        """
        while not self._stop.is_set():
            try:
                try:
                    frame = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                score = self._score_frame(frame)

                if score >= self.threshold:
                    self.detected.set()
                    # Wait until caller clears the event before detecting again
                    # This prevents multiple detections for the same wake word utterance
                    while self.detected.is_set() and not self._stop.is_set():
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error in WakeWordDetector loop: {e}", file=sys.stderr)
                time.sleep(0.1)  # Avoid tight loop on persistent error

    def start(self, audio_queue: queue.Queue) -> None:
        """
        Start the detection loop in a daemon thread.
        """
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(
            target=self.run_loop,
            args=(audio_queue,),
            daemon=True,
            name="WakeWordDetectorThread",
        )
        self._thread.start()

    def stop(self) -> None:
        """
        Stop the detection loop.
        """
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def wait_for_wake(self, timeout: float | None = None) -> bool:
        """
        Block until the wake word is detected or timeout expires.
        Returns True if detected, False on timeout.
        """
        return self.detected.wait(timeout=timeout)


def create_detector(
    threshold: float = DEFAULT_THRESHOLD,
    model_name: str = DEFAULT_MODEL,
) -> WakeWordDetector:
    """
    Factory function to create a WakeWordDetector.
    """
    return WakeWordDetector(threshold=threshold, model_name=model_name)
