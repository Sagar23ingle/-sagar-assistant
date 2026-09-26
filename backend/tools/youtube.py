"""SIA YouTube Tool
Automates searching and playing YouTube videos and music directly on Sagar's machine.
"""

import re
import urllib.parse
import webbrowser
import httpx
from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel


class YouTubeTool(BaseTool):
    name = "youtube.play"
    description = "Searches and plays a song, music, or video on YouTube."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The song, artist, or video title to search and play"},
            },
            "required": ["query"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        query = params.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Search query is required.")

        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

        video_url = search_url
        video_id = None

        # Attempt to find the top video ID for direct playback
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(search_url, headers=headers)
                if res.status_code == 200:
                    # Match video IDs in YouTube's initial data json / html
                    matches = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", res.text)
                    if matches:
                        video_id = matches[0]
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
        except Exception:
            # Fall back to opening search results
            video_url = search_url

        try:
            webbrowser.open(video_url)
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "url": video_url,
                    "video_id": video_id,
                    "direct_playback": video_id is not None,
                },
                message=f"Sir, playing '{query}' on YouTube." if video_id else f"Sir, opened YouTube search for '{query}'.",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Failed to launch YouTube.")
