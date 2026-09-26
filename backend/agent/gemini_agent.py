"""Hybrid Gemini/Ollama agent with real function calling."""
from __future__ import annotations
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from ..config import get_gemini_api_key, get_setting
from ..tools.base import registry
from .personality import build_system_prompt


def alias(tool_name: str) -> str:
    return tool_name.replace(".", "_").replace("-", "_")


def tool_manifest() -> tuple[list[dict], dict[str, str]]:
    declarations, reverse = [], {}
    for tool in registry.list_definitions():
        a = alias(tool.name)
        reverse[a] = tool.name
        params = tool.parameters or {"type": "object", "properties": {}}
        declarations.append({"type": "function", "name": a, "description": tool.description, "parameters": params})
    return declarations, reverse


class GeminiAgent:
    def __init__(self) -> None:
        self.model = get_setting("ai", "gemini_model", default="gemini-3.8-flash")
        self.max_steps = int(get_setting("ai", "max_tool_steps", default=8))

    async def process(self, user_text: str, memories: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        key = get_gemini_api_key()
        if not key or get_setting("ai", "provider", default="hybrid") == "local":
            return None
        try:
            from google import genai
            from google.genai import types
        except Exception:
            return None

        declarations, reverse = tool_manifest()
        client = genai.Client(api_key=key)
        system = build_system_prompt(memories)
        system += (
            "\n\nCURRENT TIME: " + datetime.now().astimezone().isoformat() +
            "\n\nYou have real tools. Use them to act, not to describe actions. "
            "Never hardcode missing business context. If a command is sufficiently clear, act immediately. "
            "For complex goals, chain tools and verify their outputs."
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
            temperature=float(get_setting("ai", "temperature", default=0.65)),
        )

        last_result = None
        for _ in range(self.max_steps):
            response = await asyncio.to_thread(client.models.generate_content, model=self.model, contents=contents, config=config)
            calls = list(getattr(response, "function_calls", None) or [])
            if not calls:
                answer = (getattr(response, "text", None) or "").strip()
                if answer:
                    return {"response_text": answer, "tool_result": last_result}
                return None

            contents.append(response.candidates[0].content)
            for call in calls:
                original = reverse.get(str(call.name))
                if not original:
                    continue
                params = dict(getattr(call, "args", None) or {})
                result = await registry.call_tool(original, params)
                last_result = result.model_dump()
                if result.requires_confirmation:
                    return {"response_text": f"Sir, {original} is ready and needs your confirmation before I execute it.", "tool_result": last_result, "requires_confirmation": True, "confirmation_id": result.confirmation_id}
                contents.append(types.Content(role="user", parts=[types.Part.from_function_response(
                    name=call.name, id=getattr(call, "id", None), response={"result": result.model_dump()}
                )]))
        return {"response_text": "Sir, I stopped after several safe execution steps instead of guessing.", "tool_result": last_result}


class LocalOllamaAgent:
    """Local model fallback with JSON tool planning rather than hardcoded keyword routing."""
    def __init__(self) -> None:
        self.host = get_setting("llm", "host", default="http://127.0.0.1:11434").rstrip("/")
        self.model = get_setting("llm", "model", default="qwen2.5:3b")
        self.max_steps = int(get_setting("ai", "max_tool_steps", default=6))

    async def _chat(self, messages: list[dict]) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(f"{self.host}/api/chat", json={"model": self.model, "messages": messages, "stream": False, "options": {"temperature": 0.65}})
                r.raise_for_status()
                return r.json()
        except Exception:
            return None

    def _tools(self) -> str:
        declarations, _ = tool_manifest()
        rows = []
        for d in declarations:
            rows.append({"tool": d["name"], "description": d["description"], "parameters": d["parameters"].get("properties", {}), "required": d["parameters"].get("required", [])})
        return json.dumps(rows, ensure_ascii=False)

    async def process(self, user_text: str, memories: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        _, reverse = tool_manifest()
        system = build_system_prompt(memories) + (
            "\n\nLOCAL TOOL MODE. Return ONLY JSON: "
            '{"type":"answer","text":"..."} OR {"type":"tool","tool":"alias","arguments":{...}}. '
            "Never repeat the user's question. Use tools whenever action is requested. "
            "Do not invent unstated locations or industries. TOOLS=" + self._tools()
        )
        messages = [{"role": "system", "content": system}]
        for h in history[-8:]:
            messages.append({"role": "user" if h.get("role") == "user" else "assistant", "content": str(h.get("content", ""))})
        messages.append({"role": "user", "content": user_text})
        last_result = None

        for _ in range(self.max_steps):
            data = await self._chat(messages)
            if not data:
                return None
            raw = ((data.get("message") or {}).get("content") or "").strip()
            if not raw:
                return None
            try:
                plan = json.loads(raw)
            except Exception:
                return {"response_text": raw, "tool_result": last_result}
            if plan.get("type") == "answer":
                return {"response_text": str(plan.get("text") or ""), "tool_result": last_result}
            if plan.get("type") != "tool":
                return {"response_text": raw, "tool_result": last_result}
            tool_name = reverse.get(str(plan.get("tool", "")))
            if not tool_name:
                return {"response_text": "Sir, I couldn't map that action to an installed capability.", "tool_result": None}
            result = await registry.call_tool(tool_name, dict(plan.get("arguments") or {}))
            last_result = result.model_dump()
            if result.requires_confirmation:
                return {"response_text": f"Sir, {tool_name} is ready and needs your confirmation.", "tool_result": last_result, "requires_confirmation": True, "confirmation_id": result.confirmation_id}
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": "Tool result. Continue the same goal and produce final JSON when finished: " + json.dumps(last_result, ensure_ascii=False)})
        return {"response_text": "Sir, I stopped after the safe tool-step limit.", "tool_result": last_result}
