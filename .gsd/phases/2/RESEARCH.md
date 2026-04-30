---
phase: 2
level: 2
researched_at: 2026-04-30
---

# Phase 2 Research — Voice Pipeline: Wake Word & STT

## Questions Investigated

1. Should we use `faster-whisper` or `openai-whisper` for STT? What is the exact API?
2. What audio format does `openwakeword` expect for streaming inference?
3. Should hotkeys use `keyboard` or `pynput`? Are there Windows privilege issues?
4. What are the sounddevice `float32` vs openwakeword `int16` format implications?
5. Are there Windows-specific PortAudio/microphone access issues to plan for?

---

## Findings

### 1. STT Engine: `faster-whisper` vs `openai-whisper`

**Decision: Use `openai-whisper`** for Plan 2.3 (NOT `faster-whisper`).

**Rationale:**
- `pyproject.toml` already lists `"openai-whisper"` — not `faster-whisper`
- `openai-whisper` API: `result = model.transcribe(audio_np, language="en", fp16=False)` → `result["text"]` (dict)
- `faster-whisper` API is DIFFERENT: `segments, info = model.transcribe(audio_np)` → must iterate `segments` generator
- Plan 2.3 was written against `openai-whisper` API (`result["text"]`) — this is correct as-is
- `faster-whisper` is a future optimization (RESEARCH.md previously noted this); do NOT use it in Phase 2

**Critical `openai-whisper` notes:**
- Input: `np.float32` array, 16kHz, mono, normalized to `[-1.0, 1.0]`
- `fp16=False` is mandatory — CPU mode, avoids half-precision crash
- Lazy-import inside `__init__` is essential — model download (~140MB for `base`) happens at `load_model()` call
- `result["text"]` may have leading/trailing whitespace — always `.strip()`

**Sources:** Official openai-whisper README, Stack Overflow, research synthesis

**Recommendation:** Keep Plan 2.3 as written. The `openai-whisper` dependency in `pyproject.toml` is correct.

---

### 2. `openwakeword` Streaming Format — CRITICAL FINDING

**Finding: `openwakeword` expects `int16` PCM, NOT `float32`.**

This is a critical incompatibility:
- `sounddevice` captures audio as `float32` (configured with `dtype='float32'`)
- `openwakeword.model.Model.predict(frame)` expects **16-bit signed integer** (`np.int16`) at 16kHz

**Required conversion in `wake_word.py`:**
```python
# sounddevice gives float32 in [-1.0, 1.0]
# openwakeword needs int16 in [-32768, 32767]
frame_int16 = (audio_frame * 32768).astype(np.int16)
prediction = self._model.predict(frame_int16)
```

**Frame size:** Must be exactly **1280 samples** (80ms at 16kHz). This matches `MicrophoneStream.blocksize = 1280`. ✓

**openwakeword predict API:**
```python
from openwakeword.model import Model
model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
# Returns dict: {"hey_jarvis": 0.87, ...}
prediction = model.predict(frame_int16)
score = max(prediction.values())  # or check specific key
```

**Model download:** `openwakeword.utils.download_models()` downloads ~50MB on first run. Lazy-import is non-negotiable.

**Sources:** openwakeword PyPI docs, GitHub README, deepcorelabs.com streaming example

**Recommendation:** Plan 2.2 `_score_frame` MUST convert `float32 → int16` before calling `predict()`. This is an actionable fix for the plan.

---

### 3. Hotkeys: `keyboard` vs `pynput` — Plan vs Research Discrepancy

**Finding: Plan 2.1 uses `keyboard` library; RESEARCH.md originally recommended `pynput`.**

**Decision: Use `pynput.keyboard.GlobalHotKeys`** — it is the superior choice.

| Factor | `keyboard` | `pynput` |
|--------|-----------|---------|
| Admin on Windows | Requires elevated rights for some hooks | Works without admin for normal apps |
| API for global hotkeys | `keyboard.add_hotkey()` | `pynput.keyboard.GlobalHotKeys` |
| In pyproject.toml | `"keyboard"` present | `"pynput"` NOT yet in deps |
| Thread model | Blocking `keyboard.wait()` needed | Listener is already a daemon thread |

**pynput `GlobalHotKeys` pattern (correct):**
```python
from pynput import keyboard

def on_brain_dump():
    brain_dump_event.set()

with keyboard.GlobalHotKeys({
    '<ctrl>+<shift>+<space>': on_brain_dump,
}) as h:
    h.join()
```

**Windows privilege caveat:** pynput CANNOT capture keystrokes when an elevated-privilege window is in focus (e.g., Task Manager). This is an OS security restriction — acceptable for ZENO's use case (it's not a keylogger).

**Action required for Plan 2.1:** Plan 2.1 must be corrected to use `pynput` instead of `keyboard`. Also need to add `"pynput"` to `pyproject.toml` if not present.

**Sources:** pynput PyPI docs, pynput readthedocs, Stack Overflow

**Recommendation:** Update Plan 2.1 to use `pynput.keyboard.GlobalHotKeys`. Add `pynput` to `pyproject.toml`.

---

### 4. Audio Capture: `sounddevice` on Windows

**Finding: sounddevice works well on Windows without admin rights.**

