import queue
import time
import sys
import numpy as np
from pathlib import Path

DEFAULT_MODEL = "base"
SAMPLE_RATE = 16000

class WhisperTranscriber:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize the Whisper transcriber.
        Loads the model on first instantiation via lazy-import.
        """
        try:
            import whisper
            self._model = whisper.load_model(model_name)
            self.model_name = model_name
        except Exception as e:
            print(f"Error loading Whisper model '{model_name}': {e}", file=sys.stderr)
            raise

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en",
        no_speech_threshold: float = 0.5,
        initial_prompt: str | None = None,
    ) -> str:
        """
        Transcribe a float32 numpy array (16kHz mono).
        Returns the transcript string, or "" if Whisper is not confident
        that the audio contains speech (no_speech_prob > no_speech_threshold).

        Args:
            initial_prompt: Optional text to bias Whisper's vocabulary.
                            E.g. "Hey Zeno, Okay Zeno" makes Whisper more
                            likely to output those words for similar sounds.
        """
        try:
            # fp16=False forces CPU-safe mode
            # condition_on_previous_text=False stops Whisper from hallucinating YouTube subtitles ("Thanks for watching")
            result = self._model.transcribe(
                audio,
                language=language,
                fp16=False,
                initial_prompt=initial_prompt,
                condition_on_previous_text=False,
            )

            # Reject clips Whisper itself thinks have no speech.
            # This filters out background TV / ambient noise transcriptions.
            segments = result.get("segments", [])
            if segments:
                avg_no_speech = sum(s.get("no_speech_prob", 0.0) for s in segments) / len(segments)
                if avg_no_speech > no_speech_threshold:
                    return ""

            text = result.get("text", "").strip()
            return text
        except Exception as e:
            print(f"Error during transcription: {e}", file=sys.stderr)
            return ""

    def transcribe_file(self, filepath: str | Path, language: str = "en") -> str:
        """
        Load audio from file and transcribe it.
        """
        try:
            import whisper
            audio = whisper.load_audio(str(filepath))
            return self.transcribe(audio, language)
        except Exception as e:
            print(f"Error transcribing file {filepath}: {e}", file=sys.stderr)
            return ""

def collect_audio(audio_queue: queue.Queue, duration_s: float = 5.0, 
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Read from audio_queue for up to duration_s seconds.
    Concatenates chunks into a single float32 numpy array.
    Stops early if queue is empty for >500ms.
    """
    chunks = []
    start_time = time.time()
    
    while (time.time() - start_time) < duration_s:
        try:
            # Wait up to 500ms for a chunk
            chunk = audio_queue.get(timeout=0.5)
            chunks.append(chunk)
        except queue.Empty:
            # Stop if we hit a silence/gap longer than 500ms
            break
            
    if not chunks:
        return np.array([], dtype=np.float32)
        
    return np.concatenate(chunks)
