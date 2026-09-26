"""SIA Tools Package
Initializes and registers all tools into the central Tool Registry.
"""

from .base import registry, ToolRegistry, BaseTool, ToolResult
from .browser import BrowserTool
from .youtube import YouTubeTool
from .apps import AppsTool
from .screenshots import ScreenshotTool
from .files import FileTool
from .tasks import TaskTool
from .memory_tool import MemoryTool
from .research import ResearchTool
from .email import EmailTool

# Register all built-in tools
registry.register(BrowserTool())
registry.register(YouTubeTool())
registry.register(AppsTool())
registry.register(ScreenshotTool())
registry.register(FileTool())
registry.register(TaskTool())
registry.register(MemoryTool())
registry.register(ResearchTool())
registry.register(EmailTool())

__all__ = [
    "registry",
    "ToolRegistry",
    "BaseTool",
    "ToolResult",
    "BrowserTool",
    "YouTubeTool",
    "AppsTool",
    "ScreenshotTool",
    "FileTool",
    "TaskTool",
    "MemoryTool",
    "ResearchTool",
    "EmailTool",
]
