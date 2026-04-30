---
phase: 2
plan: 2
wave: 1
depends_on: ["1"]
---

# Plan 2.2: Wake Word Detection Loop

## Objective
Implement the continuous wake word detection loop in `wake_word.py`. This module runs
as a background thread, consuming audio frames from `MicrophoneStream.queue` and
checking each 80ms frame against the "hey zeno" wake word model using `openwakeword`.
When the wake word is detected (score > threshold), it sets a `threading.Event` to
signal the transcriber to begin capturing.

**Note on `openwakeword` dependency:** `openwakeword` is NOT currently in `requirements.txt`.
The first task in this plan adds it. It downloads model files (~50MB) on first run.

## Context
- .gsd/SPEC.md (R1 — Voice Pipeline, wake word spec)
- .gsd/phases/2/RESEARCH.md
- zeno/voice/capture.py (from Plan 2.1)
- zeno/voice/__init__.py

## Tasks

<task type="auto">
  <name>Add openwakeword to requirements.txt and pyproject.toml</name>
  <files>
    requirements.txt
    pyproject.toml
  </files>
  <action>
    1. In `requirements.txt`, add `openwakeword` on a new line after `sounddevice`.

    2. In `pyproject.toml`, in the `[project] dependencies` list, add `"openwakeword"`.
       Find the existing dependency list and insert it alphabetically (after `"icalendar"`,
       before `"pynput"` or similar).

    Do NOT remove any existing dependencies.
    Do NOT pin a version — `openwakeword` is actively developed; unpinned is correct for now.
  </action>
  <verify>python -c "import tomllib; d = tomllib.loads(open('pyproject.toml').read()); deps = d['project']['dependencies']; assert any('openwakeword' in dep for dep in deps), 'missing from pyproject.toml'; print('pyproject OK'); import importlib.util; print('openwakeword importable:', importlib.util.find_spec('openwakeword') is not None)"</verify>
  <done>`openwakeword` appears in both `requirements.txt` and `pyproject.toml` dependencies; the package can be imported after `pip install openwakeword`</done>
</task>

<task type="auto">
  <name>Create zeno/voice/wake_word.py — detection loop</name>
  <files>
    zeno/voice/wake_word.py
  </files>
  <action>
    Create `zeno/voice/wake_word.py` with:

    1. Module constant `DEFAULT_THRESHOLD = 0.5` (openwakeword confidence threshold).
       `FRAME_SAMPLES = 1280` (must match `MicrophoneStream.blocksize` — 80ms at 16kHz).

    2. Class `WakeWordDetector`:
       - `__init__(self, threshold: float = DEFAULT_THRESHOLD)`:
         * Lazy-imports `openwakeword.utils` and downloads models:
           ```python
           import openwakeword
           openwakeword.utils.download_models()
           from openwakeword.model import Model
           self._model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
           ```
           Note: "hey_jarvis" is the closest pre-trained model; ZENO will confirm via short
           Whisper transcript too (belt-and-suspenders approach per RESEARCH.md).
         * `self.threshold = threshold`
         * `self.detected = threading.Event()` — set when wake word fires.
         * `self._stop = threading.Event()`
         * `self._thread: threading.Thread | None = None`

       - `_score_frame(self, audio_frame: np.ndarray) -> float`:
         `openwakeword` requires `int16` PCM, but `sounddevice` outputs `float32`.
         Must convert: `frame_int16 = (audio_frame * 32768).astype(np.int16)`
         Calls `self._model.predict(frame_int16)` — returns a dict like
         `{"hey_jarvis": 0.87}`. Extract the max score across all keys and return it.

       - `run_loop(self, audio_queue: queue.Queue) -> None`:
         ```
         while not self._stop.is_set():
             try:
                 frame = audio_queue.get(timeout=0.5)
             except queue.Empty:
                 continue
             score = self._score_frame(frame)
             if score >= self.threshold:
                 self.detected.set()
                 # Wait until caller clears the event before detecting again
                 while self.detected.is_set() and not self._stop.is_set():
                     time.sleep(0.1)
         ```

       - `start(self, audio_queue: queue.Queue) -> None`:
         Creates daemon thread targeting `self.run_loop(audio_queue)`, stores in
         `self._thread`, starts it.

       - `stop(self) -> None`:
         Sets `self._stop`. Joins `self._thread` with 2s timeout.

       - `wait_for_wake(self, timeout: float | None = None) -> bool`:
         Convenience: blocks until `self.detected` is set or timeout expires.
         Returns `True` if detected, `False` on timeout.

    3. Module-level `create_detector(threshold: float = DEFAULT_THRESHOLD) -> WakeWordDetector`
       factory function.

    Import: `threading`, `queue`, `time`, `numpy as np`.
    Lazy-import `openwakeword` inside `__init__` to avoid import-time model download.

    CRITICAL: The constructor MUST lazy-import openwakeword. Import at top-of-file will
    trigger a 50MB model download on every test run — this is unacceptable.
    CRITICAL: `run_loop` must catch ALL exceptions inside the loop body and log to stderr
    rather than crashing the thread silently.
  </action>
  <verify>python -c "from zeno.voice.wake_word import WakeWordDetector, DEFAULT_THRESHOLD; print('wake_word OK', DEFAULT_THRESHOLD)"</verify>
  <done>Import succeeds without triggering model download; `DEFAULT_THRESHOLD == 0.5`; `WakeWordDetector(threshold=0.5)` class exists; no crash on import</done>
</task>

## Success Criteria
- [ ] `openwakeword` added to `requirements.txt` and `pyproject.toml`
- [ ] `from zeno.voice.wake_word import WakeWordDetector` imports without triggering model download
- [ ] `WakeWordDetector.detected` is a `threading.Event`
- [ ] `WakeWordDetector.wait_for_wake(timeout=1.0)` returns `False` when not triggered
