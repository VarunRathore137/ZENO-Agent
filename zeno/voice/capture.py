import queue
import sys
import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"


class MicrophoneStream:
    """
    Wraps a sounddevice InputStream and delivers audio frames to all
    registered subscribers via fan-out.

    Usage (single consumer — backwards compatible):
        mic = MicrophoneStream()
        mic.start()
        frame = mic.read(timeout=1.0)   # drains the internal default queue

    Usage (multiple independent consumers — no frame stealing):
        mic = MicrophoneStream()
        q1 = mic.subscribe()   # each subscriber gets its own queue
        q2 = mic.subscribe()
        mic.start()
        # q1 and q2 both receive every frame independently
        mic.unsubscribe(q1)
    """

    def __init__(self, blocksize: int = 1280, maxsize: int = 300):
        self.blocksize = blocksize
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[np.ndarray]] = []
        # Default queue kept for single-reader / backwards-compat use
        self._default_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=maxsize)
        self._subscribers.append(self._default_q)
        self._stream: sd.InputStream | None = None

    # ------------------------------------------------------------------
    # Fan-out pub/sub
    # ------------------------------------------------------------------

    def subscribe(self, maxsize: int | None = None) -> "queue.Queue[np.ndarray]":
        """Return a new queue that will receive every captured frame."""
        q: queue.Queue[np.ndarray] = queue.Queue(maxsize=maxsize or self._maxsize)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: "queue.Queue[np.ndarray]") -> None:
        """Stop delivering frames to a previously subscribed queue."""
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # sounddevice callback — runs on a high-priority audio thread
    # ------------------------------------------------------------------

    def _callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        frame = indata[:, 0].copy()
        with self._lock:
            for q in self._subscribers:
                try:
                    q.put_nowait(frame)
                except queue.Full:
                    # Drop the oldest frame to make room for the new one
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        q.put_nowait(frame)
                    except queue.Full:
                        pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_device() -> int | None:
        """Resolve which input device to use.

        Priority:
          1. ZENO_MIC_DEVICE env var (explicit override, set to device index)
          2. Windows default *communication* device — same one Teams/Cortana use.
             Windows switches this automatically when a headset is plugged in.
          3. sounddevice system default (None) as final fallback.
        """
        import os
        env_dev = os.environ.get("ZENO_MIC_DEVICE", "").strip()
        if env_dev.isdigit():
            idx = int(env_dev)
            name = sd.query_devices(idx)["name"]
            print(f"[ZENO] Mic: using ZENO_MIC_DEVICE=[{idx}] {name}", flush=True)
            return idx

        # Try to get the Windows default *communication* input device index.
        # sounddevice exposes sd.default.device as (input_idx, output_idx).
        # On Windows the default communication device is normally reflected here.
        try:
            default_in = sd.default.device[0]
            if isinstance(default_in, int) and default_in >= 0:
                name = sd.query_devices(default_in)["name"]
                print(f"[ZENO] Mic: using system default [{default_in}] {name}", flush=True)
                return default_in
        except Exception:
            pass

        print("[ZENO] Mic: using sounddevice fallback default", flush=True)
        return None  # sounddevice picks the OS default

    def start(self) -> None:
        device = self._resolve_device()
        self._stream = sd.InputStream(
            device=device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # ------------------------------------------------------------------
    # Single-reader compat — drains the default internal queue
    # ------------------------------------------------------------------

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        """
        Read one frame from the default queue (single-reader API).
        If you need multiple independent readers, use subscribe() instead.
        """
        try:
            return self._default_q.get(timeout=timeout)
        except queue.Empty:
            return None


def list_devices() -> list[dict]:
    return [{"index": i, "name": d["name"]} for i, d in enumerate(sd.query_devices())]
