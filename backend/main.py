"""SIA local FastAPI server."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .agent.conversation import conversation_manager
from .agent.permissions import list_pending_confirmations, resolve_confirmation
from .config import get_setting, load_settings, save_settings, get_gemini_api_key, set_gemini_api_key
from .memory.database import add_task, clear_conversation, delete_memory, get_recent_messages, init_db, list_leads, list_memories, list_projects, list_tasks, remember, update_task
from .security.audit import get_recent_audit_logs, log_action
from .voice.tts import tts
from .tools.base import registry

ROOT=Path(__file__).resolve().parent.parent; FRONTEND=ROOT/"frontend"; active_connections:List[WebSocket]=[]
@asynccontextmanager
async def lifespan(app):
    await init_db(); log_action("system","startup","LOW",status="COMPLETED",result="SIA online"); yield; log_action("system","shutdown","LOW",status="COMPLETED")
app=FastAPI(title="SIA Personal Assistant",version="2.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:8000","http://localhost:8000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
async def broadcast(state,details=None):
    payload={"type":"state_change","state":state,"details":details or {}}
    for ws in list(active_connections):
        try: await ws.send_json(payload)
        except Exception:
            if ws in active_connections: active_connections.remove(ws)
class ChatRequest(BaseModel): message:str; session_id:str="default"; generate_audio:bool=True
class ConfirmRequest(BaseModel): confirmation_id:str; approved:bool
class TaskCreateRequest(BaseModel): title:str; description:str=""; due_at:Optional[str]=None; priority:str="medium"
class MemoryCreateRequest(BaseModel): category:str="personal"; key:str; value:str; importance:int=3
class TTSRequest(BaseModel): text:str; language:Optional[str]=None
class GeminiKeyRequest(BaseModel): api_key:str=""
@app.post("/api/chat")
async def chat(req: ChatRequest):
    async def on_state_change(st: str, details=None):
        await broadcast(st, details)

    await broadcast("processing", {"query": req.message})
    try:
        result = await conversation_manager.process_user_input(
            req.message,
            req.session_id,
            req.generate_audio,
            state_callback=on_state_change
        )
    except Exception as e:
        await broadcast("error", {"error": str(e)})
        result = {
            "response_text": "Sir, I encountered an issue processing your request.",
            "audio_base64": None,
            "mime_type": None,
            "state": "idle",
            "tool_result": None,
            "requires_confirmation": False,
            "confirmation_id": None
        }
    await broadcast(result.get("state", "idle"), {"response": result.get("response_text", "")})
    return result


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    try:
        await ws.send_json({"type": "welcome", "state": "idle"})
        while True:
            data = await ws.receive_json()
            typ = data.get("type")
            if typ == "user_message":
                text = data.get("text", "")

                async def on_token(token: str):
                    try:
                        await ws.send_json({"type": "stream_chunk", "chunk": token})
                    except Exception:
                        pass

                async def on_state(state: str, details=None):
                    try:
                        await ws.send_json({"type": "state_change", "state": state, "details": details or {}})
                    except Exception:
                        pass
                    await broadcast(state, details)

                try:
                    result = await conversation_manager.process_user_input(
                        text,
                        session_id=data.get("session_id", "default"),
                        generate_audio=data.get("generate_audio", True),
                        stream_callback=on_token,
                        state_callback=on_state
                    )
                except Exception as err:
                    result = {
                        "response_text": "Sir, an error occurred while processing that message.",
                        "audio_base64": None,
                        "mime_type": None,
                        "state": "idle",
                        "tool_result": None,
                        "requires_confirmation": False,
                        "confirmation_id": None
                    }
                    await on_state("error", {"error": str(err)})

                await ws.send_json({"type": "stream_end", "payload": result})
                await ws.send_json({"type": "sia_response", "payload": result})
                await broadcast(result.get("state", "idle"))
            elif typ == "interrupt":
                tts.stop()
                await broadcast("idle", {"interrupted": True})
            elif typ == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in active_connections:
            active_connections.remove(ws)


@app.get("/api/status")
async def status():
    return {
        "status": "ready",
        "assistant_name": get_setting("assistant", "name", default="SIA"),
        "user_name": get_setting("user", "name", default="Sagar"),
        "ai_provider": get_setting("ai", "provider", default="hybrid"),
        "gemini_configured": bool(get_gemini_api_key()),
        "gemini_model": get_setting("ai", "gemini_model", default="gemini-3.8-flash"),
        "voice_engine": get_setting("voice", "engine", default="gemini"),
        "voice": get_setting("ai", "gemini_voice", default="Aoede"),
        "database": "online",
        "active_clients": len(active_connections)
    }
@app.get("/api/settings")
async def settings(): return load_settings()
@app.post("/api/settings")
async def save(new_settings:Dict[str,Any]): save_settings(new_settings); return {"success":True,"settings":load_settings()}
@app.get("/api/gemini-key")
async def key_status(): return {"configured":bool(get_gemini_api_key())}
@app.post("/api/gemini-key")
async def set_key(req:GeminiKeyRequest): set_gemini_api_key(req.api_key); return {"configured":bool(get_gemini_api_key())}
@app.get("/api/tools")
async def tools(): return [x.model_dump() for x in registry.list_definitions()]
@app.get("/api/confirmations")
async def confirmations(): return list_pending_confirmations()
@app.post("/api/confirm")
async def confirm(req:ConfirmRequest):
    resolved=resolve_confirmation(req.confirmation_id,req.approved)
    if not resolved: raise HTTPException(status_code=404,detail="Confirmation not found or expired")
    if not req.approved:return {"status":"REJECTED"}
    result=await registry.call_tool(resolved["tool"],resolved["parameters"],user_confirmed=True)
    return {"status":"APPROVED_AND_EXECUTED","tool_result":result.model_dump()}
@app.get("/api/memories")
async def memories(category:Optional[str]=None): return await list_memories(category)
@app.post("/api/memories")
async def create_memory(req:MemoryCreateRequest): return await remember(req.category,req.key,req.value,req.importance)
@app.delete("/api/memories/{memory_id}")
async def del_memory(memory_id:int):
    ok=await delete_memory(memory_id)
    if not ok: raise HTTPException(status_code=404,detail="Memory not found")
    return {"success":True}
@app.get("/api/tasks")
async def tasks(status:Optional[str]=None): return await list_tasks(status)
@app.post("/api/tasks")
async def task(req:TaskCreateRequest): return await add_task(req.title,req.description,req.due_at,req.priority)
@app.patch("/api/tasks/{task_id}")
async def task_update(task_id:int,status:str):
    ok=await update_task(task_id,status=status)
    if not ok: raise HTTPException(status_code=404,detail="Task not found")
    return {"success":True}
@app.get("/api/leads")
async def leads(status:Optional[str]=None): return await list_leads(status)
@app.get("/api/projects")
async def projects(): return await list_projects()
@app.get("/api/history")
async def history(session_id:str="default",limit:int=30): return await get_recent_messages(session_id,limit)
@app.delete("/api/history")
async def clear(session_id:str="default"): await clear_conversation(session_id); return {"success":True}
@app.post("/api/tts")
async def synth(req:TTSRequest):
    b,p,m=await tts.generate_speech_audio(req.text,req.language); return {"audio_base64":b,"file_path":p,"mime_type":m}
@app.post("/api/tts/stop")
async def tts_stop(): tts.stop(); return {"success":True}
@app.get("/api/audit")
async def audit(limit:int=50): return get_recent_audit_logs(limit)
if FRONTEND.exists():
    app.mount("/styles",StaticFiles(directory=FRONTEND/"styles"),name="styles")
    app.mount("/src",StaticFiles(directory=FRONTEND/"src"),name="src")
    @app.get("/")
    async def index(): return FileResponse(FRONTEND/"index.html")
