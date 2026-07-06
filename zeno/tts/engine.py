import sys
from abc import ABC, abstractmethod

class TTSProvider(ABC):
    @abstractmethod
    def speak_sync(self, text: str) -> None: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
    
    @property
    @abstractmethod
    def name(self) -> str: ...

def create_provider(engine_name: str, **kwargs) -> TTSProvider:
    if engine_name == "pyttsx3":
        from zeno.tts.providers.pyttsx3_provider import Pyttsx3Provider
        return Pyttsx3Provider()
    elif engine_name == "elevenlabs":
        from zeno.tts.providers.elevenlabs_provider import ElevenLabsProvider
        return ElevenLabsProvider(api_key=kwargs.get("elevenlabs_api_key"))
    elif engine_name == "coqui":
        from zeno.tts.providers.coqui_provider import CoquiProvider
        return CoquiProvider()
    else:
        print(f"Warning: Unknown TTS engine '{engine_name}', falling back to pyttsx3", file=sys.stderr)
        from zeno.tts.providers.pyttsx3_provider import Pyttsx3Provider
        return Pyttsx3Provider()
