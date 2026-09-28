"""Gemini Neural TTS using Google GenAI audio modality with PCM to WAV packaging."""
from __future__ import annotations
import asyncio
import base64
import io
import logging
import uuid
import wave
from pathlib import Path

from ..config import get_gemini_api_key, get_setting

logger = logging.getLogger("sia.tts.gemini")

SUPPORTED_GEMINI_VOICES = [
    "Aoede", "Charon", "Puck", "Kore", "Fenrir", "Leda", "Callirrhoe"
]


async def generate(text: str, voice: str | None = None) -> tuple[str, str, str]:
    """Generate high-fidelity neural speech audio using Gemini GenAI SDK.
    
    Returns:
        (base64_audio, file_path, mime_type)
    """
    key = get_gemini_api_key()
    if not key:
        raise RuntimeError("Gemini API key not configured")

    from google import genai
    from google.genai import types

    voice_name = voice or get_setting("ai", "gemini_voice", default="Aoede")
    if voice_name not in SUPPORTED_GEMINI_VOICES:
        voice_name = "Aoede"

    model = get_setting("ai", "gemini_tts_model", default="gemini-2.5-flash-preview-tts")
    client = genai.Client(api_key=key)

    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
        temperature=0.6,
    )

    # 15s timeout on TTS generation
    res = await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=text,
            config=cfg,
        ),
        timeout=15.0,
    )

    candidates = getattr(res, "candidates", None) or []
    if not candidates:
        raise RuntimeError("Gemini TTS returned no candidates")

    parts = candidates[0].content.parts
    audio_parts = [p for p in parts if getattr(p, "inline_data", None)]
    if not audio_parts:
        raise RuntimeError("No audio data stream returned in candidate parts")

    inline = audio_parts[0].inline_data
    raw_bytes = inline.data
    mime = inline.mime_type or "audio/L16;codec=pcm;rate=24000"

    # Convert raw 24kHz 16-bit mono PCM into standard WAV
    if "pcm" in mime.lower() or "l16" in mime.lower():
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(raw_bytes)
        audio_bytes = wav_buf.getvalue()
        final_mime = "audio/wav"
    else:
        audio_bytes = raw_bytes
        final_mime = mime

    out_dir = Path("data/exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"gemini_voice_{uuid.uuid4().hex[:10]}.wav"
    file_path.write_bytes(audio_bytes)

    b64 = base64.b64encode(audio_bytes).decode("ascii")
    return b64, str(file_path), final_mime
