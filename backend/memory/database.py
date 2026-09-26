"""SIA SQLite Persistent Memory Engine
Manages long-term structured memory, conversations, tasks, leads, and projects.
Free, local, private, and searchable.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sia.db"


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yields an aiosqlite connection with row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """Initializes the SQLite database schema if not present."""
    async with get_db_connection() as db:
        # 1. Long-term Memories table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                importance INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(category, key)
            )
        """)

        # 2. Conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        # 3. Tasks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_at TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)

        # 4. Projects table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

        # 5. Leads table (DineMotion client discovery & outreach)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                website TEXT,
                contact TEXT,
                location TEXT DEFAULT 'Nagpur',
                issues TEXT,
                pitch_angle TEXT,
                status TEXT DEFAULT 'new',
                follow_up_at TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # 6. Action History table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                description TEXT,
                permission_level TEXT,
                status TEXT,
                result TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        await db.commit()

        # Seed essential default context if empty
        async with db.execute("SELECT COUNT(*) as cnt FROM memories") as cursor:
            row = await cursor.fetchone()
            if row and row["cnt"] == 0:
                await seed_initial_context(db)


async def seed_initial_context(db: aiosqlite.Connection) -> None:
    """Pre-seeds initial foundational memories for Sagar and SIA."""
    now = datetime.now().isoformat()
    initial_memories = [
        ("personal", "user_name", "Sagar", 5),
        ("personal", "allowed_addressing", "Sir or Sagar only. Never use bro, boss, dude, buddy, or bhai.", 5),
        ("personal", "city", "Nagpur, India", 4),
        ("projects", "DineMotion Studios", "Web design and digital agency focused on high-end restaurant websites and client acquisition.", 5),
        ("projects", "TransCore", "Core technology and logistics / core system initiative.", 4),
        ("preferences", "assistant_persona", "Intelligent, calm, female, witty, honest, direct, never blindly agrees.", 5),
        ("preferences", "language_preferences", "Supports English, Hindi, Marathi, and natural Hinglish.", 4),
    ]

    for cat, key, val, imp in initial_memories:
        await db.execute(
            "INSERT OR IGNORE INTO memories (category, key, value, importance, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (cat, key, val, imp, now, now),
        )

    # Seed projects
    await db.execute("INSERT OR IGNORE INTO projects (name, description, status) VALUES (?, ?, ?)",
                     ("DineMotion Studios", "Restaurant website redesign & digital presence agency in Nagpur.", "active"))
    await db.execute("INSERT OR IGNORE INTO projects (name, description, status) VALUES (?, ?, ?)",
                     ("TransCore", "Core technological infrastructure project.", "active"))

    await db.commit()


# ==================== MEMORY OPERATIONS ====================

async def remember(category: str, key: str, value: str, importance: int = 1) -> Dict[str, Any]:
    """Store or update a long-term memory."""
    now = datetime.now().isoformat()
    async with get_db_connection() as db:
        await db.execute("""
            INSERT INTO memories (category, key, value, importance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                value=excluded.value,
                importance=excluded.importance,
                updated_at=excluded.updated_at
        """, (category, key, value, importance, now, now))
        await db.commit()
    return {"category": category, "key": key, "value": value, "importance": importance, "updated_at": now}


async def recall(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search memories by keyword match in key or value."""
    async with get_db_connection() as db:
        sql = "SELECT * FROM memories WHERE (key LIKE ? OR value LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY importance DESC, updated_at DESC LIMIT 20"

        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def list_memories(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all stored memories, optionally filtered by category."""
    async with get_db_connection() as db:
        if category:
            cursor = await db.execute("SELECT * FROM memories WHERE category = ? ORDER BY importance DESC, updated_at DESC", (category,))
        else:
            cursor = await db.execute("SELECT * FROM memories ORDER BY category ASC, importance DESC, updated_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_memory(memory_id: int) -> bool:
    """Delete a memory item by ID."""
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await db.commit()
        return cursor.rowcount > 0


# ==================== CONVERSATION OPERATIONS ====================

async def save_message(session_id: str, role: str, content: str) -> None:
    """Save user or assistant chat message."""
    now = datetime.now().isoformat()
    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        await db.commit()


async def get_recent_messages(session_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
    """Get the most recent conversation turns for context."""
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM (SELECT * FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (session_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def clear_conversation(session_id: str = "default") -> None:
    """Clear conversation history for a session."""
    async with get_db_connection() as db:
        await db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        await db.commit()


# ==================== TASK OPERATIONS ====================

async def add_task(title: str, description: str = "", due_at: Optional[str] = None, priority: str = "medium") -> Dict[str, Any]:
    """Add a new task."""
    now = datetime.now().isoformat()
    async with get_db_connection() as db:
        cursor = await db.execute(
            "INSERT INTO tasks (title, description, due_at, priority, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
            (title, description, due_at, priority, now),
        )
        await db.commit()
        task_id = cursor.lastrowid
        return {"id": task_id, "title": title, "description": description, "due_at": due_at, "priority": priority, "status": "pending", "created_at": now}


async def list_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List tasks, optionally filtered by status."""
    async with get_db_connection() as db:
        if status:
            cursor = await db.execute("SELECT * FROM tasks WHERE status = ? ORDER BY due_at ASC, id DESC", (status,))
        else:
            cursor = await db.execute("SELECT * FROM tasks ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END, due_at ASC, id DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_task(task_id: int, status: Optional[str] = None, title: Optional[str] = None) -> bool:
    """Update task status or title."""
    async with get_db_connection() as db:
        fields = []
        params = []
        if status:
            fields.append("status = ?")
            params.append(status)
        if title:
            fields.append("title = ?")
            params.append(title)
        if not fields:
            return False
        params.append(task_id)
        cursor = await db.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", params)
        await db.commit()
        return cursor.rowcount > 0


# ==================== LEAD OPERATIONS ====================

async def add_lead(business_name: str, website: str = "", contact: str = "", location: str = "Nagpur", issues: str = "", pitch_angle: str = "") -> Dict[str, Any]:
    """Add a discovered client lead for DineMotion."""
    now = datetime.now().isoformat()
    async with get_db_connection() as db:
        cursor = await db.execute(
            "INSERT INTO leads (business_name, website, contact, location, issues, pitch_angle, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'new', ?)",
            (business_name, website, contact, location, issues, pitch_angle, now),
        )
        await db.commit()
        lead_id = cursor.lastrowid
        return {
            "id": lead_id,
            "business_name": business_name,
            "website": website,
            "contact": contact,
            "location": location,
            "issues": issues,
            "pitch_angle": pitch_angle,
            "status": "new",
            "created_at": now,
        }


async def list_leads(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List business leads."""
    async with get_db_connection() as db:
        if status:
            cursor = await db.execute("SELECT * FROM leads WHERE status = ? ORDER BY id DESC", (status,))
        else:
            cursor = await db.execute("SELECT * FROM leads ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ==================== PROJECT OPERATIONS ====================

async def list_projects() -> List[Dict[str, Any]]:
    """List all projects."""
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM projects ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
