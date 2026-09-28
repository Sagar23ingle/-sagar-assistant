"""Hybrid Gemini / Ollama agent with robust function calling, timeouts, and quota fallbacks."""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from ..config import get_gemini_api_key, get_setting
from ..tools.base import registry
from ..security.audit import log_action
from .personality import build_system_prompt

logger = logging.getLogger("sia.agent")


def alias(tool_name: str) -> str:
    """Format tool name as a valid identifier for Gemini/Ollama."""
    return tool_name.replace(".", "_").replace("-", "_")


def tool_manifest():
    """Generates valid Google GenAI types.FunctionDeclaration objects and alias reverse mapping."""
    from google.genai import types
    declarations = []
    reverse = {}
    
    for tool in registry.list_definitions():
        a = alias(tool.name)
        reverse[a] = tool.name
        params = tool.parameters or {"type": "object", "properties": {}}
        
        # Build clean Gemini Schema properties
        props = params.get("properties", {})
        clean_props = {}
        for prop_name, prop_val in props.items():
            p_type = prop_val.get("type", "string").upper()
            prop_def: Dict[str, Any] = {"type": p_type}
            if "description" in prop_val:
                prop_def["description"] = prop_val["description"]
            if "enum" in prop_val:
                prop_def["enum"] = prop_val["enum"]
            clean_props[prop_name] = prop_def
            
        clean_schema: Dict[str, Any] = {
            "type": "OBJECT",
            "properties": clean_props
        }
        if "required" in params and params["required"]:
            clean_schema["required"] = params["required"]
            
        declarations.append(types.FunctionDeclaration(
            name=a,
            description=tool.description,
            parameters=clean_schema
        ))
        
    return declarations, reverse


FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash"
]


