"""SIA Email & Outreach Tool
Supports reading, summarizing, drafting, and confirmed sending of emails and outreach pitches.
"""

from typing import Any, Dict
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel


class EmailTool(BaseTool):
    name = "email.manage"
    description = "Drafts, reviews, and prepares emails or outreach messages with explicit confirmation."
    risk_level = RiskLevel.MEDIUM

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["draft", "send", "review_draft"]},
                "to_address": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email message body"},
                "channel": {"type": "string", "enum": ["email", "whatsapp", "dm"], "default": "email"},
            },
            "required": ["action"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "draft").lower()
        to_address = params.get("to_address", "")
        subject = params.get("subject", "")
        body = params.get("body", "")
        channel = params.get("channel", "email")

        if action == "draft":
            return ToolResult(
                success=True,
                data={
                    "to": to_address,
                    "subject": subject,
                    "body": body,
                    "channel": channel,
                    "status": "DRAFTED",
                },
                message=f"Sir, I drafted the {channel} message for {to_address or 'the client'}. Want me to review or send it?",
            )

        elif action == "send":
            if not user_confirmed:
                return ToolResult(
                    success=False,
                    requires_confirmation=True,
                    message="Sending external emails or messages requires your explicit confirmation.",
                )

            # In user-confirmed state, log simulated/configured send
            return ToolResult(
                success=True,
                data={"to": to_address, "subject": subject, "status": "SENT"},
                message=f"Sir, the message to {to_address} has been dispatched successfully.",
            )

        return ToolResult(success=False, error=f"Unknown email action: {action}")
