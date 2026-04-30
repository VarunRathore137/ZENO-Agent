---
phase: 2
plan: 3
wave: 2
depends_on: ["1", "2"]
---

# Plan 2.3: Whisper STT Transcriber + Unit Tests

## Objective
Implement `transcriber.py` — the Whisper speech-to-text wrapper that converts a buffered
`numpy` audio array into a raw transcript string. Also create the unit test suite for
all three voice modules (transcriber, hotkeys, capture) using mocks so tests run
without real hardware or model downloads.

**Wave 2:** Depends on Plans 2.1 and 2.2 being complete (imports them in tests).

## Context
- .gsd/SPEC.md (R1 — Voice Pipeline)
- .gsd/phases/2/RESEARCH.md
- zeno/voice/capture.py (Plan 2.1)
- zeno/voice/wake_word.py (Plan 2.2)
- requirements-dev.txt

## Tasks

<task type="auto">
  <name>Create zeno/voice/transcriber.py — Whisper STT wrapper</name>
  <files>
    zeno/voice/transcriber.py
  </files>
  <action>
    Create `zeno/voice/transcriber.py` using `openai-whisper` (already in requirements.txt).

    1. Module constants:
       - `DEFAULT_MODEL = "base"` — matches SPEC.md `stt_model: whisper-base`
       - `SAMPLE_RATE = 16000`

    2. Class `WhisperTranscriber`:
       - `__init__(self, model_name: str = DEFAULT_MODEL)`:
         * Lazy-import whisper: `import whisper` inside `__init__`
         * `self._model = whisper.load_model(model_name)` — loads on first instantiation
         * `self.model_name = model_name`

       - `transcribe(self, audio: np.ndarray, language: str = "en") -> str`:
         Transcribes a float32 numpy array (16kHz mono) and returns the transcript string.
         ```python
         result = self._model.transcribe(audio, language=language, fp16=False)
         return result["text"].strip()
         ```
         `fp16=False` forces CPU-safe mode — no GPU assumption.
         Return empty string `""` if result["text"] is empty or whitespace-only.

       - `transcribe_file(self, filepath: str | Path, language: str = "en") -> str`:
         Convenience: loads audio from file path using `whisper.load_audio(str(filepath))`,
         then calls `self.transcribe(audio, language)`.

    3. Module-level helper `collect_audio(audio_queue: queue.Queue, duration_s: float = 5.0,
       sample_rate: int = SAMPLE_RATE) -> np.ndarray`:
       Reads from an audio queue for `duration_s` seconds, concatenating chunks into a
       single float32 numpy array. Returns the concatenated array. Stops early if queue
       is empty for >500ms consecutively (end of speech).

    Import: `numpy as np`, `queue`, `pathlib.Path`, `time`.
    Lazy-import `whisper` inside `__init__` only — NOT at module level.

    CRITICAL: `transcribe()` must accept a numpy array, NOT a file path. The caller
    (wake word → buffer → transcribe) always works with in-memory arrays.
    CRITICAL: Do NOT call `whisper.load_model()` at import time. Tests must be able to
    import this module without downloading Whisper models.
  </action>
  <verify>python -c "from zeno.voice.transcriber import WhisperTranscriber, DEFAULT_MODEL, collect_audio; print('transcriber OK', DEFAULT_MODEL)"</verify>
  <done>Import succeeds without model download; `DEFAULT_MODEL == "base"`; `WhisperTranscriber` class exists; `collect_audio` is callable</done>
</task>

