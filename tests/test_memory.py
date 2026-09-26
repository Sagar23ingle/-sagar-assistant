"""Tests for SIA SQLite Structured Memory Engine."""

import pytest
from backend.memory.database import (
    init_db,
    remember,
    recall,
    list_memories,
    delete_memory,
    add_task,
    list_tasks,
    update_task,
    add_lead,
    list_leads,
    save_message,
    get_recent_messages,
)


@pytest.mark.asyncio
async def test_memory_lifecycle():
    await init_db()

    # 1. Remember
    mem = await remember("projects", "TestProject", "Automated test project detail", importance=4)
    assert mem["key"] == "TestProject"

    # 2. Recall
    recalled = await recall("TestProject")
    assert len(recalled) >= 1
    assert any(m["key"] == "TestProject" for m in recalled)

    # 3. List
    all_mems = await list_memories()
    assert len(all_mems) >= 1

    # 4. Find created memory ID to delete
    target = next((m for m in all_mems if m["key"] == "TestProject"), None)
    assert target is not None
    deleted = await delete_memory(target["id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_task_operations():
    await init_db()

    # Add task
    task = await add_task("Follow up with Nagpur Cafe", "Send redesign pitch", priority="high")
    assert task["id"] is not None
    assert task["title"] == "Follow up with Nagpur Cafe"

    # List tasks
    tasks = await list_tasks()
    assert any(t["id"] == task["id"] for t in tasks)

    # Update task
    success = await update_task(task["id"], status="completed")
    assert success is True


@pytest.mark.asyncio
async def test_lead_operations():
    await init_db()

    lead = await add_lead(
        business_name="Haldirams Nagpur",
        website="https://haldirams.com",
        location="Nagpur",
        issues="Mobile menu needs streamlining",
        pitch_angle="Modern DineMotion responsive revamp",
    )
    assert lead["id"] is not None

    leads = await list_leads()
    assert any(l["business_name"] == "Haldirams Nagpur" for l in leads)


@pytest.mark.asyncio
async def test_conversation_saving():
    await init_db()

    await save_message("test_session", "user", "Hello SIA")
    await save_message("test_session", "assistant", "Hello Sir.")

    history = await get_recent_messages("test_session", limit=5)
    assert len(history) >= 2
    assert history[-2]["content"] == "Hello SIA"
    assert history[-1]["content"] == "Hello Sir."
