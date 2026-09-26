"""Tests for SIA Personality, Addressing Rules, and Language Detection."""

import pytest
from backend.agent.personality import (
    FORBIDDEN_NICKNAMES,
    detect_language,
    sanitize_sia_response,
    build_system_prompt,
)


def test_no_forbidden_nicknames_in_sanitizer():
    # If an LLM ever outputs a forbidden word, sanitizer replaces it with 'Sir'
    test_outputs = [
        ("Hey bro, how can I help you?", "Hey Sir, how can I help you?"),
        ("Sure boss, I will check that.", "Sure Sir, I will check that."),
        ("No worries dude, let's fix it.", "No worries Sir, let's fix it."),
        ("Suno bhai, ye idea theek nahi hai.", "Suno Sir, ye idea theek nahi hai."),
        ("Hello buddy, ready when you are.", "Hello Sir, ready when you are."),
    ]
    for raw, expected in test_outputs:
        sanitized = sanitize_sia_response(raw)
        assert sanitized == expected


def test_language_detection():
    # English
    assert detect_language("Please find restaurant leads in Nagpur") == "en"
    # Hindi
    assert detect_language("aaj mujhe kya kaam karna hai batao") in ("hi", "hinglish")
    # Marathi
    assert detect_language("माहित नाही काय करायचे") == "mr"
    # Hinglish
    assert detect_language("YouTube pe Arijit Singh ka song laga") in ("hi", "hinglish")


def test_system_prompt_structure():
    prompt = build_system_prompt([{"category": "projects", "key": "DineMotion", "value": "Web design"}])
    assert "SIA" in prompt
    assert "Sagar" in prompt
    assert "DineMotion" in prompt
    assert "Sir" in prompt
