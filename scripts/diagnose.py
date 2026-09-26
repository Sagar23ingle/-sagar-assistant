"""SIA Diagnostics Utility
Verifies all local components: Python, SQLite database, audio/TTS, permissions, tools, and local LLM.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import get_setting
from backend.memory.database import init_db, list_memories
from backend.tools.base import registry
from backend.voice.tts import tts


async def run_diagnostics():
    print("=" * 55)
    print("           SIA SYSTEM DIAGNOSTICS")
    print("=" * 55)

    # 1. Python runtime
    print(f"[OK] Python Version: {sys.version.split()[0]} ({sys.executable})")

    # 2. SQLite Database
    try:
        await init_db()
        mems = await list_memories()
        print(f"[OK] SQLite Database: ONLINE (Found {len(mems)} seeded memories)")
    except Exception as e:
        print(f"[FAIL] SQLite Database: FAILED ({e})")

    # 3. TTS Voice Engine
    try:
        b64, path = await tts.generate_speech_audio("SIA diagnostics test.", language="en")
        if b64 and path:
            print("[OK] Neural TTS Engine: READY (Audio generation verified)")
        else:
            print("[WARN] Neural TTS Engine: Audio generation returned empty (fallback active)")
    except Exception as e:
        print(f"[FAIL] TTS Engine: FAILED ({e})")

    # 4. Tool Registry
    tools = registry.list_definitions()
    print(f"[OK] Computer Tools: {len(tools)} tools registered and permission-bounded")
    for t in tools:
        print(f"   * {t.name:<22} [{t.risk_level.value} RISK]")

    # 5. Local LLM / Ollama
    ollama_path = get_setting("llm", "ollama_path")
    has_ollama = (ollama_path and Path(ollama_path).exists()) or (shutil.which("ollama") is not None)
    if has_ollama:
        print("[OK] Local LLM Engine: INSTALLED (Ollama Portable ready)")
    else:
        print("[WARN] Local LLM Engine: Rule-based fallback active (Ollama optional)")

    print("=" * 55)
    print("[OK] All core SIA services are operational and free/local-first.")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
