"""Tool framework with action-aware permissions."""
from enum import Enum
from typing import Any, Dict, List, Optional
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
    risk_level: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tool_name: Optional[str] = None

class BaseTool:
    name = "base_tool"
    description = "Base tool"
    risk_level = RiskLevel.LOW

    def get_definition(self) -> ToolDefinition:
        from ..agent.permissions import get_risk_level
        return ToolDefinition(
            name=self.name,
            description=self.description,
            risk_level=get_risk_level(self.name),
            parameters=self.get_parameter_schema()
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {}

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        raise NotImplementedError

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list_definitions(self) -> List[ToolDefinition]:
        return [t.get_definition() for t in self._tools.values()]

    async def call_tool(self, name: str, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found.", tool_name=name)

        from ..agent.permissions import check_permission
        action = params.get("action", "execute")
        allowed, risk, cid = check_permission(name, action, params, user_confirmed)

        if not allowed:
            return ToolResult(
                success=False,
                requires_confirmation=True,
                confirmation_id=cid,
                risk_level=risk.value,
                parameters=params,
                tool_name=name,
                message=f"Action '{name}' requires confirmation (Risk: {risk.value})."
            )

        try:
            result = await tool.execute(params, user_confirmed=user_confirmed)
            result.tool_name = name
            result.risk_level = risk.value
            result.parameters = params
            log_action(
                name,
                action,
                risk.value,
                params,
                status="COMPLETED" if result.success else "FAILED",
                result=result.data,
                error=result.error,
                user_confirmed=user_confirmed
            )
            return result
        except Exception as e:
            log_action(name, action, risk.value, params, status="FAILED", error=str(e), user_confirmed=user_confirmed)
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Tool execution failed: {e}",
                risk_level=risk.value,
                parameters=params,
                tool_name=name
            )

registry = ToolRegistry()
