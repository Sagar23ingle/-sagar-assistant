"""SIA Task Management Tool
Allows SIA to manage Sagar's to-dos, follow-ups, and reminders locally.
"""

from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel
from ..memory.database import add_task, list_tasks, update_task


class TaskTool(BaseTool):
    name = "tasks.manage"
    description = "Manages tasks, to-dos, and reminders (create, list, complete)."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "list", "complete", "update"]},
                "title": {"type": "string", "description": "Title of the task"},
                "description": {"type": "string", "description": "Details of the task"},
                "due_at": {"type": "string", "description": "Due date/time"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                "task_id": {"type": "integer", "description": "ID of task to update/complete"},
            },
            "required": ["action"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "list").lower()

        try:
            if action == "create":
                title = params.get("title", "").strip()
                if not title:
                    return ToolResult(success=False, error="Task title is required.")
                task = await add_task(
                    title=title,
                    description=params.get("description", ""),
                    due_at=params.get("due_at"),
                    priority=params.get("priority", "medium"),
                )
                return ToolResult(
                    success=True,
                    data=task,
                    message=f"Sir, added task: '{title}'.",
                )

            elif action == "list":
                status = params.get("status")
                tasks = await list_tasks(status=status)
                return ToolResult(
                    success=True,
                    data=tasks,
                    message=f"Sir, you have {len(tasks)} tasks.",
                )

            elif action == "complete":
                task_id = params.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required to complete task.")
                success = await update_task(task_id=task_id, status="completed")
                if success:
                    return ToolResult(
                        success=True,
                        data={"task_id": task_id, "status": "completed"},
                        message=f"Sir, marked task #{task_id} as completed.",
                    )
                else:
                    return ToolResult(success=False, error=f"Task #{task_id} not found.")

            else:
                return ToolResult(success=False, error=f"Unknown task action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Task operation failed.")
