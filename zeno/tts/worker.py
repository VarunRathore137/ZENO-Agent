import queue
import threading
import sys
from zeno.tts.engine import TTSProvider

_SENTINEL = None  # signals worker to stop

class TTSWorker:
    def __init__(self, provider: TTSProvider) -> None:
        self._provider = provider
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="TTSWorker")
        self._thread.start()

    def enqueue(self, text: str) -> None:
        """Non-blocking. Called from any thread (asyncio, APScheduler, etc.)."""
        self._queue.put(text)

    def flush(self) -> None:
        """Drain the queue immediately. Used for interrupt ('stop speaking')."""
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def stop(self) -> None:
        """Signal the worker thread to exit cleanly."""
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is _SENTINEL:
                break
            try:
                self._provider.speak_sync(item)
            except Exception as e:
                print(f"[TTSWorker] speak error: {e}", file=sys.stderr)
