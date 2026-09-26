"""SIA Local Secrets Management
Ensures credentials, local auth tokens, and sensitive configs remain safe and local.
Never exposes sensitive tokens to frontend.
"""

import os
from pathlib import Path
from typing import Optional

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve secret from environment or local .env file."""
    if key in os.environ:
        return os.environ[key]

    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key:
                        return v.strip().strip("'\"")

    return default


def set_secret(key: str, value: str) -> None:
    """Store secret into local .env file."""
    lines = []
    found = False
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    os.environ[key] = value
