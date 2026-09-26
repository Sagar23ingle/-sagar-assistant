"""TTS manager: Gemini neural voice -> Edge-TTS fallback."""
from __future__ import annotations
import asyncio, base64, uuid
from pathlib import Path
from ..config import get_setting, get_gemini_api_key

class TTSManager:
    def __init__(self): self._stop=False
    async def generate_speech_audio(self,text:str,language:str|None=None):
        engine=get_setting("voice","engine",default="gemini")
        if engine=="gemini" and get_gemini_api_key():
            try:
                from .gemini_tts import generate
                return await generate(text,get_setting("ai","gemini_voice",default="Charon"))
            except Exception:
                pass
        return await self._edge(text, language)
    async def _edge(self,text,language=None):
        try:
            import edge_tts
            voices={"en":"en-IN-NeerjaNeural","hi":"hi-IN-SwaraNeural","mr":"mr-IN-AarohiNeural","hinglish":"hi-IN-SwaraNeural"}
            voice=voices.get(language or "en",voices["en"])
            comm=edge_tts.Communicate(text,voice)
            buf=bytearray()
            async for chunk in comm.stream():
                if chunk.get("type")=="audio": buf.extend(chunk.get("data",b""))
            out=Path("data/exports"); out.mkdir(parents=True,exist_ok=True)
            path=out/f"edge_voice_{uuid.uuid4().hex[:10]}.mp3"; path.write_bytes(bytes(buf))
            return base64.b64encode(buf).decode("ascii"),str(path),"audio/mpeg"
        except Exception:
            return None,None,None
    def stop(self): self._stop=True

tts=TTSManager()
