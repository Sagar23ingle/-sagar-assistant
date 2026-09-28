"""Runtime configuration with safe local secrets storage."""
from __future__ import annotations
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
SECRETS_FILE = CONFIG_DIR / "local_secrets.json"

DEFAULTS: Dict[str, Any] = {
    "user": {"name": "Sagar", "allowed_addressing": ["Sir", "Sagar"], "default_addressing": "Sir", "preferred_language": "auto"},
    "assistant": {"name": "SIA", "gender": "female", "personality": {"sarcasm_level": 0.35, "playfulness": 0.5, "proactive_enabled": True, "verbosity": "natural", "honesty_level": "direct"}},
    "voice": {"engine": "gemini", "gemini_voice": "Aoede", "auto_speak_responses": True, "fallback_engine": "edge-tts"},
    "speech_to_text": {"engine": "browser", "wake_word": "Hey Sia", "wake_word_enabled": True, "push_to_talk_key": "Space"},
    "ai": {"provider": "hybrid", "gemini_model": "gemini-3.5-flash-lite", "gemini_tts_model": "gemini-2.5-flash-preview-tts", "gemini_voice": "Aoede", "temperature": 0.65, "max_tool_steps": 8},
    "llm": {"provider": "ollama", "host": "http://127.0.0.1:11434", "model": "qwen2.5:3b", "temperature": 0.7, "context_window": 8192},
    "memory": {"db_path": "data/sia.db", "max_recent_messages": 20},
    "permissions": {
        "browser.open_url": "LOW", "youtube.play": "LOW", "apps.open": "LOW", "screenshots.capture": "LOW",
        "research.search": "LOW", "research.analyze": "LOW", "research.search_web": "LOW", "business.manage": "LOW",
        "tasks.manage": "LOW", "memory.manage": "LOW", "files.read": "LOW", "files.list": "LOW", "files.write": "MEDIUM",
        "files.delete": "HIGH", "email.manage": "MEDIUM", "email.send": "MEDIUM"
    },
    "security": {"kill_switch": False, "microphone_muted": False, "audit_log": "data/logs/audit.log"},
}


def _merge(a: dict, b: dict) -> dict:
    out = deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
        return deepcopy(DEFAULTS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    return _merge(DEFAULTS, raw)


settings = load_settings()


def save_settings(new_settings: Dict[str, Any]) -> None:
    global settings
    safe = deepcopy(new_settings or {})
    # Never allow a UI save to persist API keys into the tracked settings file.
    if isinstance(safe.get("ai"), dict):
        safe["ai"].pop("gemini_api_key", None)
    SETTINGS_FILE.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    settings = load_settings()


def get_setting(*keys: str, default: Any = None) -> Any:
    value: Any = settings
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def update_setting(keys: list[str], value: Any) -> None:
    global settings
    node = settings
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value
    save_settings(settings)


def get_gemini_api_key() -> str:
    env = os.getenv("GEMINI_API_KEY", "").strip()
    if env:
        return env
    try:
        data = json.loads(SECRETS_FILE.read_text(encoding="utf-8")) if SECRETS_FILE.exists() else {}
        return str(data.get("gemini_api_key", "")).strip()
    except Exception:
        return ""


def set_gemini_api_key(key: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SECRETS_FILE.write_text(json.dumps({"gemini_api_key": (key or "").strip()}, indent=2), encoding="utf-8")
    try:
        os.chmod(SECRETS_FILE, 0o600)
    except Exception:
        pass
