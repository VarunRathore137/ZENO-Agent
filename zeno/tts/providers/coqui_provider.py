from zeno.tts.engine import TTSProvider

class CoquiProvider(TTSProvider):
    def speak_sync(self, text: str) -> None:
        raise NotImplementedError("Coqui provider not yet implemented")
        
    def is_available(self) -> bool:
        return False
        
    @property
    def name(self) -> str:
        return "coqui"
