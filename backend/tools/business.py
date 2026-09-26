"""Advanced business operator skill: prospects, research, qualification, outreach."""
from __future__ import annotations
from typing import Any
from .base import BaseTool, ToolResult
from .research import ResearchTool
from ..agent.permissions import RiskLevel
from ..memory.database import add_lead

class BusinessOpsTool(BaseTool):
    name="business.manage"
    description="Advanced business workflow: discover prospects from a requested market, research companies, qualify/score leads, save leads, and write personalized outreach. Use user-provided market/location; never assume Nagpur or any brand."
    risk_level=RiskLevel.LOW
    def get_parameter_schema(self):
        return {"type":"object","properties":{
            "action":{"type":"string","enum":["discover_leads","company_research","qualify_lead","draft_outreach","save_lead"]},
            "industry":{"type":"string"},"location":{"type":"string"},"country":{"type":"string"},"limit":{"type":"integer"},
            "company_name":{"type":"string"},"website":{"type":"string"},"pain_points":{"type":"string"},"offer":{"type":"string"},
            "contact_name":{"type":"string"},"channel":{"type":"string","enum":["email","whatsapp","linkedin","dm"]},
            "business_name":{"type":"string"},"notes":{"type":"string"}
        },"required":["action"]}
    async def execute(self,params,user_confirmed=False):
        action=params.get("action","discover_leads")
        research=ResearchTool()
        try:
            if action=="discover_leads":
                industry=params.get("industry") or "businesses"; location=params.get("location") or ""; country=params.get("country") or ""; limit=int(params.get("limit") or 10)
                res=await research.execute({"action":"find_business_leads","industry":industry,"location":location,"country":country,"limit":limit})
                return res
            if action=="company_research":
                name=(params.get("company_name") or "").strip(); website=(params.get("website") or "").strip()
                q=f"{name} official website company services contact" if name else website
                results=await research._search(q,8)
                report={"company_name":name,"website":website,"search_results":results}
                if website: report["website_analysis"]=await research._analyze(website)
                elif results: report["website_analysis"]=await research._analyze(results[0]["url"])
                return ToolResult(success=True,data=report,message=f"Sir, I researched {name or 'that company'}.")
            if action=="qualify_lead":
                name=params.get("company_name") or params.get("business_name") or "Unknown"; website=params.get("website") or ""
                pain=params.get("pain_points") or ""; notes=params.get("notes") or ""
                score=50
                if website: score+=15
                if pain: score+=20
                if notes: score+=10
                if not website: score-=15
                score=max(0,min(100,score))
                band="high" if score>=75 else "medium" if score>=50 else "low"
                return ToolResult(success=True,data={"company_name":name,"score":score,"band":band,"reasoning":"Based on supplied website, pain points, and notes; not a guarantee of buying intent."},message=f"Sir, {name} has a {band} qualification signal ({score}/100) based on the available evidence.")
            if action=="draft_outreach":
                name=params.get("company_name") or "there"; contact=params.get("contact_name") or "there"; offer=params.get("offer") or "a practical growth improvement"; pain=params.get("pain_points") or "a few obvious opportunities"; channel=params.get("channel") or "email"
                if channel=="email":
                    subject=f"A quick idea for {name}"
                    body=f"Hi {contact},\n\nI was looking at {name} and noticed {pain}. I have a focused idea around {offer} that could improve the current experience without turning this into a huge project.\n\nWould a quick 10-minute look be useful?\n\nRegards,\nSagar"
                    data={"channel":channel,"subject":subject,"body":body}
                else:
                    data={"channel":channel,"message":f"Hi {contact}, noticed {pain} at {name}. I have a focused idea around {offer}. Open to a quick 10-minute look?"}
                return ToolResult(success=True,data=data,message=f"Sir, I drafted personalized {channel} outreach for {name}.")
            if action=="save_lead":
                name=params.get("business_name") or params.get("company_name") or "Unnamed lead"
                lead=await add_lead(name,params.get("website", ""),params.get("contact_name", ""),params.get("location") or params.get("country") or "",params.get("pain_points", ""),params.get("offer", ""))
                return ToolResult(success=True,data=lead,message=f"Sir, {name} is saved to your local lead memory.")
            return ToolResult(success=False,error=f"Unknown business action: {action}")
        except Exception as e:
            return ToolResult(success=False,error=str(e),message="Business workflow failed.")
