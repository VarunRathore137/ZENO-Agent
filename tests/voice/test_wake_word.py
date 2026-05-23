import pytest
import numpy as np
import queue
import threading
from unittest.mock import MagicMock, patch
from zeno.voice.wake_word import WakeWordDetector, DEFAULT_THRESHOLD

def test_detector_init():
    with patch("openwakeword.utils.download_models"), \
         patch("openwakeword.model.Model") as mock_model:
        detector = WakeWordDetector()
        assert detector.threshold == DEFAULT_THRESHOLD
        assert not detector.detected.is_set()

@patch("openwakeword.model.Model")
@patch("openwakeword.utils.download_models")
def test_score_frame_conversion(mock_download, mock_model_class):
    mock_model = MagicMock()
    mock_model.predict.return_value = {"hey_jarvis": 0.8}
    mock_model_class.return_value = mock_model
    
    detector = WakeWordDetector()
    audio_frame = np.zeros(1280, dtype=np.float32)
    # Put a value that will be converted to int16
    audio_frame[0] = 0.5
    
    score = detector._score_frame(audio_frame)
    assert score == 0.8
    
    # Verify predict was called with int16 array
    args, _ = mock_model.predict.call_args
    passed_frame = args[0]
    assert passed_frame.dtype == np.int16
    assert passed_frame[0] == int(0.5 * 32768)

@patch("openwakeword.model.Model")
@patch("openwakeword.utils.download_models")
def test_run_loop_detection(mock_download, mock_model_class):
    mock_model = MagicMock()
    mock_model.predict.return_value = {"hey_jarvis": 0.9}
    mock_model_class.return_value = mock_model
    
    detector = WakeWordDetector(threshold=0.5)
    audio_queue = queue.Queue()
    audio_queue.put(np.zeros(1280, dtype=np.float32))
    
    # Start loop in a way we can stop it
    def stop_after_detected():
        if detector.detected.wait(timeout=1.0):
            detector.stop()
            
    threading.Thread(target=stop_after_detected, daemon=True).start()
    detector.run_loop(audio_queue)
    
    assert detector.detected.is_set()
