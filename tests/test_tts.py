"""Tests for SIA Free Multilingual TTS Engine."""

import pytest
from pathlib import Path
from backend.voice.tts import tts


@pytest.mark.asyncio
async def test_tts_english_generation():
    text = "Hello Sir, I am SIA. All local systems are functioning normally."
    base64_audio, file_path = await tts.generate_speech_audio(text, language="en")
    assert base64_audio is not None
    assert file_path is not None
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000


@pytest.mark.asyncio
async def test_tts_hindi_generation():
    text = "नमस्ते सर, मैं सिया हूँ। आपका काम शुरू करें?"
    base64_audio, file_path = await tts.generate_speech_audio(text, language="hi")
    assert base64_audio is not None
    assert file_path is not None
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000
