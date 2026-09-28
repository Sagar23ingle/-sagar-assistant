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
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "browser": "msedge",
    "terminal": "wt.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "settings": "ms-settings:",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
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

        candidates = []
        if app_name in ["chrome", "google chrome"]:
            candidates = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ]
        elif app_name in ["vscode", "vs code", "code"]:
            candidates = [
                os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
            ]
        elif app_name in ["edge", "browser"]:
            candidates = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ]

        try:
            # 1. Try known explicit Windows installation paths
            for path in candidates:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    return ToolResult(
                        success=True,
                        data={"app_name": app_name, "path": path},
                        message=f"Sir, opened {app_name.capitalize()}.",
                    )

            # 2. Try Windows protocol (e.g. ms-settings:)
            target = COMMON_APP_MAP.get(app_name, app_name)
            if target.startswith("ms-"):
                os.startfile(target)
                return ToolResult(
                    success=True,
                    data={"app_name": app_name, "target": target},
                    message=f"Sir, opened {app_name.capitalize()}.",
                )

            # 3. Use Windows shell 'start' command (consults Windows App Paths registry)
            subprocess.Popen(f'start "" {target}', shell=True)
            return ToolResult(
                success=True,
                data={"app_name": app_name, "target": target},
                message=f"Sir, opened {app_name.capitalize()}.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Sir, I couldn't open '{app_name}': {e}",
            )