class GeminiAgent:
    """Primary Gemini cloud reasoning agent with separated fast conversational path and tool agent."""

    def __init__(self) -> None:
        pass

    def _get_candidate_models(self) -> List[str]:
        cfg_model = get_setting("ai", "gemini_model", default="gemini-3.5-flash-lite")
        models = [cfg_model] + FALLBACK_MODELS
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for m in models:
            if m and m not in seen:
                seen.add(m)
                deduped.append(m)
        return deduped

    async def fast_chat(
        self,
        user_text: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
        stream_callback: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Fast direct conversational path without tool declarations or planning overhead."""
        key = get_gemini_api_key()
        provider = get_setting("ai", "provider", default="hybrid").lower()
        if not key or provider in ("local", "ollama"):
            return None

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google.genai SDK not available; skipping Gemini fast chat.")
            return None

        system = build_system_prompt(memories)
        system += (
            f"\n\nSYSTEM TIMESTAMP: {datetime.now().astimezone().isoformat()}"
            "\n\nYou are having an ongoing natural conversation with Sagar. Keep responses engaging, witty, and natural. Maintain context with previous messages."
        )

        contents: list[Any] = []
        for item in history[-10:]:
            role = "user" if item.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(item.get("content", "")))]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

        temperature = float(get_setting("ai", "temperature", default=0.7))
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        )

        candidates = self._get_candidate_models()
        client = genai.Client(api_key=key)

        for model_name in candidates:
            # Try streaming first if callback is provided
            if stream_callback:
                try:
                    accumulated = []
                    # Run stream generator in thread
                    def _get_stream():
                        return client.models.generate_content_stream(model=model_name, contents=contents, config=config)

                    stream = await asyncio.wait_for(asyncio.to_thread(_get_stream), timeout=7.0)
                    for chunk in stream:
                        t = getattr(chunk, "text", "") or ""
                        if t:
                            accumulated.append(t)
                            try:
                                if asyncio.iscoroutinefunction(stream_callback):
                                    await stream_callback(t)
                                else:
                                    stream_callback(t)
                            except Exception:
                                pass
                    full = "".join(accumulated).strip()
                    if full:
                        return {"response_text": full, "tool_result": None}
                except Exception as stream_err:
                    logger.debug("Fast chat stream failed on %s: %s; trying next candidate", model_name, stream_err)

            # Fallback to direct synchronous generation
            try:
                resp = await asyncio.wait_for(
                    asyncio.to_thread(client.models.generate_content, model=model_name, contents=contents, config=config),
                    timeout=7.0
                )
                text = (getattr(resp, "text", None) or "").strip()
                if not text:
                    for cand in getattr(resp, "candidates", None) or []:
                        for p in (getattr(getattr(cand, "content", None), "parts", None) or []):
                            t = getattr(p, "text", "")
                            if t:
                                text = t.strip()
                                break
                if text:
                    return {"response_text": text, "tool_result": None}
            except Exception as gen_err:
                logger.debug("Fast chat generation failed on %s: %s; trying next candidate", model_name, gen_err)
                continue

        return None

    async def process_tool_workflow(
        self,
        user_text: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Multi-step agent workflow with tool calling, parameter inspection, and bounded execution."""
        key = get_gemini_api_key()
        provider = get_setting("ai", "provider", default="hybrid").lower()
        if not key or provider in ("local", "ollama"):
            return None

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google.genai SDK not available; skipping Gemini tool workflow.")
            return None

        max_steps = int(get_setting("ai", "max_tool_steps", default=8))
        temperature = float(get_setting("ai", "temperature", default=0.6))
        declarations, reverse = tool_manifest()
        client = genai.Client(api_key=key)

        system = build_system_prompt(memories)
        system += (
            f"\n\nSYSTEM TIMESTAMP: {datetime.now().astimezone().isoformat()}"
            "\n\nYou have access to local desktop tools. When the user requests an action, use tools immediately. "
            "For multi-step goals (e.g. discover prospects -> research -> qualify -> save -> draft outreach), "
            "chain the required tools and inspect results before replying. "
            "Never invent missing client parameters or assume brands/cities not mentioned."
        )

        contents: list[Any] = []
        for item in history[-8:]:
            role = "user" if item.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(item.get("content", "")))]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))

        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=temperature,
        )

        candidates = self._get_candidate_models()
        last_result = None

        for model_name in candidates:
            try:
                for step in range(max_steps):
                    try:
                        response = await asyncio.wait_for(
                            asyncio.to_thread(client.models.generate_content, model=model_name, contents=contents, config=config),
                            timeout=18.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Tool step on %s timed out after 18s", model_name)
                        break
                    except Exception as model_err:
                        logger.debug("Tool call error on %s: %s", model_name, model_err)
                        break

                    calls = list(getattr(response, "function_calls", None) or [])
                    if not calls:
                        # Direct text answer
                        ans = (getattr(response, "text", None) or "").strip()
                        if ans:
                            return {"response_text": ans, "tool_result": last_result}
                        for cand in getattr(response, "candidates", None) or []:
                            for p in getattr(getattr(cand, "content", None), "parts", None) or []:
                                t = getattr(p, "text", "")
                                if t:
                                    return {"response_text": t.strip(), "tool_result": last_result}
                        return None

                    # Model returned tool call(s)
                    contents.append(response.candidates[0].content)
                    for call in calls:
                        fn_name = str(call.name)
                        original_name = reverse.get(fn_name)
                        if not original_name:
                            continue

                        params = dict(getattr(call, "args", None) or {})
                        log_action("tool", original_name, "LOW", status="CALLING", result=json.dumps(params))

                        try:
                            result = await asyncio.wait_for(
                                registry.call_tool(original_name, params),
                                timeout=25.0
                            )
                        except asyncio.TimeoutError:
                            from ..tools.base import ToolResult
                            result = ToolResult(success=False, error=f"Tool {original_name} timed out after 25 seconds.")
                        except Exception as te:
                            from ..tools.base import ToolResult
                            result = ToolResult(success=False, error=f"Tool execution failed: {te}")

                        last_result = result.model_dump()
                        log_action("tool", original_name, "LOW", status="COMPLETED" if result.success else "FAILED", result=result.message or result.error)

                        if result.requires_confirmation:
                            return {
                                "response_text": f"Sir, {original_name} is prepared and requires your confirmation before proceeding.",
                                "tool_result": last_result,
                                "requires_confirmation": True,
                                "confirmation_id": result.confirmation_id
                            }

                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part.from_function_response(
                                name=call.name,
                                response={"result": last_result}
                            )]
                        ))

                if last_result is not None:
                    return {
                        "response_text": "Sir, I completed the workflow steps.",
                        "tool_result": last_result
                    }

            except Exception as candidate_err:
                logger.debug("Candidate %s failed in tool workflow: %s", model_name, candidate_err)
                continue

        return None

    async def process(
        self,
        user_text: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        from .personality import is_tool_query
        if is_tool_query(user_text):
            return await self.process_tool_workflow(user_text, memories, history)
        return await self.fast_chat(user_text, memories, history)


class LocalOllamaAgent:
    """Fallback local model with rapid health check, question answering, and structured tool execution."""

    def __init__(self) -> None:
        self._last_health_check = 0.0
        self._cached_available = False

    async def is_available(self) -> bool:
        """Fast non-blocking check if Ollama is running (cached 15s)."""
        now = datetime.now().timestamp()
        if now - self._last_health_check < 15.0:
            return self._cached_available

        host = get_setting("llm", "host", default="http://127.0.0.1:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=0.8) as client:
                r = await client.get(f"{host}/api/tags")
                self._cached_available = (r.status_code == 200)
        except Exception:
            self._cached_available = False

        self._last_health_check = now
        return self._cached_available

    async def _chat(self, host: str, model: str, messages: list[dict], timeout: float = 6.0) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    f"{host}/api/chat",
                    json={"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.65}}
                )
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.debug("Ollama chat connection failed: %s", e)
        return None

    async def fast_chat(
        self,
        user_text: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
        stream_callback: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        if not await self.is_available():
            return None

        host = get_setting("llm", "host", default="http://127.0.0.1:11434").rstrip("/")
        model = get_setting("llm", "model", default="qwen2.5:3b")

        system = build_system_prompt(memories) + "\n\nMaintain natural conversation with Sagar. Be concise, witty, and helpful."
        messages = [{"role": "system", "content": system}]
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": str(h.get("content", ""))})
        messages.append({"role": "user", "content": user_text})

        data = await self._chat(host, model, messages, timeout=6.0)
        if data:
            raw = ((data.get("message") or {}).get("content") or "").strip()
            if raw:
                return {"response_text": raw, "tool_result": None}
        return None

    def _tool_descriptions(self) -> list[dict]:
        tools = []
        for t in registry.list_definitions():
            tools.append({
                "tool": alias(t.name),
                "original_name": t.name,
                "description": t.description,
                "parameters": (t.parameters or {}).get("properties", {}),
                "required": (t.parameters or {}).get("required", [])
            })
        return tools

    async def process(
        self,
        user_text: str,
        memories: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not await self.is_available():
            return None

        from .personality import is_tool_query
        if not is_tool_query(user_text):
            return await self.fast_chat(user_text, memories, history)

        host = get_setting("llm", "host", default="http://127.0.0.1:11434").rstrip("/")
        model = get_setting("llm", "model", default="qwen2.5:3b")
        max_steps = int(get_setting("ai", "max_tool_steps", default=5))

        tools_info = self._tool_descriptions()
        reverse = {t["tool"]: t["original_name"] for t in tools_info}

        system = build_system_prompt(memories) + (
            "\n\nLOCAL AGENT MODE."
            "\nIf the user is asking a general question, provide a helpful direct answer."
            "\nIf the user is requesting an action or tool, respond with JSON in one of these two formats ONLY:"
            '\n1. {"type": "answer", "text": "Your direct response"}'
            '\n2. {"type": "tool", "tool": "tool_name", "arguments": { ... }}'
            "\n\nAVAILABLE TOOLS:\n" + json.dumps(tools_info, indent=1)
        )

        messages = [{"role": "system", "content": system}]
        for h in history[-6:]:
            role = "user" if h.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": str(h.get("content", ""))})
        messages.append({"role": "user", "content": user_text})

        last_result = None

        for step in range(max_steps):
            data = await self._chat(host, model, messages, timeout=8.0)
            if not data:
                return None

            raw = ((data.get("message") or {}).get("content") or "").strip()
            if not raw:
                return None

            try:
                clean_json = raw
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()

                plan = json.loads(clean_json)
                if isinstance(plan, dict):
                    if plan.get("type") == "answer":
                        return {"response_text": str(plan.get("text", "")).strip(), "tool_result": last_result}

                    if plan.get("type") == "tool":
                        t_alias = plan.get("tool", "")
                        orig_name = reverse.get(t_alias) or reverse.get(alias(t_alias))
                        if orig_name:
                            args = dict(plan.get("arguments") or {})
                            res = await registry.call_tool(orig_name, args)
                            last_result = res.model_dump()
                            if res.requires_confirmation:
                                return {
                                    "response_text": f"Sir, {orig_name} is ready and requires your confirmation.",
                                    "tool_result": last_result,
                                    "requires_confirmation": True,
                                    "confirmation_id": res.confirmation_id
                                }
                            messages.append({"role": "assistant", "content": raw})
                            messages.append({"role": "user", "content": f"Tool '{orig_name}' output: {json.dumps(last_result)}. Continue or provide final answer."})
                            continue
            except Exception:
                pass

            return {"response_text": raw, "tool_result": last_result}

        return {"response_text": "Sir, I completed the local action workflow.", "tool_result": last_result}
