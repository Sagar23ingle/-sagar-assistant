"""SIA Voice Engine: Multilingual Local & Free TTS
Features:
- Primary: edge-tts (100% free, natural neural voices, no API keys or subscription required)
  - English (India): en-IN-NeerjaNeural (expressive female)
  - Hindi: hi-IN-SwaraNeural (natural Hindi female)
  - Marathi: mr-IN-AarohiNeural (natural Marathi female)
- Fallback: pyttsx3 (100% offline local SAPI5 Windows voice)
"""

import asyncio
import base64
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import edge_tts
import pyttsx3
from ..agent.personality import detect_language

EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Free Neural Voice Map
VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
    "hinglish": "hi-IN-SwaraNeural",
}

_is_speaking = False


class TTSProvider:
    """Manages audio generation and speech playback."""

    def __init__(self):
        self.offline_engine = None

    def _get_offline_engine(self):
        if self.offline_engine is None:
            try:
                self.offline_engine = pyttsx3.init()
                # Set female voice if available
                voices = self.offline_engine.getProperty("voices")
                for v in voices:
                    if "zira" in v.name.lower() or "female" in v.name.lower():
                        self.offline_engine.setProperty("voice", v.id)
                        break
            except Exception:
                pass
        return self.offline_engine

    async def generate_speech_audio(
        self,
        text: str,
        language: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Synthesizes text to speech audio.
        Returns: (base64_audio_data, file_path)
        """
        global _is_speaking
        _is_speaking = True

        if not language or language == "auto":
            language = detect_language(text)

        voice = VOICE_MAP.get(language, VOICE_MAP["en"])
        output_filename = f"sia_speech_{os.getpid()}_{int(asyncio.get_event_loop().time() * 1000)}.mp3"
        output_path = EXPORTS_DIR / output_filename

        # 1. Try free neural edge-tts first
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            await communicate.save(str(output_path))

            if output_path.exists() and output_path.stat().st_size > 0:
                audio_bytes = output_path.read_bytes()
                base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                _is_speaking = False
                return base64_audio, str(output_path)
        except Exception:
            pass

        # 2. Offline fallback using pyttsx3
        try:
            wav_filename = output_filename.replace(".mp3", ".wav")
            wav_path = EXPORTS_DIR / wav_filename
            engine = self._get_offline_engine()
            if engine:
                engine.save_to_file(text, str(wav_path))
                engine.runAndWait()
                if wav_path.exists() and wav_path.stat().st_size > 0:
                    audio_bytes = wav_path.read_bytes()
                    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                    _is_speaking = False
                    return base64_audio, str(wav_path)
        except Exception:
            pass

        _is_speaking = False
        return None, None

    def stop(self) -> None:
        """Interrupts and stops speech."""
        global _is_speaking
        _is_speaking = False
        if self.offline_engine:
            try:
                self.offline_engine.stop()
            except Exception:
                pass


# Global singleton instance
tts = TTSProvider()
