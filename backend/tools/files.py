"""SIA File Management Tool
Provides file reading, writing, listing, and deletion with strict risk-tier enforcement.
"""

from pathlib import Path
from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel


class FileTool(BaseTool):
    name = "files.manage"
    description = "Reads, writes, lists, or deletes local files."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["read", "write", "list", "delete"]},
                "path": {"type": "string", "description": "Target file or folder path"},
                "content": {"type": "string", "description": "Text content when writing"},
            },
            "required": ["action", "path"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "read").lower()
        target_path_str = params.get("path", "").strip()

        if not target_path_str:
            return ToolResult(success=False, error="File path is required.")

        target = Path(target_path_str).resolve()

        try:
            if action == "read":
                if not target.exists():
                    return ToolResult(success=False, error=f"File not found: {target}")
                if target.is_dir():
                    return ToolResult(success=False, error=f"Path is a directory, not a file: {target}")

                content = target.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    success=True,
                    data={"path": str(target), "content": content[:5000], "total_bytes": target.stat().st_size},
                    message=f"Read {target.name} successfully.",
                )

            elif action == "list":
                if not target.exists() or not target.is_dir():
                    return ToolResult(success=False, error=f"Directory not found: {target}")

                items = []
                for p in target.iterdir():
                    items.append({
                        "name": p.name,
                        "is_dir": p.is_dir(),
                        "size": p.stat().st_size if p.is_file() else 0,
                    })
                return ToolResult(
                    success=True,
                    data={"directory": str(target), "items": items[:50]},
                    message=f"Found {len(items)} items in {target.name}.",
                )

            elif action == "write":
                content = params.get("content", "")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    data={"path": str(target), "bytes_written": len(content)},
                    message=f"Sir, saved changes to {target.name}.",
                )

            elif action == "delete":
                if not target.exists():
                    return ToolResult(success=False, error=f"Path not found: {target}")
                if target.is_file():
                    target.unlink()
                else:
                    return ToolResult(success=False, error="Directory deletion is restricted for safety.")
                return ToolResult(
                    success=True,
                    data={"path": str(target)},
                    message=f"Sir, deleted {target.name}.",
                )

            else:
                return ToolResult(success=False, error=f"Unknown file action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"File operation failed: {e}")
