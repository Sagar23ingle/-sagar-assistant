"""Tests for SIA Safety & Risk-tiered Permission System."""

import pytest
from backend.agent.permissions import (
    RiskLevel,
    check_permission,
    get_risk_level,
    list_pending_confirmations,
    resolve_confirmation,
)


def test_permission_tier_mappings():
    # Low risk
    assert get_risk_level("browser.open_url") == RiskLevel.LOW
    assert get_risk_level("youtube.play") == RiskLevel.LOW
    assert get_risk_level("research.search") == RiskLevel.LOW

    # Medium risk
    assert get_risk_level("files.write") == RiskLevel.MEDIUM
    assert get_risk_level("email.send") == RiskLevel.MEDIUM

    # High risk
    assert get_risk_level("files.delete") == RiskLevel.HIGH


def test_low_risk_auto_approved():
    allowed, risk, cid = check_permission("youtube.play", "play", {"query": "Arijit Singh"})
    assert allowed is True
    assert risk == RiskLevel.LOW
    assert cid is None


def test_medium_risk_requires_confirmation():
    allowed, risk, cid = check_permission("email.send", "send", {"to": "client@example.com"})
    assert allowed is False
    assert risk == RiskLevel.MEDIUM
    assert cid is not None

    # Check pending list
    pending = list_pending_confirmations()
    assert any(p["id"] == cid for p in pending)

    # Approve
    resolved = resolve_confirmation(cid, approved=True)
    assert resolved is not None
    assert resolved["status"] == "APPROVED"


def test_high_risk_rejection():
    allowed, risk, cid = check_permission("files.delete", "delete", {"path": "test.txt"})
    assert allowed is False
    assert risk == RiskLevel.HIGH
    assert cid is not None

    resolved = resolve_confirmation(cid, approved=False)
    assert resolved is not None
    assert resolved["status"] == "REJECTED"
