"""SIA Permission and Safety Engine
Strictly validates risk levels and enforces human-in-the-loop confirmation
for medium and high-risk actions.
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ..config import get_setting
from ..security.audit import log_action


class RiskLevel(str, Enum):
    LOW = "LOW"        # Auto-execute (browser open, youtube play, read files, search, apps launch)
    MEDIUM = "MEDIUM"  # Ask first (send email, write important files, external messages)
    HIGH = "HIGH"      # Always explicit confirmation (delete files, system config, destructive actions)


# Default permission map
TOOL_PERMISSION_MAP = {
    # Low Risk
    "browser.open_url": RiskLevel.LOW,
    "youtube.play": RiskLevel.LOW,
    "apps.open": RiskLevel.LOW,
    "screenshots.capture": RiskLevel.LOW,
    "research.search": RiskLevel.LOW,
    "research.analyze": RiskLevel.LOW,
    "tasks.list": RiskLevel.LOW,
    "tasks.create": RiskLevel.LOW,
    "tasks.update": RiskLevel.LOW,
    "memory.recall": RiskLevel.LOW,
    "memory.remember": RiskLevel.LOW,
    "files.read": RiskLevel.LOW,
    "files.list": RiskLevel.LOW,
    "email.read": RiskLevel.LOW,
    "email.draft": RiskLevel.LOW,

    # Medium Risk
    "files.write": RiskLevel.MEDIUM,
    "files.rename": RiskLevel.MEDIUM,
    "email.send": RiskLevel.MEDIUM,
    "outreach.prepare_send": RiskLevel.MEDIUM,

    # High Risk
    "files.delete": RiskLevel.HIGH,
    "system.execute_raw": RiskLevel.HIGH,
    "system.shutdown": RiskLevel.HIGH,
    "security.modify": RiskLevel.HIGH,
}

# In-memory store for pending confirmations: confirmation_id -> request dict
_pending_confirmations: Dict[str, Dict[str, Any]] = {}


def get_risk_level(tool_name: str, action: str = "") -> RiskLevel:
    """Determine risk level from configuration or default map."""
    full_key = f"{tool_name}.{action}" if action else tool_name
    config_perm = get_setting("permissions", full_key) or get_setting("permissions", tool_name)
    if config_perm:
        try:
            return RiskLevel(config_perm)
        except ValueError:
            pass
    return TOOL_PERMISSION_MAP.get(full_key, TOOL_PERMISSION_MAP.get(tool_name, RiskLevel.MEDIUM))


def check_permission(
    tool_name: str,
    action: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    user_confirmed: bool = False,
) -> Tuple[bool, RiskLevel, Optional[str]]:
    """
    Evaluates whether an action is permitted.
    Returns: (is_allowed, risk_level, confirmation_id_or_none)
    """
    # Check global kill switch
    if get_setting("security", "kill_switch", default=False):
        log_action(tool_name, action, "HIGH", parameters, status="BLOCKED", error="Emergency kill switch active")
        return False, RiskLevel.HIGH, None

    risk = get_risk_level(tool_name, action)

    # Low risk actions are auto-approved
    if risk == RiskLevel.LOW or user_confirmed:
        return True, risk, None

    # Medium and High risk require user confirmation
    confirmation_id = str(uuid.uuid4())
    _pending_confirmations[confirmation_id] = {
        "id": confirmation_id,
        "tool": tool_name,
        "action": action,
        "risk_level": risk.value,
        "parameters": parameters or {},
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat(),
        "status": "PENDING",
    }

    log_action(
        tool=tool_name,
        action=action,
        permission_level=risk.value,
        parameters=parameters,
        status="AWAITING_CONFIRMATION",
        result={"confirmation_id": confirmation_id},
    )

    return False, risk, confirmation_id


def resolve_confirmation(confirmation_id: str, approved: bool) -> Optional[Dict[str, Any]]:
    """Handles user approval or rejection of a pending action."""
    if confirmation_id not in _pending_confirmations:
        return None

    request = _pending_confirmations.pop(confirmation_id)
    request["status"] = "APPROVED" if approved else "REJECTED"
    request["resolved_at"] = datetime.now().isoformat()

    log_action(
        tool=request["tool"],
        action=request["action"],
        permission_level=request["risk_level"],
        parameters=request["parameters"],
        status="CONFIRMED" if approved else "CANCELLED_BY_USER",
        user_confirmed=approved,
    )

    return request


def list_pending_confirmations() -> list:
    """Returns all currently pending confirmation requests."""
    now = datetime.now()
    valid = []
    expired_ids = []
    for cid, req in _pending_confirmations.items():
        exp = datetime.fromisoformat(req["expires_at"])
        if exp < now:
            expired_ids.append(cid)
        else:
            valid.append(req)

    for cid in expired_ids:
        _pending_confirmations.pop(cid, None)

    return valid
