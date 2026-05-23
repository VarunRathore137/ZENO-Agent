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
