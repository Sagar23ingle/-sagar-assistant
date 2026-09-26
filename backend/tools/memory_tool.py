"""SIA Memory Management Tool
Enables SIA to remember new facts, recall context, and search Sagar's stored memory.
"""

from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel
from ..memory.database import remember, recall, list_memories, delete_memory


class MemoryTool(BaseTool):
    name = "memory.manage"
    description = "Remembers, recalls, or removes persistent personal or project memory."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["remember", "recall", "list", "forget"]},
                "category": {"type": "string", "description": "Category (personal, projects, work, preferences, context)"},
                "key": {"type": "string", "description": "Subject or title of the memory"},
                "value": {"type": "string", "description": "Details to store"},
                "query": {"type": "string", "description": "Search term for recall"},
                "memory_id": {"type": "integer", "description": "ID to delete"},
            },
            "required": ["action"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "recall").lower()

        try:
            if action == "remember":
                key = params.get("key", "").strip()
                value = params.get("value", "").strip()
                category = params.get("category", "personal").strip()
                if not key or not value:
                    return ToolResult(success=False, error="Both key and value are required to remember.")

                mem = await remember(category=category, key=key, value=value, importance=params.get("importance", 3))
                return ToolResult(
                    success=True,
                    data=mem,
                    message=f"I've committed that to memory under '{key}', Sir.",
                )

            elif action == "recall":
                query = params.get("query", "")
                category = params.get("category")
                results = await recall(query=query, category=category)
                return ToolResult(
                    success=True,
                    data=results,
                    message=f"Found {len(results)} relevant memories.",
                )

            elif action == "list":
                category = params.get("category")
                results = await list_memories(category=category)
                return ToolResult(
                    success=True,
                    data=results,
                    message=f"Retrieved {len(results)} memories.",
                )

            elif action == "forget":
                memory_id = params.get("memory_id")
                if not memory_id:
                    return ToolResult(success=False, error="memory_id is required to delete memory.")
                deleted = await delete_memory(memory_id=memory_id)
                if deleted:
                    return ToolResult(success=True, message=f"Sir, I have deleted memory #{memory_id}.")
                return ToolResult(success=False, error=f"Memory #{memory_id} not found.")

            else:
                return ToolResult(success=False, error=f"Unknown memory action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Memory operation failed.")
