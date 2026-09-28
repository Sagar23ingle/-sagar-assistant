"""TTS manager: Gemini neural voice -> Edge-TTS fallback -> graceful degradation."""
from __future__ import annotations
import asyncio
import base64
import logging
import uuid
from pathlib import Path

from ..config import get_gemini_api_key, get_setting

logger = logging.getLogger("sia.tts")


class TTSManager:
    """Manages audio generation with failover from Gemini to Edge-TTS."""

    def __init__(self) -> None:
        self._stop = False

    async def generate_speech_audio(
        self,
        text: str,
        language: str | None = None
    ) -> tuple[str | None, str | None, str | None]:
        """Synthesize speech audio, attempting Gemini first if configured, then Edge-TTS."""
        self._stop = False
        engine = get_setting("voice", "engine", default="gemini").lower()
        has_key = bool(get_gemini_api_key())

        if engine == "gemini" and has_key:
            try:
                from .gemini_tts import generate
                voice = get_setting("ai", "gemini_voice", default="Aoede")
                return await generate(text, voice=voice)
            except Exception as e:
                logger.warning("Gemini TTS failed or timed out: %s; falling back to Edge-TTS", e)

        # Edge-TTS fallback
        return await self._edge(text, language)

    async def _edge(
        self,
        text: str,
        language: str | None = None
    ) -> tuple[str | None, str | None, str | None]:
        try:
            import edge_tts

            voices = {
                "en": "en-IN-NeerjaNeural",
                "hi": "hi-IN-SwaraNeural",
                "mr": "mr-IN-AarohiNeural",
                "hinglish": "hi-IN-SwaraNeural",
            }
            voice = voices.get(language or "en", voices["en"])

            async def _run_stream():
                comm = edge_tts.Communicate(text, voice)
                buf = bytearray()
                async for chunk in comm.stream():
                    if self._stop:
                        return None
                    if chunk.get("type") == "audio":
                        buf.extend(chunk.get("data", b""))
                return buf

            # 12s timeout for Edge-TTS
            buf = await asyncio.wait_for(_run_stream(), timeout=12.0)
            if not buf:
                return None, None, None

            out_dir = Path("data/exports")
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"edge_voice_{uuid.uuid4().hex[:10]}.mp3"
            path.write_bytes(bytes(buf))

            b64 = base64.b64encode(buf).decode("ascii")
            return b64, str(path), "audio/mpeg"

        except Exception as e:
            logger.warning("Edge-TTS generation failed: %s", e)
            return None, None, None

    def stop(self) -> None:
        self._stop = True


tts = TTSManager()
