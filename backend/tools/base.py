"""SIA Tool Framework
Base class and central registry for all SIA computer, browser, and assistant tools.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from ..security.audit import log_action


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: str = ""
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_id: Optional[str] = None


class BaseTool:
    name: str = "base_tool"
    description: str = "Base tool"
    risk_level: RiskLevel = RiskLevel.LOW

    def get_definition(self) -> ToolDefinition:
        from ..agent.permissions import get_risk_level
        return ToolDefinition(
            name=self.name,
            description=self.description,
            risk_level=get_risk_level(self.name),
            parameters=self.get_parameter_schema(),
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {}

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_definitions(self) -> List[ToolDefinition]:
        return [tool.get_definition() for tool in self._tools.values()]

    async def call_tool(
        self,
        name: str,
        params: Dict[str, Any],
        user_confirmed: bool = False,
    ) -> ToolResult:
        """Enforces permission checks before executing any registered tool."""
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found.")

        # Permission check
        from ..agent.permissions import check_permission
        allowed, risk, confirmation_id = check_permission(
            tool_name=name,
            action=params.get("action", "execute"),
            parameters=params,
            user_confirmed=user_confirmed,
        )

        if not allowed:
            return ToolResult(
                success=False,
                requires_confirmation=True,
                confirmation_id=confirmation_id,
                message=f"Action '{name}' requires your confirmation (Risk: {risk.value}).",
            )

        try:
            result = await tool.execute(params, user_confirmed=user_confirmed)
            log_action(
                tool=name,
                action=params.get("action", "execute"),
                permission_level=risk.value,
                parameters=params,
                status="COMPLETED" if result.success else "FAILED",
                result=result.data,
                error=result.error,
                user_confirmed=user_confirmed,
            )
            return result
        except Exception as e:
            error_msg = str(e)
            log_action(
                tool=name,
                action=params.get("action", "execute"),
                permission_level=risk.value,
                parameters=params,
                status="FAILED",
                error=error_msg,
                user_confirmed=user_confirmed,
            )
            return ToolResult(success=False, error=error_msg, message=f"Tool execution failed: {error_msg}")


# Global Tool Registry instance
registry = ToolRegistry()
