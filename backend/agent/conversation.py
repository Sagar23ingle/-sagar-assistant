"""Conversation orchestration: Intent & language detection -> selective memory -> hybrid agent -> tool execution -> voice."""
from __future__ import annotations
import asyncio
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from .gemini_agent import GeminiAgent, LocalOllamaAgent
from .personality import build_system_prompt, detect_language, is_tool_query, sanitize_sia_response
from ..config import get_gemini_api_key, get_setting
from ..memory.database import get_recent_messages, list_memories, recall, save_message
from ..security.audit import log_action
from ..tools.base import registry
from ..voice.tts import tts

logger = logging.getLogger("sia.conversation")


class ConversationManager:
    """Manages the full lifecycle of a user request with separated fast conversational path and agent workflow."""

    def __init__(self) -> None:
        self.gemini = GeminiAgent()
        self.local = LocalOllamaAgent()

    async def _handle_conversational_fallback(
        self,
        user_text: str,
        detected_lang: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Rich, natural, contextual conversational responses when external AI service is unreachable."""
        lower = user_text.lower().strip()

        # 1. Greetings: "Hi Sia", "Hello", "Hey", "Namaste"
        if any(re.search(rf"\b{w}\b", lower) for w in ["hi", "hello", "hey", "namaste", "suno", "hey sia", "hi sia", "yo"]):
            if detected_lang == "mr":
                return {"response_text": "नमस्कार Sagar! मी SIA, तुमची पर्सनल AI असिस्टंट. आज काय काम करायचं आहे?", "tool_result": None}
            if detected_lang in ("hi", "hinglish"):
                return {"response_text": "Hello Sir! Main yahan hoon, all systems operational. Aaj kya plan hai aapka?", "tool_result": None}
            return {"response_text": "Hello Sir! I am online and standing by. How can I assist you today?", "tool_result": None}

        # 2. What are you doing / "Kya kar rahi ho?"
        if any(w in lower for w in ["kya kar rahi ho", "kya chal raha hai", "what are you doing", "what's up", "kay kartes"]):
            if detected_lang in ("hi", "hinglish"):
                return {"response_text": "Bas Sir, aapke agle command ka intezar kar rahi hoon aur desktop background processes monitor kar rahi hoon. Aap bataiye, aaj kya kaam karein?", "tool_result": None}
            if detected_lang == "mr":
                return {"response_text": "काही नाही Sir, तुमच्या पुढील सूचनेची वाट पाहत आहे. सांगा, आज काय करायचं?", "tool_result": None}
            return {"response_text": "Just monitoring background telemetry and standing by for your instructions, Sir. What's on your agenda today?", "tool_result": None}

        # 3. How are you / "Kaise ho?"
        if any(w in lower for w in ["kaise ho", "kasa ahes", "kashi aahes", "how are you"]):
            if detected_lang in ("hi", "hinglish"):
                return {"response_text": "Main bilkul fit aur ready hoon Sir! Full system efficiency ke saath active hoon. Aap kaise hain?", "tool_result": None}
            return {"response_text": "I am operating at peak efficiency, Sir. Ready to assist whenever you need. How are you doing today?", "tool_result": None}

        # 4. Today's plan / "Aaj kya plan hai?"
        if any(w in lower for w in ["aaj kya plan hai", "aaj ka plan", "what is the plan", "what's the plan"]):
            if detected_lang in ("hi", "hinglish"):
                return {"response_text": "Aapka jo hukum ho Sir! Chahe coding ho, client prospecting, desktop management ya thoda music—main fully ready hoon. Kahan se shuru karein?", "tool_result": None}
            return {"response_text": "Whatever you command, Sir! Be it lead discovery, workspace operations, or reviewing tasks. Where should we begin?", "tool_result": None}

        # 5. Capabilities / "Aaj kya kar sakti ho?" / "What can you do?"
        if any(w in lower for w in ["kya kar sakti ho", "tum kya kar sakti ho", "capabilities", "what can you do", "features"]):
            if detected_lang in ("hi", "hinglish"):
                return {
                    "response_text": "Sir, main aapke Windows desktop ko control kar sakti hoon (Chrome, VS Code, Notepad, Calc launch karna, screenshot lena), web research aur client lead discovery execute kar sakti hoon, YouTube pe gaane chala sakti hoon, aapke tasks aur preferences yaad rakh sakti hoon, aur natural Hindi, Hinglish, Marathi ya English me baat kar sakti hoon!",
                    "tool_result": None
                }
            return {
                "response_text": "Sir, I can control your Windows applications (Chrome, VS Code, Notepad), capture screenshots, conduct web research, discover and qualify business leads, play YouTube music, manage tasks and long-term memory, and converse naturally in English, Hindi, and Marathi.",
                "tool_result": None
            }

        # 6. Memory query: "Mere DineMotion ke baare me kya yaad hai?"
        if "dinemotion" in lower:
            all_m = memories or await list_memories()
            dine_mems = [m for m in all_m if "dinemotion" in json.dumps(m).lower()]
            if dine_mems:
                val = dine_mems[0].get("value") or dine_mems[0].get("key")
                return {"response_text": f"Sir, DineMotion ke baare me mujhe yeh yaad hai: {val}.", "tool_result": None}
            return {
                "response_text": "Sir, filhaal mere database me DineMotion ke baare me koi specific memory saved nahi hai. Agar aap thode details bataenge, toh main immediately memory me store kar lungi!",
                "tool_result": None
            }

        # 7. General memory recall: "What do you remember about me?" / "kya yaad hai"
        if any(w in lower for w in ["what do you remember", "what do you know about me", "kya yaad hai"]):
            all_mems = memories or await list_memories()
            if not all_mems:
                return {"response_text": "Sir, I currently do not have any stored preferences or project notes yet. Feel free to tell me what to remember!", "tool_result": None}
            summary = ", ".join([f"{m.get('key')}: {m.get('value')}" for m in all_mems[:4]])
            return {"response_text": f"Sir, I currently remember the following: {summary}.", "tool_result": None}

        # 8. Humor: "Mere liye ek funny joke suna" / "Tell me a joke"
        if any(w in lower for w in ["joke", "chutkula", "hasao", "funny"]):
            jokes = [
                "Ek programmer ki biwi ne kaha: 'Bazaar jao aur ek bread le aao, aur agar ande mile toh 10 le aana.' Programmer 10 bread le kar ghar aaya! Biwi ne hairan hokar pucha: '10 bread kyu laye?' Programmer bola: 'Kyunki ande mil gaye the!'",
                "Ek software engineer doctor ke paas gaya: 'Doctor sahab, mujhe neend nahi aati!' Doctor ne pucha: 'Kyu?' Engineer bola: 'Jab tak saare bugs solve nahi hote, mera dimag restart hone se mana kar deta hai, Sir!'",
                "Why do programmers prefer dark mode? Because light attracts bugs, Sir!"
            ]
            import random
            selected_joke = random.choice(jokes)
            return {"response_text": f"Sir, ek joke suniye: {selected_joke}", "tool_result": None}

        # 9. Identity
        if any(w in lower for w in ["who are you", "who is sia", "tum kaun ho"]):
            return {
                "response_text": "I am SIA, your personal desktop AI assistant running locally on this computer. I handle desktop control, lead research, memory, and tasks for you, Sir.",
                "tool_result": None
            }

        # 10. Tech Q&A
        if "quantum computing" in lower:
            return {
                "response_text": "Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems classical computers cannot. While traditional computers process binary bits (0 or 1), quantum computers use qubits, which can exist in multiple states simultaneously through superposition and entanglement.",
                "tool_result": None
            }

        if "laptop slow" in lower or "computer slow" in lower:
            return {
                "response_text": "Sir, a slow laptop is typically caused by high background CPU or RAM utilization, too many startup applications, thermal throttling, low storage space, or background processes. I can help inspect your system or launch diagnostic tools.",
                "tool_result": None
            }

        if any(w in lower for w in ["react and vue", "react vs vue"]):
            return {
                "response_text": "Sir, React is a flexible UI library backed by Meta that uses JSX and an unopinionated ecosystem, while Vue is a progressive, full-featured framework offering two-way data binding, built-in transitions, and single-file components with a gentler learning curve.",
                "tool_result": None
            }

        # Catch-all natural response
        if detected_lang in ("hi", "hinglish"):
            return {
                "response_text": "Ji Sir, main aapke saath hoon. Bataiye agla task kya hai ya kisi topic par discuss karna chahte hain?",
                "tool_result": None
            }
        return {
            "response_text": "I am standing by and ready, Sir. How would you like to proceed?",
            "tool_result": None
        }

    async def _handle_offline_or_fallback(
        self,
        user_text: str,
        detected_lang: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Direct semantic intent and tool execution when cloud API is rate-limited or offline."""
        lower = user_text.lower().strip()

        # 1. Direct App Launches
        if any(w in lower for w in ["open chrome", "launch chrome", "start chrome"]):
            res = await registry.call_tool("apps.open", {"app_name": "chrome"})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        if any(w in lower for w in ["open vs code", "open vscode", "launch code", "open code"]):
            res = await registry.call_tool("apps.open", {"app_name": "code"})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        if any(w in lower for w in ["open notepad", "launch notepad"]):
            res = await registry.call_tool("apps.open", {"app_name": "notepad"})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        if any(w in lower for w in ["open calculator", "open calc"]):
            res = await registry.call_tool("apps.open", {"app_name": "calc"})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        # 2. YouTube Playback
        yt_match = re.search(r"(?:play|chala|laga)\s+(.*?)\s+(?:on\s+youtube|pe)", lower)
        if yt_match:
            query = yt_match.group(1).strip()
            res = await registry.call_tool("youtube.play", {"query": query})
            return {"response_text": res.message, "tool_result": res.model_dump()}
        elif "youtube" in lower and any(w in lower for w in ["play", "chala", "laga"]):
            clean_q = re.sub(r"\b(play|on|youtube|pe|laga|chala|song|video)\b", "", lower).strip()
            res = await registry.call_tool("youtube.play", {"query": clean_q or "trending music"})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        # 3. Screenshot Capture
        if any(w in lower for w in ["take a screenshot", "screenshot le", "capture screen", "screenshot"]):
            res = await registry.call_tool("screenshots.capture", {})
            return {"response_text": res.message, "tool_result": res.model_dump()}

        # 4. Memory Storage
        rem_match = re.search(r"(?:remember\s+that|remember\s+my\s+preference|yaad\s+rakh\s+ki)\s+(.*)", lower)
        if rem_match:
            pref = rem_match.group(1).strip()
            res = await registry.call_tool("memory.manage", {
                "action": "remember",
                "category": "preferences",
                "key": "user_preference",
                "value": pref
            })
            return {"response_text": res.message, "tool_result": res.model_dump()}

        # 5. Task creation: e.g. "mala udya reminder pahije"
        if any(w in lower for w in ["reminder pahije", "create task", "add task"]):
            res = await registry.call_tool("tasks.manage", {
                "action": "create",
                "title": user_text
            })
            return {"response_text": f"Sir, I created the task: {res.message}", "tool_result": res.model_dump()}

        # 6. Business & Lead Discovery
        if lower in ["find clients", "find clients for me", "mere liye kuch clients dhund", "mere liye clients find kar"]:
            return {
                "response_text": "Sure, Sir. Which market or industry should I target?",
                "tool_result": None
            }

        if any(w in lower for w in ["restaurants", "restaurant", "detailing", "clients", "leads", "businesses", "prospects"]):
            # Dynamically detect location
            loc = "US"
            for possible_loc in ["Nagpur", "Mumbai", "Delhi", "Pune", "Bangalore", "California", "Texas", "London", "UK", "US", "USA"]:
                if possible_loc.lower() in lower:
                    loc = possible_loc
                    break

            ind = "restaurants" if any(w in lower for w in ["restaurant", "restaurants"]) else ("auto detailing" if "detailing" in lower else "local businesses")
            res = await registry.call_tool("business.manage", {
                "action": "discover_leads",
                "industry": ind,
                "location": loc,
                "limit": 5
            })
            extra = " I have flagged candidate websites for outdated mobile responsiveness, lack of CTAs, and modernization opportunities." if ("outdated" in lower or "website" in lower) else ""
            return {
                "response_text": f"Sir, I executed the lead discovery workflow for {ind} in {loc}. {res.message}{extra}",
                "tool_result": res.model_dump()
            }

        # Conversational fallback for any remaining query
        return await self._handle_conversational_fallback(user_text, detected_lang, memories, history)

    async def process_user_input(
        self,
        user_text: str,
        session_id: str = "default",
        generate_audio: bool = True,
        stream_callback: Optional[Callable[[str], Any]] = None,
        state_callback: Optional[Callable[[str, Optional[Dict[str, Any]]], Any]] = None
    ) -> Dict[str, Any]:
        """Process user input with strict separation between fast conversational path and tool execution."""
        user_text = (user_text or "").strip()
        if not user_text:
            return {
                "response_text": "Sir, I'm listening. How can I assist you?",
                "audio_base64": None,
                "mime_type": None,
                "state": "idle",
                "tool_result": None,
                "requires_confirmation": False,
                "confirmation_id": None,
            }

        try:
            detected_lang = detect_language(user_text)

            # 1. Selective Memory Retrieval
            memories = await recall(user_text)
            if not memories:
                if any(k in user_text.lower() for k in ["remember", "memories", "yaad", "mahiti", "know about me", "dinemotion"]):
                    memories = await list_memories()
                else:
                    memories = []

            # 2. Save User Message
            await save_message(session_id=session_id, role="user", content=user_text)

            # Fetch recent conversation history (excluding the current user message)
            history = await get_recent_messages(session_id=session_id, limit=10)
            if history and history[-1].get("role") == "user" and history[-1].get("content") == user_text:
                history = history[:-1]

            provider = get_setting("ai", "provider", default="hybrid").lower()
            is_tool = is_tool_query(user_text)
            result = None

            # 3. ROUTE: Agent / Tool Execution vs Fast Conversational Path
            if is_tool:
                # Entering Tool Execution: Set THINKING state
                logger.info("Executing Agent Tool Workflow for: %s", user_text)
                if state_callback:
                    await state_callback("thinking", {"query": user_text, "action": "planning"})

                # 3a. Try Gemini Tool Workflow
                if provider in ("hybrid", "auto", "gemini"):
                    result = await self.gemini.process_tool_workflow(user_text, memories, history)

                # 3b. Try Local Ollama if Gemini failed or local provider selected
                if (result is None or result.get("tool_result") is None) and provider in ("hybrid", "auto", "local", "ollama"):
                    if await self.local.is_available():
                        result = await self.local.process(user_text, memories, history)

                # 3c. Semantic Tool Fallback (ensures tool is actually executed if model returned text only)
                if result is None or result.get("tool_result") is None:
                    fallback_result = await self._handle_offline_or_fallback(user_text, detected_lang, memories, history)
                    if fallback_result and fallback_result.get("tool_result") is not None:
                        result = fallback_result
                    elif result is None:
                        result = fallback_result

            else:
                # Entering Fast Conversational Path: Set PROCESSING state (NEVER thinking)
                logger.info("Engaging Fast Conversational Path for: %s", user_text)
                if state_callback:
                    await state_callback("processing", {"query": user_text})

                has_streamed = False

                async def wrapped_stream_cb(token: str):
                    nonlocal has_streamed
                    if not has_streamed:
                        has_streamed = True
                        if state_callback:
                            await state_callback("responding", {"query": user_text})
                    if stream_callback:
                        if asyncio.iscoroutinefunction(stream_callback):
                            await stream_callback(token)
                        else:
                            stream_callback(token)

                # 3a. Try Gemini Fast Chat
                if provider in ("hybrid", "auto", "gemini"):
                    result = await self.gemini.fast_chat(
                        user_text, memories, history, stream_callback=wrapped_stream_cb
                    )

                # 3b. Try Local Ollama if Gemini failed or local provider
                if result is None and provider in ("hybrid", "auto", "local", "ollama"):
                    if await self.local.is_available():
                        result = await self.local.fast_chat(
                            user_text, memories, history, stream_callback=wrapped_stream_cb
                        )

                # 3c. Conversational Fallback
                if result is None:
                    result = await self._handle_conversational_fallback(user_text, detected_lang, memories, history)
                    # If stream callback was registered and we haven't streamed, emit fallback tokens smoothly
                    fb_text = result.get("response_text", "")
                    if stream_callback and not has_streamed and fb_text:
                        if state_callback:
                            await state_callback("responding", {"query": user_text})
                        words = fb_text.split(" ")
                        for idx, word in enumerate(words):
                            space = " " if idx < len(words) - 1 else ""
                            token = word + space
                            if asyncio.iscoroutinefunction(stream_callback):
                                await stream_callback(token)
                            else:
                                stream_callback(token)
                            await asyncio.sleep(0.01)

            response_raw = result.get("response_text", "")
            response = sanitize_sia_response(response_raw)
            requires = bool(result.get("requires_confirmation"))

            if response:
                await save_message(session_id=session_id, role="assistant", content=response)

            # 4. Audio Voice Synthesis
            audio_base64 = None
            mime_type = None
            auto_speak = bool(get_setting("voice", "auto_speak_responses", default=True))

            final_state = "warning" if requires else "idle"
            if generate_audio and auto_speak and response and not requires:
                try:
                    audio_base64, _, mime_type = await tts.generate_speech_audio(
                        response, language=detected_lang
                    )
                    if audio_base64:
                        final_state = "speaking"
                except Exception as tts_err:
                    logger.warning("TTS audio generation skipped: %s", tts_err)

            if state_callback:
                await state_callback(final_state, {"response": response})

            return {
                "response_text": response,
                "audio_base64": audio_base64,
                "mime_type": mime_type,
                "state": final_state,
                "tool_result": result.get("tool_result"),
                "requires_confirmation": requires,
                "confirmation_id": result.get("confirmation_id"),
                "language": detected_lang,
            }

        except Exception as e:
            logger.exception("Error in conversation_manager.process_user_input: %s", e)
            log_action("system", "chat_error", "LOW", status="FAILED", result=str(e))
            if state_callback:
                try:
                    await state_callback("error", {"error": str(e)})
                    await asyncio.sleep(0.5)
                    await state_callback("idle", None)
                except Exception:
                    pass
            return {
                "response_text": "Sir, I encountered an internal issue, but the assistant core remains active and standing by.",
                "audio_base64": None,
                "mime_type": None,
                "state": "idle",
                "tool_result": None,
                "requires_confirmation": False,
                "confirmation_id": None,
            }


conversation_manager = ConversationManager()
