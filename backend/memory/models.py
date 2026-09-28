"""SIA Memory Models
Pydantic data models for structured SQLite persistence.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: Optional[int] = None
    category: str = Field(..., description="personal, projects, work, preferences, context")
    key: str
    value: str
    importance: int = Field(default=1, ge=1, le=5)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationMessage(BaseModel):
    id: Optional[int] = None
    session_id: str = "default"
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: Optional[str] = None


class TaskItem(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = ""
    due_at: Optional[str] = None
    priority: str = Field(default="medium", description="low, medium, high")
    status: str = Field(default="pending", description="pending, in_progress, completed, overdue")
    created_at: Optional[str] = None


class LeadItem(BaseModel):
    id: Optional[int] = None
    business_name: str
    website: Optional[str] = ""
    contact: Optional[str] = ""
    location: Optional[str] = ""
    issues: Optional[str] = ""
    pitch_angle: Optional[str] = ""
    status: str = Field(default="new", description="new, analyzed, drafted, contacted, closed")
    follow_up_at: Optional[str] = None
    created_at: Optional[str] = None


class ProjectItem(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = ""
    status: str = Field(default="active", description="active, paused, completed")
