"""Advanced business operator skill: discovery, qualification, website audit, outreach, CRM lead memory, proposals."""
from __future__ import annotations
from typing import Any, Dict
from .base import BaseTool, ToolResult
from .research import ResearchTool
from ..agent.permissions import RiskLevel
from ..memory.database import add_lead, add_task, list_leads

class BusinessOpsTool(BaseTool):
    name = "business.manage"
    description = (
        "Advanced business operator: discover client leads across any geography/industry, "
        "audit websites, qualify prospects, draft personalized multi-channel outreach, "
        "save to local CRM, schedule follow-ups, and generate proposals."
    )
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "discover_leads",
                        "company_research",
                        "website_audit",
                        "qualify_lead",
                        "draft_outreach",
                        "save_lead",
                        "create_follow_up",
                        "draft_proposal"
                    ],
                    "description": "The business operation to perform"
                },
                "industry": {"type": "string", "description": "Target niche, e.g. detailing, real estate, dental clinics"},
                "location": {"type": "string", "description": "Target city, state, or region, e.g. California, London, Texas"},
                "country": {"type": "string", "description": "Target country, e.g. US, UK, Australia, India"},
                "limit": {"type": "integer", "description": "Max prospects to discover (default 10)"},
                "company_name": {"type": "string", "description": "Name of the business"},
                "business_name": {"type": "string", "description": "Alternative company name"},
                "website": {"type": "string", "description": "Website URL to inspect or audit"},
                "pain_points": {"type": "string", "description": "Observed issues or improvement areas"},
                "offer": {"type": "string", "description": "Value proposition or service offer"},
                "contact_name": {"type": "string", "description": "Decision maker or contact name"},
                "channel": {"type": "string", "enum": ["email", "whatsapp", "linkedin", "dm"], "description": "Outreach channel"},
                "tone": {"type": "string", "enum": ["direct", "consultative", "friendly", "formal"], "description": "Tone of outreach"},
                "notes": {"type": "string", "description": "Additional prospect notes"},
                "follow_up_date": {"type": "string", "description": "Due date for follow-up reminder"},
                "scope_of_work": {"type": "string", "description": "Deliverables for proposal"},
                "estimated_price": {"type": "string", "description": "Estimated quotation price"}
            },
            "required": ["action"]
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "discover_leads")
        research = ResearchTool()

        try:
            if action == "discover_leads":
                industry = params.get("industry") or "businesses"
                location = params.get("location") or ""
                country = params.get("country") or ""
                limit = int(params.get("limit") or 10)
                res = await research.execute({
                    "action": "find_business_leads",
                    "industry": industry,
                    "location": location,
                    "country": country,
                    "limit": limit
                })
                return res

            if action in ("company_research", "website_audit"):
                name = (params.get("company_name") or params.get("business_name") or "").strip()
                website = (params.get("website") or "").strip()
                q = f"{name} official website services contact" if name else website
                results = await research._search(q, 6)
                
                target_url = website
                if not target_url and results:
                    target_url = results[0]["url"]

                audit_data = {}
                if target_url:
                    audit_data = await research._analyze(target_url)

                report = {
                    "company_name": name or audit_data.get("title", "Target Company"),
                    "website": target_url,
                    "search_results": results,
                    "website_audit": audit_data,
                    "opportunities": audit_data.get("opportunities", []),
                    "mobile_ready": audit_data.get("has_viewport", False),
                    "clear_cta": audit_data.get("has_contact", False),
                    "social_presence": audit_data.get("has_social", False)
                }
                return ToolResult(
                    success=True,
                    data=report,
                    message=f"Sir, I completed company research and website audit for {name or target_url}."
                )

            if action == "qualify_lead":
                name = params.get("company_name") or params.get("business_name") or "Target Business"
                website = params.get("website") or ""
                pain = params.get("pain_points") or ""
                notes = params.get("notes") or ""

                score = 50
                reasons = []

                if website:
                    score += 15
                    reasons.append("Active web presence verified (+15)")
                else:
                    score -= 20
                    reasons.append("No website detected — major digital revamp/build opportunity (-20)")

                if pain:
                    score += 20
                    reasons.append(f"Identified concrete pain point: {pain} (+20)")

                if notes:
                    score += 10
                    reasons.append("Contextual notes provided (+10)")

                score = max(0, min(100, score))
                band = "HIGH PRIORITY" if score >= 75 else "QUALIFIED" if score >= 50 else "LOW SIGNAL"
                
                return ToolResult(
                    success=True,
                    data={
                        "company_name": name,
                        "qualification_score": score,
                        "status_band": band,
                        "score_breakdown": reasons,
                        "recommendation": "Prepare personalized outreach focusing on identified gaps."
                    },
                    message=f"Sir, {name} is evaluated as {band} (Score: {score}/100)."
                )

            if action == "draft_outreach":
                name = params.get("company_name") or params.get("business_name") or "there"
                contact = params.get("contact_name") or "there"
                offer = params.get("offer") or "a modern digital upgrade to increase customer bookings"
                pain = params.get("pain_points") or "a few obvious conversion and mobile experience gaps"
                channel = params.get("channel") or "email"
                tone = params.get("tone") or "direct"

                if channel == "email":
                    subject = f"Quick observation regarding {name}"
                    body = (
                        f"Hi {contact},\n\n"
                        f"I was recently reviewing {name}'s online presence and noticed {pain}.\n\n"
                        f"We specialize in {offer}, helping businesses like yours turn visitors into booked clients.\n\n"
                        f"Would you be open to a brief 5-minute walkthrough of a few quick wins you can implement right away?\n\n"
                        "Best regards,\n"
                        "Sagar"
                    )
                    data = {"channel": channel, "subject": subject, "body": body, "tone": tone}
                elif channel == "whatsapp":
                    data = {
                        "channel": channel,
                        "message": (
                            f"Hi {contact}! Noticed {name} and saw {pain}. "
                            f"We help with {offer} to boost inquiries. Open to a quick 2-minute demo?"
                        ),
                        "tone": tone
                    }
                else:
                    data = {
                        "channel": channel,
                        "message": (
                            f"Hi {contact}, came across {name}. Noticed {pain} and wanted to share a quick idea around {offer}. "
                            "Worth a quick chat this week?"
                        ),
                        "tone": tone
                    }

                return ToolResult(
                    success=True,
                    data=data,
                    message=f"Sir, I drafted personalized {channel} outreach for {name}."
                )

            if action == "save_lead":
                name = params.get("business_name") or params.get("company_name") or "Unnamed prospect"
                website = params.get("website", "")
                contact = params.get("contact_name", "")
                loc = params.get("location") or params.get("country") or ""
                pain = params.get("pain_points", "")
                offer = params.get("offer", "")

                lead = await add_lead(
                    business_name=name,
                    website=website,
                    contact=contact,
                    location=loc,
                    issues=pain,
                    pitch_angle=offer
                )
                return ToolResult(
                    success=True,
                    data=lead,
                    message=f"Sir, {name} has been added to your local CRM lead memory."
                )

            if action == "create_follow_up":
                name = params.get("company_name") or params.get("business_name") or "Prospect"
                due = params.get("follow_up_date") or None
                notes = params.get("notes") or f"Follow up on outreach with {name}"
                task = await add_task(
                    title=f"Follow up with {name}",
                    description=notes,
                    due_at=due,
                    priority="high"
                )
                return ToolResult(
                    success=True,
                    data=task,
                    message=f"Sir, scheduled follow-up task for {name}."
                )

            if action == "draft_proposal":
                name = params.get("company_name") or params.get("business_name") or "Client"
                scope = params.get("scope_of_work") or "Comprehensive digital revamp, mobile optimization, and conversion engine setup."
                price = params.get("estimated_price") or "Negotiable / Project Milestone based"

                proposal = {
                    "title": f"Project Proposal for {name}",
                    "client": name,
                    "executive_summary": f"This proposal outlines a focused solution for {name} to eliminate technical friction, elevate brand presence, and maximize client acquisition.",
                    "scope_of_work": scope,
                    "deliverables": [
                        "Custom modern responsive interface",
                        "High-speed performance & mobile optimization",
                        "Direct conversion / inquiry / booking flow",
                        "Full deployment and ongoing analytics support"
                    ],
                    "investment": price,
                    "timeline": "2 to 3 weeks from kickoff"
                }
                return ToolResult(
                    success=True,
                    data=proposal,
                    message=f"Sir, I drafted a project proposal for {name}."
                )

            return ToolResult(success=False, error=f"Unknown business action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Business operation failed.")
