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
from .business import BusinessOpsTool

registry.register(BrowserTool())
registry.register(YouTubeTool())
registry.register(AppsTool())
registry.register(ScreenshotTool())
registry.register(FileTool())
registry.register(TaskTool())
registry.register(MemoryTool())
registry.register(ResearchTool())
registry.register(BusinessOpsTool())
registry.register(EmailTool())