<task type="auto">
  <name>Create tests/voice/ unit tests with mocks</name>
  <files>
    tests/__init__.py
    tests/voice/__init__.py
    tests/voice/test_transcriber.py
    tests/voice/test_capture.py
    tests/voice/test_hotkeys.py
  </files>
  <action>
    Create the test suite for Phase 2 voice modules. All tests MUST run without
    real hardware (no microphone) and without downloading AI models (use mocks).

    **tests/__init__.py** and **tests/voice/__init__.py**: Empty files.

    **tests/voice/test_transcriber.py**:
    ```python
    import numpy as np
    import pytest
    from unittest.mock import MagicMock, patch
    from zeno.voice.transcriber import WhisperTranscriber, DEFAULT_MODEL, collect_audio
    import queue, threading

    def test_default_model_constant():
        assert DEFAULT_MODEL == "base"

    def test_transcriber_lazy_import():
        """WhisperTranscriber class importable without loading model."""
        # Just importing the class should not trigger whisper.load_model
        assert WhisperTranscriber is not None

    @patch("whisper.load_model")
    def test_transcribe_returns_stripped_text(mock_load):
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "  hello world  "}
        mock_load.return_value = mock_model

        t = WhisperTranscriber()
        audio = np.zeros(16000, dtype=np.float32)
        result = t.transcribe(audio)
        assert result == "hello world"

    @patch("whisper.load_model")
    def test_transcribe_empty_audio_returns_empty_string(mock_load):
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "   "}
        mock_load.return_value = mock_model

        t = WhisperTranscriber()
        result = t.transcribe(np.zeros(16000, dtype=np.float32))
        assert result == ""

    def test_collect_audio_concatenates_chunks():
        q = queue.Queue()
        chunk = np.ones(1280, dtype=np.float32)
        for _ in range(5):
            q.put(chunk)
        # collect for 0.1s — should drain the 5 chunks quickly
        result = collect_audio(q, duration_s=0.1)
        assert result.dtype == np.float32
        assert len(result) > 0
    ```

    **tests/voice/test_capture.py**:
    ```python
    import pytest
    from unittest.mock import patch, MagicMock
    from zeno.voice.capture import MicrophoneStream, SAMPLE_RATE, CHANNELS, DTYPE, list_devices

    def test_constants():
        assert SAMPLE_RATE == 16000
        assert CHANNELS == 1
        assert DTYPE == "float32"

    def test_microphone_stream_init():
        stream = MicrophoneStream()
        assert stream.queue is not None
        assert stream._stream is None  # Not started yet

    @patch("sounddevice.query_devices")
    def test_list_devices(mock_query):
        mock_query.return_value = [{"name": "Mock Mic", "max_input_channels": 2}]
        devices = list_devices()
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert devices[0]["name"] == "Mock Mic"
    ```

    **tests/voice/test_hotkeys.py**:
    ```python
    import pytest
    import threading
    from zeno.voice.hotkeys import HotkeyListener, HotkeyState

    def test_hotkey_state_init():
        state = HotkeyState()
        assert isinstance(state.brain_dump_triggered, threading.Event)
        assert isinstance(state.push_to_talk_active, threading.Event)
        assert not state.brain_dump_triggered.is_set()
        assert not state.push_to_talk_active.is_set()

    def test_listener_init_with_state():
        state = HotkeyState()
        listener = HotkeyListener(state)
        assert listener.state is state

    def test_listener_init_creates_state_if_none():
        listener = HotkeyListener()
        assert listener.state is not None
        assert isinstance(listener.state, HotkeyState)

    def test_ptt_events():
        """PTT callbacks set/clear the event correctly."""
        state = HotkeyState()
        listener = HotkeyListener(state)
        listener._on_ptt_press()
        assert state.push_to_talk_active.is_set()
        listener._on_ptt_release()
        assert not state.push_to_talk_active.is_set()
    ```

    Run the tests with: `python -m pytest tests/voice/ -v`
    All 4 files must exist. All tests must pass (or be clearly skipped with reason).
  </action>
  <verify>python -m pytest tests/voice/ -v --tb=short 2>&1 | tail -20</verify>
  <done>All tests in `tests/voice/` pass (or show collected with no failures); no `ModuleNotFoundError` for any zeno.voice submodule</done>
</task>

## Success Criteria
- [ ] `from zeno.voice.transcriber import WhisperTranscriber, collect_audio` imports without model download
- [ ] `python -m pytest tests/voice/ -v` passes all tests (mocked — no real hardware)
- [ ] `WhisperTranscriber.transcribe(np.zeros(16000, dtype=np.float32))` returns a string when model mocked
- [ ] `collect_audio` produces a float32 ndarray from a queue
