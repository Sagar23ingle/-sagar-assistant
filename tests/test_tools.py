"""Tests for SIA Built-in Tool Implementations."""

import pytest
from backend.tools.base import registry


def test_registered_tools():
    tool_names = [t.name for t in registry.list_definitions()]
    assert "browser.open_url" in tool_names
    assert "youtube.play" in tool_names
    assert "apps.open" in tool_names
    assert "screenshots.capture" in tool_names
    assert "files.manage" in tool_names
    assert "tasks.manage" in tool_names
    assert "memory.manage" in tool_names
    assert "research.search" in tool_names
    assert "email.manage" in tool_names


@pytest.mark.asyncio
async def test_task_tool_call():
    result = await registry.call_tool("tasks.manage", {
        "action": "create",
        "title": "Review TransCore architecture",
        "priority": "high",
    })
    assert result.success is True
    assert "Review TransCore architecture" in result.message


@pytest.mark.asyncio
async def test_memory_tool_call():
    result = await registry.call_tool("memory.manage", {
        "action": "remember",
        "category": "preferences",
        "key": "test_pref",
        "value": "Keep logs concise",
    })
    assert result.success is True
    assert "test_pref" in result.message
