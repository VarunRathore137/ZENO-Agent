"""
ZENO voice detection diagnostic.

BEFORE RUNNING:
  - Stop the ZENO daemon (Ctrl+C in its terminal) — it holds the mic open
  - Run from project root: python scripts/voice_test.py

The script will count down and tell you exactly when to stay silent or speak.
"""
import sounddevice as sd
import numpy as np
import time
import sys

SR = 16000


def countdown(action: str, seconds: int = 3):
    """Print a live countdown so you know exactly when recording starts."""
    print(f"\n  >> {action}")
    for i in range(seconds, 0, -1):
        print(f"     Starting in {i}...", end="\r", flush=True)
        time.sleep(1.0)
    print("  " + "=" * 40)
    print(f"  >>> RECORDING NOW — {action} <<<")
    print("  " + "=" * 40, flush=True)


def record_and_analyse(label: str, seconds: int, action: str):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")

    countdown(action, seconds=3)

    audio = sd.rec(int(seconds * SR), samplerate=SR, channels=1, dtype="float32")
    # Show elapsed time while recording
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        elapsed = time.monotonic() - start
        remaining = seconds - elapsed
        print(f"  Recording... {remaining:.1f}s left   ", end="\r", flush=True)
        time.sleep(0.1)
    sd.wait()
    print("  Recording done.                      ")

    clip = audio[:, 0]
    rms = float(np.sqrt(np.mean(clip ** 2)))

    # webrtcvad frame-by-frame analysis
    import webrtcvad
    vad = webrtcvad.Vad(1)
    pcm = (np.clip(clip, -1.0, 1.0) * 32767).astype(np.int16)
    FRAME = 320  # 20 ms at 16 kHz
    results = []
    for i in range(0, len(pcm) - FRAME, FRAME):
        fb = pcm[i: i + FRAME].tobytes()
        try:
            results.append(vad.is_speech(fb, SR))
        except Exception:
            results.append(False)

    speech_frames = sum(results)
    total_frames  = len(results)
    speech_pct    = 100.0 * speech_frames / total_frames if total_frames else 0
    consec = max_consec = 0
    for r in results:
        consec = consec + 1 if r else 0
        max_consec = max(max_consec, consec)

    # Whisper with hallucination suppression settings
    import whisper
    result  = model.transcribe(
        clip,
        language="en",
        fp16=False,
        condition_on_previous_text=False,
        initial_prompt="Hey Zenith, Hey Zeno, Okay Zeno, Hi Zen",
    )
    text    = result.get("text", "").strip()
    segs    = result.get("segments", [])
    avg_nsp = (
        sum(s.get("no_speech_prob", 0) for s in segs) / len(segs)
        if segs else 1.0
    )

    print(f"\n  RMS level        : {rms:.5f}")
    print(f"  webrtcvad        : {speech_frames}/{total_frames} frames = {speech_pct:.0f}% speech  (max consecutive: {max_consec})")
    print(f"  Whisper heard    : {text!r}")
    print(f"  no_speech_prob   : {avg_nsp:.2f}  (>0.5 means Whisper thinks it's noise)")
    return speech_frames, max_consec, text, avg_nsp


# ── Load Whisper once ─────────────────────────────────────────────────────────
print("\nLoading Whisper tiny...")
import whisper
model = whisper.load_model("tiny")
print("Ready!\n")
print("This test has 3 parts. Read each instruction before the countdown ends.")
input("Press ENTER to begin...")

# ── TEST 1: silence ───────────────────────────────────────────────────────────
s1, c1, t1, n1 = record_and_analyse(
    "TEST 1 of 3 — SILENCE TEST",
    seconds=3,
    action="STAY COMPLETELY SILENT — do not speak or move",
)
input("\nPress ENTER for the next test...")

# ── TEST 2: full command ──────────────────────────────────────────────────────
s2, c2, t2, n2 = record_and_analyse(
    "TEST 2 of 3 — FULL COMMAND",
    seconds=5,
    action='SAY THIS CLEARLY: "Hey Zeno, what are my tasks today?"',
)
input("\nPress ENTER for the next test...")

# ── TEST 3: just wake word ────────────────────────────────────────────────────
s3, c3, t3, n3 = record_and_analyse(
    "TEST 3 of 3 — WAKE WORD ONLY",
    seconds=3,
    action='SAY THIS CLEARLY: "Okay Zeno"',
)

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
print(f"  Silence   — RMS: {0:.5f}  webrtcvad: {s1} frames  Whisper: {t1!r}")
print(f"  Full cmd  — webrtcvad: {s2} frames  Whisper: {t2!r}  no_speech: {n2:.2f}")
print(f"  Wake word — webrtcvad: {s3} frames  Whisper: {t3!r}  no_speech: {n3:.2f}")
print()
if s2 > s1 + 2 or s3 > s1 + 2:
    ideal_min = max(s1 + 1, 2)
    print(f"  GOOD  webrtcvad CAN tell your voice apart from silence.")
    print(f"        Recommended SPEECH_FRAME_MIN = {ideal_min}")
else:
    print("  PROBLEM  webrtcvad sees the same frames in silence and speech.")
    print("           Your mic DSP is suppressing all audio including your voice.")
    print()
    print("  NEXT STEPS:")
    print("   1. Open Windows Settings > Privacy > Microphone")
    print("      Make sure microphone access is ON for Desktop apps")
    print("   2. Try speaking louder and closer to the mic")
    print("   3. Or use Push-To-Talk instead: hold Ctrl+Shift+J to speak to ZENO")

