"""SIA Windows Application Launcher Tool
Launches Windows applications, tools, and system utilities.
"""

import os
import subprocess
from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel

COMMON_APP_MAP = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "browser": "msedge.exe",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "settings": "ms-settings:",
    "vscode": "code.cmd",
    "vs code": "code.cmd",
    "code": "code.cmd",
}


class AppsTool(BaseTool):
    name = "apps.open"
    description = "Opens a Windows application, utility, or program."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "The name of the application to open (e.g. notepad, calc, chrome, vscode)"},
            },
            "required": ["app_name"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        app_name = params.get("app_name", "").strip().lower()
        if not app_name:
            return ToolResult(success=False, error="Application name is required.")

        target = COMMON_APP_MAP.get(app_name, app_name)

        try:
            if target.startswith("ms-"):
                os.startfile(target)
            else:
                subprocess.Popen(target, shell=True)

            return ToolResult(
                success=True,
                data={"app_name": app_name, "target": target},
                message=f"Sir, opened {app_name.capitalize()}.",
            )
        except Exception as e:
            # Fall back to startfile
            try:
                os.startfile(target)
                return ToolResult(
                    success=True,
                    data={"app_name": app_name, "target": target},
                    message=f"Sir, opened {app_name.capitalize()}.",
                )
            except Exception as e2:
                return ToolResult(
                    success=False,
                    error=str(e2),
                    message=f"Sir, I couldn't open '{app_name}'. Windows did not return a usable launch result.",
                )
