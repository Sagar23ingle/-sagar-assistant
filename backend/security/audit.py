"""SIA Security Audit Logger
Maintains local immutable action audit logs for security and compliance.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_FILE = LOGS_DIR / "audit.log"

logger = logging.getLogger("sia.audit")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)


def log_action(
    tool: str,
    action: str,
    permission_level: str,
    parameters: Optional[Dict[str, Any]] = None,
    status: str = "COMPLETED",
    result: Optional[Any] = None,
    error: Optional[str] = None,
    user_confirmed: bool = False,
) -> Dict[str, Any]:
    """Records an event in the local audit log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool,
        "action": action,
        "permission_level": permission_level,
        "parameters": parameters or {},
        "status": status,
        "result": str(result)[:300] if result else None,
        "error": error,
        "user_confirmed": user_confirmed,
    }

    log_line = json.dumps(entry, ensure_ascii=False)
    if status == "FAILED" or error:
        logger.error(log_line)
    elif permission_level in ("MEDIUM", "HIGH"):
        logger.warning(log_line)
    else:
        logger.info(log_line)

    return entry


def get_recent_audit_logs(limit: int = 50) -> list:
    """Reads the last N audit log entries."""
    if not AUDIT_LOG_FILE.exists():
        return []
    entries = []
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in reversed(lines[-limit:]):
            try:
                # Remove timestamp and level prefix
                json_part = line.split("]", 1)[-1].strip()
                entries.append(json.loads(json_part))
            except Exception:
                continue
    return entries
