"""Tests for SIA Multilingual TTS Engine."""

import pytest
from pathlib import Path
from backend.voice.tts import tts


@pytest.mark.asyncio
async def test_tts_english_generation():
    text = "Hello Sir, I am SIA. All local systems are functioning normally."
    res = await tts.generate_speech_audio(text, language="en")
    assert len(res) == 3
    base64_audio, file_path, mime_type = res
    assert base64_audio is not None
    assert mime_type in ["audio/wav", "audio/mp3"]
    if file_path:
        assert Path(file_path).exists()


@pytest.mark.asyncio
async def test_tts_hindi_generation():
    text = "नमस्ते सर, मैं सिया हूँ। आपका काम शुरू करें?"
    res = await tts.generate_speech_audio(text, language="hi")
    assert len(res) == 3
    base64_audio, file_path, mime_type = res
    assert base64_audio is not None
    assert mime_type in ["audio/wav", "audio/mp3"]
    if file_path:
        assert Path(file_path).exists()