- `sounddevice` wraps PortAudio — wheels on PyPI include bundled PortAudio binaries for Windows (no manual install needed)
- `pyaudio` is also in `pyproject.toml` but is NOT used in Phase 2 — `sounddevice` is the chosen library
- Common issue: Windows Microphone Privacy settings can block access → document in README

**Potential conflict:** Both `sounddevice` and `pyaudio` use PortAudio internally. Instantiating streams from both simultaneously can cause device conflicts. ZENO only uses `sounddevice` — do NOT open a `pyaudio` stream.

**Correct `sounddevice` callback pattern:**
```python
# dtype MUST be 'float32' for sounddevice
# blocksize = 1280 for 80ms frames
def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(indata[:, 0].copy())  # mono channel

with sd.InputStream(samplerate=16000, channels=1, dtype='float32',
                    blocksize=1280, callback=callback):
    # wake word loop runs here
```

**Sources:** sounddevice docs, clay-atlas.com, Stack Overflow

---

### 5. `faster-whisper` — Deferred to Future Phase

`faster-whisper` returns a **generator** of segment objects, not a dict:
```python
segments, info = model.transcribe(audio)
text = " ".join(seg.text for seg in segments)  # must iterate generator
```

This is architecturally different from `openai-whisper`. Switching is a future optimization task — add to backlog, do NOT introduce in Phase 2.

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| STT library | `openai-whisper` | Already in pyproject.toml; Plan 2.3 API matches |
| Wake word library | `openwakeword` | Apache 2.0, no API key, CPU-capable |
| Wake word audio format | Convert `float32 → int16` in `wake_word.py` | openwakeword requires int16; sounddevice outputs float32 |
| Hotkey library | `pynput` | No admin required; `GlobalHotKeys` API is cleaner |
| Audio capture library | `sounddevice` | Already chosen; pyaudio in deps but NOT used in Phase 2 |
| VAD strategy | Energy-based (numpy RMS threshold) | Simpler; avoids torch dep just for VAD in Phase 2 |

---

## Patterns to Follow

- **Lazy-import pattern**: All heavy imports (`whisper`, `openwakeword`) inside `__init__` — NEVER at module top level
- **Queue producer-consumer**: `sounddevice` callback → `queue.Queue` → wake word thread / transcriber thread
- **Threading.Event signaling**: Use events, never shared mutable state or polling flags
- **Daemon threads for listeners**: All background threads set `daemon=True` so they die with the main process
- **Context manager for streams**: `MicrophoneStream` as `with` block ensures `.stop()`/`.close()` on exit

---

## Anti-Patterns to Avoid

- **`openai-whisper` at module import**: Triggers 140MB download on `import` — lazy-import only
- **`float32` frames to openwakeword**: Will produce wrong scores or crash — always convert to `int16` first
- **Blocking in audio callback**: `sounddevice` callbacks must be fast; never call blocking functions inside
- **`keyboard.wait()` in main thread**: Blocks main loop; use daemon thread or pynput's non-blocking `GlobalHotKeys`
- **Opening `pyaudio` stream alongside `sounddevice`**: PortAudio device conflict on Windows

---

## Dependencies Identified

| Package | Version | Purpose | In pyproject.toml? |
|---------|---------|---------|-------------------|
| `openai-whisper` | unpinned | STT transcription | ✓ Yes |
| `sounddevice` | unpinned | Microphone capture | ✓ Yes |
| `openwakeword` | unpinned | Wake word detection | ✗ Add in Plan 2.2 |
| `pynput` | unpinned | Global hotkeys | ✗ Add in Plan 2.1 or 2.2 |
| `numpy` | unpinned | Audio array ops | ✓ Yes (transitive) |
| `keyboard` | unpinned | Legacy dep — NOT used in Phase 2 | ✓ Yes (keep, may use elsewhere) |

---

## Plan Corrections Required

### Plan 2.1 (hotkeys.py) — Must Fix Before Execution
- **Issue**: Plan 2.1 uses `keyboard.add_hotkey()` API from `keyboard` library
- **Fix**: Replace with `pynput.keyboard.GlobalHotKeys` pattern
- **Also**: Add `"pynput"` to `pyproject.toml` dependencies

### Plan 2.2 (wake_word.py) — Must Fix Before Execution
- **Issue**: `_score_frame` passes raw `float32` frame to `openwakeword.predict()`
- **Fix**: Add `frame_int16 = (audio_frame * 32768).astype(np.int16)` before calling `predict()`

### Plan 2.3 (transcriber.py) — Correct As-Is
- Uses `openai-whisper` API correctly (`result["text"]`)
- `fp16=False` already specified
- Lazy-import inside `__init__` already specified

---

## Risks

- **openwakeword ~50MB first-run download**: Mitigation — lazy-import + document in README; first run is slow but expected
- **Windows microphone privacy settings blocking sounddevice**: Mitigation — add OS privacy check to `capture.py` error handling and user-facing error message
- **pynput cannot intercept elevated-window keystrokes**: Mitigation — acceptable limitation; ZENO targets normal workflow, not UAC dialogs
- **openai-whisper model download (~140MB) for `base` model**: Mitigation — lazy-load; document in README; future option to use `tiny` model for faster startup

---

## Ready for Planning

- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
- [x] Critical API mismatches documented (int16/float32, openai vs faster-whisper)
- [x] Plan corrections identified (Plans 2.1 and 2.2 need updates before execution)
