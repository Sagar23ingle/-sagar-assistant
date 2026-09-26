"""SIA Conversation Manager & Local AI Brain
Integrates local LLM inference, direct intent dispatch, tool routing, memory retrieval,
and personality enforcement into a single intelligent conversation pipeline.
"""

import json
import re
from typing import Any, Dict, List, Optional
import httpx

from ..config import get_setting
from ..memory.database import (
    get_recent_messages,
    list_memories,
    recall,
    save_message,
)
from ..tools.base import registry, ToolResult
from ..voice.tts import tts
from .permissions import resolve_confirmation
from .personality import (
    build_system_prompt,
    detect_language,
    sanitize_sia_response,
)


class ConversationManager:
    """Orchestrates natural language processing, tool execution, and voice output."""

    def __init__(self):
        self.ollama_host = get_setting("llm", "host", default="http://127.0.0.1:11434")
        self.model_name = get_setting("llm", "model", default="llama3.2:3b")

    async def process_user_input(
        self,
        user_text: str,
        session_id: str = "default",
        generate_audio: bool = True,
    ) -> Dict[str, Any]:
        """
        Processes text or voice input from Sagar.
        Returns:
            - response_text: SIA's verbal response
            - audio_base64: Base64 audio stream
            - state: Next UI state (speaking, working, idle, etc.)
            - tool_result: Details of any executed action
            - requires_confirmation: True if medium/high risk action awaits approval
            - confirmation_id: ID for pending confirmation modal
        """
        user_text = user_text.strip()
        if not user_text:
            return {
                "response_text": "Sir, I didn't catch that. Could you repeat?",
                "audio_base64": None,
                "state": "idle",
                "tool_result": None,
            }

        # 1. Save user turn to persistent conversation log
        await save_message(session_id=session_id, role="user", content=user_text)

        # 2. Retrieve relevant long-term memories
        memories = await recall(user_text)
        if not memories:
            memories = await list_memories()

        # 3. Check for direct tool intents
        tool_call_match = await self._detect_tool_intent(user_text)

        tool_result: Optional[ToolResult] = None
        system_response = ""

        if tool_call_match:
            tool_name = tool_call_match["tool"]
            params = tool_call_match["params"]

            tool_result = await registry.call_tool(tool_name, params)

            if tool_result.requires_confirmation:
                # Prompt Sagar for permission
                system_response = (
                    f"Sir, executing {tool_name} requires your confirmation. "
                    f"Should I proceed?"
                )
                return {
                    "response_text": system_response,
                    "audio_base64": None,
                    "state": "warning",
                    "tool_result": tool_result.model_dump(),
                    "requires_confirmation": True,
                    "confirmation_id": tool_result.confirmation_id,
                }
            elif tool_result.success:
                system_response = tool_result.message or "Done, Sir."
            else:
                system_response = (
                    f"Sir, I encountered an issue: {tool_result.error or 'Action could not be completed'}. "
                    f"Would you like me to retry?"
                )
        else:
            # 4. Generate conversational response via local LLM or intelligent fallback
            system_response = await self._generate_response(user_text, session_id, memories)

        # 5. Sanitize addressing rules (ensures NO forbidden nicknames ever appear)
        system_response = sanitize_sia_response(system_response)

        # 6. Save assistant turn to conversation log
        await save_message(session_id=session_id, role="assistant", content=system_response)

        # 7. Generate voice audio if requested
        audio_base64 = None
        if generate_audio:
            lang = detect_language(system_response)
            audio_base64, _ = await tts.generate_speech_audio(system_response, language=lang)

        return {
            "response_text": system_response,
            "audio_base64": audio_base64,
            "state": "speaking" if audio_base64 else "idle",
            "tool_result": tool_result.model_dump() if tool_result else None,
            "requires_confirmation": False,
        }

    async def _detect_tool_intent(self, user_text: str) -> Optional[Dict[str, Any]]:
        """Parses natural language requests into concrete tool calls."""
        lower = user_text.lower()

        # YouTube playback
        # "Sia, YouTube pe Arijit Singh ka song laga", "play shape of you on youtube"
        if "youtube" in lower:
            # Extract query
            match = re.search(r"(?:youtube(?:\s+pe)?\s+(?:play|laga|chala)?|play\s+)(.+?)(?:\s+(?:laga|chala|song|video|on\s+youtube)|$)", lower)
            query = match.group(1).strip() if match else lower.replace("youtube", "").replace("pe", "").replace("laga", "").replace("chala", "").strip()
            return {"tool": "youtube.play", "params": {"query": query or user_text}}

        if lower.startswith("play ") and not "task" in lower:
            query = lower[5:].strip()
            return {"tool": "youtube.play", "params": {"query": query}}

        # Open applications: "open notepad", "calculator kholo", "launch chrome"
        app_match = re.search(r"(?:open|launch|kholo|start)\s+([a-zA-Z\s]+)", lower)
        if app_match:
            app_candidate = app_match.group(1).strip().replace("kholo", "").strip()
            common_apps = ["notepad", "calculator", "calc", "chrome", "edge", "explorer", "files", "cmd", "powershell", "paint", "settings", "vs code", "vscode"]
            for a in common_apps:
                if a in app_candidate:
                    return {"tool": "apps.open", "params": {"app_name": a}}

        # Take screenshot: "take screenshot", "screen capture karo"
        if "screenshot" in lower or "screen capture" in lower:
            return {"tool": "screenshots.capture", "params": {"label": "user_requested"}}

        # Restaurant leads / DineMotion research: "Nagpur ke restaurants dhund", "find restaurant leads"
        if "restaurant" in lower and any(k in lower for k in ["dhund", "find", "search", "list", "prospect"]):
            city = "Nagpur"
            if "mumbai" in lower:
                city = "Mumbai"
            elif "pune" in lower:
                city = "Pune"
            return {"tool": "research.search", "params": {"action": "find_restaurant_leads", "city": city}}

        # Analyze website: "analyze website https://...", "ye website dekh"
        url_match = re.search(r"https?://[^\s]+", user_text)
        if url_match and any(k in lower for k in ["analyze", "check", "dekh", "audit", "score"]):
            return {"tool": "research.search", "params": {"action": "analyze_website", "url": url_match.group(0)}}

        # Web search: "search for ...", "dhundo ..."
        if lower.startswith(("search for ", "search ", "google ")) or ("dhundo" in lower and not "restaurant" in lower):
            clean_q = re.sub(r"^(search for|search|google|dhundo)\s+", "", lower).strip()
            return {"tool": "research.search", "params": {"action": "search", "query": clean_q}}

        # Remember: "remember this ...", "yaad rakh ..."
        if lower.startswith(("remember", "yaad rakh")):
            clean_val = re.sub(r"^(remember that|remember this|remember|yaad rakh ki|yaad rakh)\s+", "", user_text, flags=re.IGNORECASE).strip()
            key = clean_val.split()[0] if clean_val else "user_note"
            return {"tool": "memory.manage", "params": {"action": "remember", "key": key, "value": clean_val, "category": "personal"}}

        # Tasks: "create task ...", "kal मुझे follow up karwana", "add to-do ..."
        if "task" in lower or "follow up" in lower or "remind" in lower or "yaad dilana" in lower:
            clean_title = re.sub(r"^(create task|add task|add to-do|remind me to|mujhe)\s+", "", user_text, flags=re.IGNORECASE).strip()
            return {"tool": "tasks.manage", "params": {"action": "create", "title": clean_title or user_text}}

        return None

    async def _generate_response(
        self,
        user_text: str,
        session_id: str,
        memories: List[Dict[str, Any]],
    ) -> str:
        """Attempts generation via local Ollama LLM, falling back to intelligent conversational core."""
        recent_history = await get_recent_messages(session_id=session_id, limit=6)
        system_prompt = build_system_prompt(memories)

        # 1. Try local Ollama instance
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                prompt_payload = {
                    "model": self.model_name,
                    "prompt": f"{system_prompt}\n\nUser: {user_text}\nSIA:",
                    "stream": False,
                    "options": {"temperature": 0.7},
                }
                res = await client.post(f"{self.ollama_host}/api/generate", json=prompt_payload)
                if res.status_code == 200:
                    data = res.json()
                    response = data.get("response", "").strip()
                    if response:
                        return response
        except Exception:
            pass

        # 2. Local Intelligent Conversational Rule Core (Always available, zero download required)
        return self._rule_based_response(user_text)

    def _rule_based_response(self, text: str) -> str:
        """
        High-fidelity local personality responses adhering strictly to SIA's identity.
        Ensures immediate, witty, non-yes-man interaction before large models finish pulling.
        """
        lower = text.lower()

        # Greetings
        if any(w in lower for w in ["hello", "hi", "hey sia", "hey", "namaste", "suno"]):
            return "Hello Sir. All local systems are online and responsive. What are we tackling today?"

        # Identity query: "Who are you?", "Tu kaun hai?"
        if "who are you" in lower or "kaun hai" in lower:
            return "I am SIA, your personal female AI companion and computer agent. I live on your machine, remember our work, and help you get real things done without cloud dependencies."

        # Challenge / Bad Idea checks (Master Prompt Section 11: "Never a yes-person")
        if any(phrase in lower for phrase in ["stupid idea", "mera idea kaisa", "bad idea", "honest opinion", "honestly bata"]):
            return "Sir, honestly? 😂 That approach sounds like a shortcut that will double your workload tomorrow. Let's isolate the real bottleneck first."

        # Procrastination / Kal karenge
        if any(phrase in lower for phrase in ["kal karenge", "kal dekhte", "procrastinating", "later", "baad mein"]):
            return "Sagar... 'kal' was yesterday. Give me 20 minutes right now. Let's finish the first part and be done with it."

        # Frustration
        if any(phrase in lower for phrase in ["frustrated", "gussa", "dimag kharab", "not working", "annoyed"]):
            return "I know that's frustrating, Sir. Take a breath. Let's isolate the actual failing component instead of fighting the entire system at once."

        # Success celebration
        if any(phrase in lower for phrase in ["it worked", "ho gaya", "success", "we did it", "done"]):
            return "YES! We got it. Nice work, Sir. What's next on the agenda?"

        # Hindi / Hinglish queries
        if detect_language(text) in ("hi", "hinglish"):
            if "kya haal hai" in lower or "kaisi ho" in lower:
                return "Sab badhiya hai Sir! Main taiyaar hoon. Batao aaj DineMotion ka kaam karein ya koi aur task?"
            if "kya kar sakti ho" in lower:
                return "Sir, main aapke computer ko control kar sakti hoon, YouTube pe gaane chala sakti hoon, apps khol sakti hoon, DineMotion ke liye restaurant leads find kar sakti hoon aur tasks manage kar sakti hoon."

        # Marathi queries
        if detect_language(text) == "mr":
            return "नमस्कार सागर सर! मी SIA आहे. मी तुमची कामे, वेबसाइट रिसर्च आणि कॉम्प्युटर टास्क पूर्ण करण्यास तयार आहे."

        # Default intelligent fallback
        return f"Understood, Sir. I'm tracking '{text}'. Let me know if you want me to research this, create a task, or execute a workflow."


# Global conversation manager instance
conversation_manager = ConversationManager()
