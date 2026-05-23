import threading
import queue
import time
import sys
import numpy as np

DEFAULT_THRESHOLD = 0.5
FRAME_SAMPLES = 1280  # 80ms at 16kHz

class WakeWordDetector:
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Initialize the wake word detector.
        Downloads models on first run via lazy-import.
        """
        try:
            import openwakeword
            openwakeword.utils.download_models()
            from openwakeword.model import Model
            self._model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        except Exception as e:
            print(f"Error initializing openwakeword: {e}", file=sys.stderr)
            raise

        self.threshold = threshold
        self.detected = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _score_frame(self, audio_frame: np.ndarray) -> float:
        """
        Convert float32 audio frame to int16 and score it.
        """
        # openwakeword requires int16 PCM
        frame_int16 = (audio_frame * 32768).astype(np.int16)
        
        # predict returns a dict of {model_name: score}
        scores = self._model.predict(frame_int16)
        
        if not scores:
            return 0.0
            
        return max(scores.values())

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
                time.sleep(0.1) # Avoid tight loop on persistent error

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
            name="WakeWordDetectorThread"
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

def create_detector(threshold: float = DEFAULT_THRESHOLD) -> WakeWordDetector:
    """
    Factory function to create a WakeWordDetector.
    """
    return WakeWordDetector(threshold=threshold)
