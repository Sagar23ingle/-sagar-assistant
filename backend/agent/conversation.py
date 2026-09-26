"""Conversation orchestration: memory -> hybrid agent -> tool execution -> voice."""
from __future__ import annotations
from typing import Any, Dict, Optional
from .gemini_agent import GeminiAgent, LocalOllamaAgent
from .personality import sanitize_sia_response, detect_language
from ..memory.database import get_recent_messages, recall, list_memories, save_message
from ..voice.tts import tts

class ConversationManager:
    def __init__(self):
        self.gemini = GeminiAgent()
        self.local = LocalOllamaAgent()

    async def process_user_input(self, user_text: str, session_id: str = "default", generate_audio: bool = True) -> Dict[str, Any]:
        user_text = (user_text or "").strip()
        if not user_text:
            return {"response_text": "Sir, I didn't catch that.", "audio_base64": None, "state": "idle", "tool_result": None}

        memories = await recall(user_text)
        if not memories:
            memories = await list_memories()
        await save_message(session_id=session_id, role="user", content=user_text)
        history = await get_recent_messages(session_id=session_id, limit=10)
        if history and history[-1].get("role") == "user" and history[-1].get("content") == user_text:
            history = history[:-1]

        result = await self.gemini.process(user_text, memories, history)
        if result is None:
            result = await self.local.process(user_text, memories, history)
        if result is None:
            result = {"response_text": "Sir, the local AI engine is unavailable. Start Ollama or configure a Gemini API key in Settings.", "tool_result": None}

        response = sanitize_sia_response(result.get("response_text", ""))
        requires = bool(result.get("requires_confirmation"))
        if response:
            await save_message(session_id=session_id, role="assistant", content=response)

        audio = None
        mime_type = None
        state = "warning" if requires else "idle"
        if generate_audio and response and not requires:
            try:
                audio, _, mime_type = await tts.generate_speech_audio(response, language=detect_language(response))
                state = "speaking" if audio else "idle"
            except Exception:
                audio = None

        return {
            "response_text": response,
            "audio_base64": audio,
            "mime_type": mime_type,
            "state": state,
            "tool_result": result.get("tool_result"),
            "requires_confirmation": requires,
            "confirmation_id": result.get("confirmation_id"),
        }

conversation_manager = ConversationManager()
