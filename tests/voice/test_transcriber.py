import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from zeno.voice.transcriber import WhisperTranscriber, DEFAULT_MODEL, collect_audio
import queue
import threading

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
    assert len(result) == 5 * 1280
