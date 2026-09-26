"""SIA FastAPI Core Backend & WebSocket Command Server
Orchestrates REST endpoints, real-time WebSocket communication, tool execution,
and static frontend serving on Sagar's machine.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent.conversation import conversation_manager
from .agent.permissions import list_pending_confirmations, resolve_confirmation
from .config import get_setting, load_settings, save_settings
from .memory.database import (
    add_task,
    clear_conversation,
    delete_memory,
    get_recent_messages,
    init_db,
    list_leads,
    list_memories,
    list_projects,
    list_tasks,
    remember,
    update_task,
)
from .security.audit import get_recent_audit_logs, log_action
from .voice.tts import tts

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite schema and pre-seed context
    await init_db()
    log_action("system", "startup", "LOW", status="COMPLETED", result="SIA Backend Online")
    yield
    # Shutdown
    log_action("system", "shutdown", "LOW", status="COMPLETED")


app = FastAPI(
    title="SIA — Sagar's AI Assistant",
    description="Local-first, free personal AI companion & computer agent.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: List[WebSocket] = []


async def broadcast_state(state: str, details: Optional[Dict[str, Any]] = None):
    """Notify all connected frontend clients of state changes."""
    payload = {"type": "state_change", "state": state, "details": details or {}}
    for ws in list(active_connections):
        try:
            await ws.send_json(payload)
        except Exception:
            active_connections.remove(ws)


# ==================== REST DATA SCHEMAS ====================

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    generate_audio: bool = True


class ConfirmRequest(BaseModel):
    confirmation_id: str
    approved: bool


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    due_at: Optional[str] = None
    priority: str = "medium"


class MemoryCreateRequest(BaseModel):
    category: str = "personal"
    key: str
    value: str
    importance: int = 3


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = None


# ==================== CORE CHAT & WEBSOCKET ====================

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Processes user text/voice input through SIA's conversation manager."""
    await broadcast_state("thinking", {"query": req.message})

    result = await conversation_manager.process_user_input(
        user_text=req.message,
        session_id=req.session_id,
        generate_audio=req.generate_audio,
    )

    await broadcast_state(result["state"], {"response": result["response_text"]})
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bidirectional WebSocket for voice streaming and state updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        await websocket.send_json({
            "type": "welcome",
            "message": "Connected to SIA Core.",
            "state": "idle",
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "user_message":
                text = data.get("text", "")
                await broadcast_state("thinking", {"query": text})

                resp = await conversation_manager.process_user_input(
                    user_text=text,
                    session_id=data.get("session_id", "default"),
                    generate_audio=data.get("generate_audio", True),
                )
                await websocket.send_json({"type": "sia_response", "payload": resp})
                await broadcast_state(resp["state"])

            elif msg_type == "state_ping":
                state = data.get("state", "idle")
                await broadcast_state(state)

            elif msg_type == "interrupt":
                tts.stop()
                await broadcast_state("idle", {"interrupted": True})

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


# ==================== PERMISSIONS & CONFIRMATIONS ====================

@app.get("/api/confirmations")
async def get_confirmations():
    """Returns pending confirmation requests."""
    return list_pending_confirmations()


@app.post("/api/confirm")
async def resolve_confirmation_endpoint(req: ConfirmRequest):
    """Resolves a pending action approval or rejection."""
    resolved = resolve_confirmation(req.confirmation_id, req.approved)
    if not resolved:
        raise HTTPException(status_code=404, detail="Confirmation request not found or expired.")

    # If approved, run the tool
    if req.approved:
        from .tools.base import registry
        tool_name = resolved["tool"]
        params = resolved["parameters"]
        result = await registry.call_tool(tool_name, params, user_confirmed=True)
        return {"status": "APPROVED_AND_EXECUTED", "tool_result": result.model_dump()}

    return {"status": "REJECTED"}


# ==================== MEMORY & CONTEXT ====================

@app.get("/api/memories")
async def get_memories(category: Optional[str] = None):
    return await list_memories(category=category)


@app.post("/api/memories")
async def create_memory(req: MemoryCreateRequest):
    mem = await remember(req.category, req.key, req.value, req.importance)
    return mem


@app.delete("/api/memories/{memory_id}")
async def delete_memory_endpoint(memory_id: int):
    deleted = await delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}


# ==================== TASKS ====================

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None):
    return await list_tasks(status=status)


@app.post("/api/tasks")
async def create_task_endpoint(req: TaskCreateRequest):
    task = await add_task(req.title, req.description, req.due_at, req.priority)
    return task


@app.patch("/api/tasks/{task_id}")
async def update_task_endpoint(task_id: int, status: str):
    success = await update_task(task_id, status=status)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "status": status}


# ==================== LEADS & PROJECTS ====================

@app.get("/api/leads")
async def get_leads(status: Optional[str] = None):
    return await list_leads(status=status)


@app.get("/api/projects")
async def get_projects():
    return await list_projects()


@app.get("/api/history")
async def get_history(session_id: str = "default", limit: int = 30):
    return await get_recent_messages(session_id=session_id, limit=limit)


@app.delete("/api/history")
async def clear_history(session_id: str = "default"):
    await clear_conversation(session_id=session_id)
    return {"success": True}


# ==================== VOICE & TTS ====================

@app.post("/api/tts")
async def synthesize_speech(req: TTSRequest):
    base64_audio, file_path = await tts.generate_speech_audio(req.text, language=req.language)
    return {"audio_base64": base64_audio, "file_path": file_path}


@app.post("/api/tts/stop")
async def stop_speech():
    tts.stop()
    await broadcast_state("idle")
    return {"success": True}


# ==================== SYSTEM & AUDIT ====================

@app.get("/api/status")
async def get_status():
    """Returns local system diagnostic states."""
    import shutil
    ollama_path = get_setting("llm", "ollama_path")
    has_ollama = Path(ollama_path).exists() if ollama_path else (shutil.which("ollama") is not None)

    return {
        "status": "ready",
        "assistant_name": get_setting("assistant", "name", default="SIA"),
        "user_name": get_setting("user", "name", default="Sagar"),
        "addressing": get_setting("user", "default_addressing", default="Sir"),
        "database": "online",
        "tts_engine": get_setting("voice", "engine", default="edge-tts"),
        "local_llm_ready": has_ollama,
        "active_clients": len(active_connections),
    }


@app.get("/api/settings")
async def get_settings_endpoint():
    return load_settings()


@app.post("/api/settings")
async def update_settings_endpoint(new_settings: Dict[str, Any]):
    save_settings(new_settings)
    return {"success": True}


@app.get("/api/audit")
async def get_audit_endpoint(limit: int = 50):
    return get_recent_audit_logs(limit=limit)


# ==================== STATIC FRONTEND SERVING ====================

if FRONTEND_DIR.exists():
    app.mount("/styles", StaticFiles(directory=FRONTEND_DIR / "styles"), name="styles")
    app.mount("/src", StaticFiles(directory=FRONTEND_DIR / "src"), name="src")
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
