---
phase: 2
plan: 1
wave: 1
---

# Plan 2.1: Microphone Capture & Global Hotkeys

## Objective
Build the audio capture foundation and global hotkey listener. `capture.py` provides a
continuous, non-blocking microphone stream that other voice components consume via a
shared `queue.Queue`. `hotkeys.py` registers `Ctrl+Shift+Space` (brain dump) and
`Ctrl+Shift+J` held (push-to-talk) using the `keyboard` library (already in
`requirements.txt`), signaling via `threading.Event` flags.

This is the lowest-level audio infrastructure that wake word detection and STT both
depend on — it must be implemented first.

## Context
- .gsd/SPEC.md (R1 — Voice Pipeline)
- .gsd/phases/2/RESEARCH.md
- zeno/voice/__init__.py
- requirements.txt

## Tasks

<task type="auto">
  <name>Create zeno/voice/capture.py — sounddevice microphone stream</name>
  <files>
    zeno/voice/capture.py
  </files>
  <action>
    Create `zeno/voice/capture.py` with the following:

    1. Module-level constant `SAMPLE_RATE = 16000` and `CHANNELS = 1` and `DTYPE = "float32"`.
       Whisper expects 16kHz mono float32 — do NOT use a different format.

    2. Class `MicrophoneStream`:
       - `__init__(self, blocksize: int = 1280)` — 1280 samples = 80ms at 16kHz, good for
         wake word frame size.
       - `self.queue: queue.Queue[np.ndarray]` — thread-safe audio chunk queue.
       - `self._stream: sd.InputStream | None = None`
       - `_callback(self, indata, frames, time, status)` — sounddevice callback:
         * If `status` is truthy, `print(status, file=sys.stderr)` (non-fatal, just log)
         * Put `indata[:, 0].copy()` into `self.queue` (extract mono channel)
       - `start(self) -> None` — creates `sd.InputStream(samplerate=SAMPLE_RATE,
         channels=CHANNELS, dtype=DTYPE, blocksize=self.blocksize, callback=self._callback)`
         and calls `.start()`. Store as `self._stream`.
       - `stop(self) -> None` — calls `self._stream.stop()` and `self._stream.close()` if
         `self._stream is not None`.
       - `__enter__` / `__exit__` for context manager usage.
       - `read(self, timeout: float = 1.0) -> np.ndarray | None` — calls
         `self.queue.get(timeout=timeout)`, returns `None` on `queue.Empty`.

    3. Module-level helper `list_devices() -> list[dict]` — returns
       `[{"index": i, "name": d["name"]} for i, d in enumerate(sd.query_devices())]`
       for debugging.

    Do NOT start the stream in `__init__` — caller controls lifecycle.
    Import `sounddevice as sd`, `numpy as np`, `queue`, `sys`.
  </action>
  <verify>python -c "from zeno.voice.capture import MicrophoneStream, SAMPLE_RATE; print('capture OK', SAMPLE_RATE)"</verify>
  <done>Import succeeds; `SAMPLE_RATE == 16000`; `MicrophoneStream` instantiates without error; `list_devices()` returns a list</done>
</task>

<task type="auto">
  <name>Create zeno/voice/hotkeys.py — global hotkey listener</name>
  <files>
    zeno/voice/hotkeys.py
  </files>
  <action>
    Create `zeno/voice/hotkeys.py` using the `keyboard` library (already in requirements.txt).

    1. Define `HotkeyState` dataclass (or simple class):
       ```python
       @dataclass
       class HotkeyState:
           brain_dump_triggered: threading.Event = field(default_factory=threading.Event)
           push_to_talk_active: threading.Event = field(default_factory=threading.Event)
       ```

    2. Class `HotkeyListener`:
       - `__init__(self, state: HotkeyState | None = None)` — stores state, creates one
         if not provided.
       - `self.state: HotkeyState`
       - `self._thread: threading.Thread | None = None`
       - `self._stop_event = threading.Event()`

       - `_on_brain_dump(self) -> None`:
         Sets `self.state.brain_dump_triggered`, then clears it after 100ms (fire-and-forget).
         The consuming code watches for the event to be set.

       - `_on_ptt_press(self) -> None`: Sets `self.state.push_to_talk_active`.
       - `_on_ptt_release(self) -> None`: Clears `self.state.push_to_talk_active`.

       - `start(self) -> None`:
         Registers hotkeys using `keyboard.add_hotkey` and `keyboard.on_press_key` /
         `keyboard.on_release_key` in a daemon thread:
         * `keyboard.add_hotkey("ctrl+shift+space", self._on_brain_dump)`
         * Push-to-talk: detect `ctrl+shift+j` hold — use `keyboard.on_press_key("j",
           self._on_ptt_press)` and `keyboard.on_release_key("j", self._on_ptt_release)`.
           Note: simplified — full combo detection via `keyboard.is_pressed`.
         Then call `keyboard.wait()` — this blocks the thread but not the main thread.
         Run this entire registration in a daemon `threading.Thread`.

       - `stop(self) -> None`: Calls `keyboard.unhook_all()` and sets `self._stop_event`.

    3. Module-level `create_listener(state: HotkeyState | None = None) -> HotkeyListener`
       factory function for convenience.

    Import: `keyboard`, `threading`, `dataclasses`, `time`.

    CRITICAL: Do NOT block the main thread. All listener logic in daemon thread.
    CRITICAL: Callbacks must never raise — wrap in try/except and log to stderr.
  </action>
  <verify>python -c "from zeno.voice.hotkeys import HotkeyListener, HotkeyState; s = HotkeyState(); l = HotkeyListener(s); print('hotkeys OK')"</verify>
  <done>Import succeeds; `HotkeyState` instantiates; `HotkeyListener(state)` creates without error; no exceptions on import</done>
</task>

## Success Criteria
- [ ] `from zeno.voice.capture import MicrophoneStream, SAMPLE_RATE` imports cleanly
- [ ] `from zeno.voice.hotkeys import HotkeyListener, HotkeyState` imports cleanly
- [ ] `MicrophoneStream()` context manager works (does not crash without a real mic)
- [ ] `SAMPLE_RATE == 16000`, `CHANNELS == 1`, `DTYPE == "float32"`
