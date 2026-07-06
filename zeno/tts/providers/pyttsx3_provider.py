from zeno.tts.engine import TTSProvider

class Pyttsx3Provider(TTSProvider):
    def __init__(self, rate: int = 175, volume: float = 1.0):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._available = True
            if self._engine:
                self._engine.setProperty('rate', rate)
                self._engine.setProperty('volume', volume)
        except ImportError:
            self._available = False
            self._engine = None

    def speak_sync(self, text: str) -> None:
        if not self._available or self._engine is None:
            return
        self._engine.say(text)
        self._engine.runAndWait()

    def is_available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return "pyttsx3"
