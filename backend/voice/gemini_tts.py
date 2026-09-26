"""Gemini 3.8 neural TTS using the Charon voice by default."""
from __future__ import annotations
import asyncio, base64, uuid
from pathlib import Path
from ..config import get_gemini_api_key, get_setting

async def generate(text:str, voice:str|None=None)->tuple[str,str,str]:
    key=get_gemini_api_key()
    if not key: raise RuntimeError("Gemini API key not configured")
    from google import genai
    voice_name=voice or get_setting("ai","gemini_voice",default="Charon")
    model=get_setting("ai","gemini_tts_model",default="gemini-3.8-flash-tts")
    client=genai.Client(api_key=key)
    interaction=await asyncio.to_thread(client.interactions.create, model=model, input=[{
        "type":"user_input","content":[{"type":"text","text":text,"annotations":[{"type":"speech_metadata","style":"natural, warm, confident, conversational personal assistant"}]}]
    }], response_format={"type":"audio"}, generation_config={"speech_config":[{"voice":voice_name}]})
    raw=base64.b64decode(interaction.output_audio.data)
    out=Path("data/exports"); out.mkdir(parents=True,exist_ok=True)
    path=out/f"gemini_voice_{uuid.uuid4().hex[:10]}.wav"; path.write_bytes(raw)
    return base64.b64encode(raw).decode("ascii"),str(path),"audio/wav"
