import hashlib
import re
import tempfile
import os
from pathlib import Path
from datetime import datetime
from zeno.tts.engine import TTSProvider
from zeno.tts.providers.pyttsx3_provider import Pyttsx3Provider

def _is_static(text: str) -> bool:
    """Return True only if text contains NONE of: any digit, any date word."""
    return bool(re.fullmatch(r"[A-Za-z ,.'!?-]+", text))

def _cache_path(text: str) -> Path:
    cache_dir = Path.home() / "Zeno" / "tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / (hashlib.sha256(text.encode()).hexdigest() + ".mp3")

def _load_cache(path: Path) -> bytes | None:
    if not path.exists():
        return None
    
    # 30 day TTL
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if (datetime.now() - mtime).days > 30:
        path.unlink(missing_ok=True)
        return None
        
    cached = path.read_bytes()
    
    # Check total cache size and evict if > 50MB
    cache_dir = path.parent
    total_size = sum(f.stat().st_size for f in cache_dir.iterdir() if f.is_file())
    if total_size > 50 * 1024 * 1024:
        files = sorted([f for f in cache_dir.iterdir() if f.is_file()], key=lambda f: f.stat().st_mtime)
        for f in files:
            total_size -= f.stat().st_size
            f.unlink(missing_ok=True)
            if total_size <= 50 * 1024 * 1024:
                break
                
    return cached

def _save_cache(path: Path, audio_bytes: bytes) -> None:
    path.write_bytes(audio_bytes)
    
    # Check total cache size and evict if > 50MB
    cache_dir = path.parent
    total_size = sum(f.stat().st_size for f in cache_dir.iterdir() if f.is_file())
    if total_size > 50 * 1024 * 1024:
        files = sorted([f for f in cache_dir.iterdir() if f.is_file()], key=lambda f: f.stat().st_mtime)
        for f in files:
            total_size -= f.stat().st_size
            f.unlink(missing_ok=True)
            if total_size <= 50 * 1024 * 1024:
                break

class ElevenLabsProvider(TTSProvider):
    def __init__(self, api_key: str | None):
        self._announced_fallback: bool = False
        self._fallback_provider: Pyttsx3Provider = Pyttsx3Provider()
        
        if api_key is None:
            self._available = False
            return
            
        try:
            from elevenlabs import ElevenLabs, play
            self._client = ElevenLabs(api_key=api_key)
            self._play = play
            self._available = True
        except ImportError:
            self._available = False
            
    def _fallback(self, text: str, reason: str) -> None:
        if not self._announced_fallback:
            self._announced_fallback = True
            self._fallback_provider.speak_sync("Switched to offline voice. ElevenLabs unavailable.")
        self._fallback_provider.speak_sync(text)

    def speak_sync(self, text: str) -> None:
        if not self._available:
            return self._fallback(text, "unavailable")
            
        if _is_static(text):
            path = _cache_path(text)
            cached = _load_cache(path)
            if cached:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(cached)
                    tmp = f.name
                try:
                    self._play(open(tmp, "rb"))
                finally:
                    os.unlink(tmp)
                return
                
        try:
            audio = self._client.text_to_speech.convert(
                voice_id="Rachel", model_id="eleven_monolingual_v1", text=text
            )
            audio_bytes = b"".join(audio)
            self._play(audio_bytes)
            if _is_static(text):
                _save_cache(_cache_path(text), audio_bytes)
        except Exception as e:
            self._fallback(text, str(e))

    def is_available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return "elevenlabs"
