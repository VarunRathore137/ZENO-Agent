# Phase 2 Research — Voice Pipeline

> Discovery Level: 2 (Standard Research)
> Date: 2026-04-30

---

## Component Decisions

### 1. STT Engine: `faster-whisper` over `openai-whisper`

**Decision:** Use `faster-whisper` (CTranslate2 backend).

**Rationale:**
- Standard `openai-whisper` is batch-oriented; `faster-whisper` provides 2-4× speedup on CPU with identical accuracy
- `faster-whisper` API is drop-in equivalent — `WhisperModel(model_size).transcribe(audio_array)`
- Supports streaming segments, better for ZENO's <3s response target
- Already listed in `requirements.txt` as `faster-whisper`

**Architecture:** Producer-consumer queue pattern
- `sounddevice` callback → puts raw PCM chunks in `queue.Queue`
- Worker thread pulls from queue → VAD filter → Whisper inference → yields transcript string
- Audio format: 16kHz mono float32 (Whisper native format — avoids resampling overhead)

---

### 2. Wake Word: `openwakeword` over `pvporcupine`

**Decision:** Use `openwakeword` (Apache 2.0).

**Rationale:**
- ZENO is a personal, open-source project — no proprietary API key dependency for core voice
- `openwakeword` runs on CPU, ~30ms inference per 80ms audio frame
- Pre-trained model "hey jarvis" is close; but we need "hey zeno" — openwakeword supports custom training
- **Fallback approach:** Use string matching on short-burst Whisper transcript for robustness — if openwakeword fires OR transcript starts with "hey zeno" / "zeno" → activate
- `pvporcupine` requires AccessKey per-device; problematic for offline-first requirement

**Pattern:**
```python
# 80ms audio frame loop
frame = read_audio_frame(80ms)
score = oww_model.predict(frame)
if score["hey_zeno"] > THRESHOLD:
    activate_listening_mode()
```

---

### 3. Hotkeys: `pynput` over `keyboard`

**Decision:** Use `pynput` (LGPLv3).

**Rationale:**
- `pynput` does NOT require admin privileges on Windows (unlike `keyboard` library)
- Non-blocking listener in daemon thread; signals via `threading.Event`
- Already in `requirements.txt` as `pynput`

**Hotkey mappings:**
- `Ctrl+Shift+Space` → brain dump overlay trigger (signal upstream)
- `Ctrl+Shift+J` held → push-to-talk (press=start, release=stop)

**Pattern:**
```python
# In a daemon thread
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
# Callbacks set threading.Event flags — never block in callback
```

---

### 4. Audio Capture: `sounddevice`

**Decision:** Use `sounddevice` with callback-based non-blocking stream.

**Pattern:**
```python
def audio_callback(indata, frames, time, status):
    audio_queue.put(indata.copy())

with sd.InputStream(samplerate=16000, channels=1, dtype='float32',
                    blocksize=1280,  # 80ms at 16kHz
                    callback=audio_callback):
    # ... wake word loop
```

---

### 5. VAD: Silero VAD (via `torch`)

**Decision:** Use Silero VAD to gate Whisper inference.

**Rationale:** Prevents transcribing silence; eliminates Whisper hallucinations on noise.
Silero VAD is a tiny (1.8MB) LSTM model that runs in <1ms per 30ms frame.
Already in `requirements.txt` indirectly via `torch`.

**However:** For simplicity in Phase 2, implement a **simple energy-based VAD** first
(`numpy` RMS threshold) as the primary guard. Silero can replace it in a future optimization
pass. This avoids a torch dependency just for VAD.

---

## File Structure Confirmed

```
zeno/voice/
├── __init__.py          # Already exists (stub)
├── capture.py           # sounddevice stream + queue
├── wake_word.py         # openwakeword detection loop
├── transcriber.py       # faster-whisper wrapper
└── hotkeys.py           # pynput global hotkey listener
```

## Unit Test Strategy

- `transcriber.py` → mock `WhisperModel`; feed known numpy float32 array → assert transcript string returned
- `hotkeys.py` → test that callbacks set correct `threading.Event` flags
- `capture.py` → test queue receives data (mock sounddevice stream)

---

## Dependency Verification

All required packages are already in `requirements.txt`:
- `faster-whisper` ✓
- `sounddevice` ✓
- `openwakeword` ✓ (check: if missing, add)
- `pynput` ✓
- `numpy` ✓ (transitive via faster-whisper)

> Note: `openwakeword` downloads model files on first run (~50MB). This is expected behavior.
