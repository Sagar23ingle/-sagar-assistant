"""SIA Configuration Manager
Loads and manages configuration from config/settings.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file."""
    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {SETTINGS_FILE}")
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(new_settings: Dict[str, Any]) -> None:
    """Save updated settings to JSON file."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(new_settings, f, indent=2, ensure_ascii=False)


# Default cached settings instance
settings = load_settings()


def get_setting(*keys: str, default: Any = None) -> Any:
    """Safely traverse settings dict using key hierarchy."""
    val = settings
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def update_setting(keys: list, value: Any) -> None:
    """Update a specific nested key and save to disk."""
    global settings
    ref = settings
    for k in keys[:-1]:
        if k not in ref or not isinstance(ref[k], dict):
            ref[k] = {}
        ref = ref[k]
    ref[keys[-1]] = value
    save_settings(settings)
