"""SIA Desktop Screenshot Tool
Captures the screen and stores it in the data/exports directory.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import pyautogui
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel

EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ScreenshotTool(BaseTool):
    name = "screenshots.capture"
    description = "Takes a screenshot of Sagar's computer screen and saves it locally."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Optional label or description for the screenshot"},
            },
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = params.get("label", "capture").replace(" ", "_")
        filename = f"screenshot_{label}_{timestamp}.png"
        filepath = EXPORTS_DIR / filename

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)

            return ToolResult(
                success=True,
                data={
                    "filename": filename,
                    "filepath": str(filepath),
                    "width": screenshot.width,
                    "height": screenshot.height,
                    "timestamp": timestamp,
                },
                message=f"Sir, I captured the screen. Saved to {filename}.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message="Failed to capture screen.",
            )
