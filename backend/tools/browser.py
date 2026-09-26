"""SIA Browser Tool
Opens websites and search queries directly in the user's default browser.
"""

import urllib.parse
import webbrowser
from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel


class BrowserTool(BaseTool):
    name = "browser.open_url"
    description = "Opens a web page or URL in the default browser."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open (e.g. https://google.com)"},
            },
            "required": ["url"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        url = params.get("url", "").strip()
        if not url:
            return ToolResult(success=False, error="URL parameter is required.")

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            webbrowser.open(url)
            return ToolResult(
                success=True,
                data={"url": url},
                message=f"Opened {url} in browser.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Failed to open browser.")
