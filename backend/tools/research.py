"""Generic web research and website analysis. No fixed city or brand."""
from __future__ import annotations
import re, urllib.parse
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel
from ..memory.database import add_lead

HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}

class ResearchTool(BaseTool):
    name="research.search"
    description="General web research: search the web, analyze any website, or discover business prospects for a requested niche and location. Never assume a location that the user did not provide."
    risk_level=RiskLevel.LOW
    def get_parameter_schema(self):
        return {"type":"object","properties":{
            "action":{"type":"string","enum":["search","analyze_website","find_business_leads"]},
            "query":{"type":"string"},"url":{"type":"string"},"industry":{"type":"string"},
            "location":{"type":"string"},"country":{"type":"string"},"limit":{"type":"integer"}
        },"required":["action"]}
    async def execute(self,params,user_confirmed=False):
        try:
            a=params.get("action","search")
            if a=="search":
                q=(params.get("query") or "").strip()
                results=await self._search(q, int(params.get("limit") or 8)) if q else []
                return ToolResult(success=True,data={"query":q,"results":results},message=f"Sir, I found {len(results)} results.")
            if a=="analyze_website":
                url=params.get("url","")
                report=await self._analyze(url)
                return ToolResult(success=True,data=report,message=f"Sir, website analysis is complete for {report.get('url') }.")
            if a=="find_business_leads":
                industry=(params.get("industry") or "businesses").strip()
                location=(params.get("location") or "").strip()
                country=(params.get("country") or "").strip()
                if not location and not country:
                    return ToolResult(success=False,error="A location or country is required for targeted lead discovery.")
                scope=" ".join(x for x in [industry,location,country] if x)
                results=await self._search(f"{scope} businesses official website contact", int(params.get("limit") or 10))
                leads=[]
                for item in results:
                    name=item["title"].split("|")[0].split("-")[0].strip()
                    lead=await add_lead(name,item["url"],"",location or country, item.get("snippet", ""), f"Research {industry} prospect and personalize outreach.")
                    leads.append(lead)
                return ToolResult(success=True,data={"industry":industry,"location":location,"country":country,"leads":leads},message=f"Sir, I found {len(leads)} prospect candidates for {industry} in {location or country}.")
            return ToolResult(success=False,error=f"Unknown research action: {a}")
        except Exception as e:
            return ToolResult(success=False,error=str(e),message="Research failed.")
    async def _search(self,q,max_results=8):
        encoded=urllib.parse.quote_plus(q); url=f"https://html.duckduckgo.com/html/?q={encoded}"; out=[]
        try:
            async with httpx.AsyncClient(timeout=12,follow_redirects=True) as client:
                r=await client.get(url,headers=HEADERS)
                if r.status_code!=200:return out
                soup=BeautifulSoup(r.text,"html.parser")
                for block in soup.select(".result__body")[:max_results]:
                    a=block.select_one(".result__title a"); sn=block.select_one(".result__snippet")
                    if not a: continue
                    href=a.get("href","")
                    m=re.search(r"uddg=([^&]+)",href)
                    if m: href=urllib.parse.unquote(m.group(1))
                    out.append({"title":a.get_text(" ",strip=True),"url":href,"snippet":sn.get_text(" ",strip=True) if sn else ""})
        except Exception: pass
        return out
    async def _analyze(self,url):
        if not url.startswith(("http://","https://")): url="https://"+url
        report={"url":url,"title":"","https":url.startswith("https"),"has_viewport":False,"has_contact":False,"has_social":False,"opportunities":[]}
        try:
            async with httpx.AsyncClient(timeout=12,follow_redirects=True) as client:
                r=await client.get(url,headers=HEADERS); soup=BeautifulSoup(r.text,"html.parser")
                report["title"]=(soup.title.get_text(strip=True) if soup.title else "")
                report["has_viewport"]=bool(soup.find("meta",attrs={"name":"viewport"}))
                texts=" ".join(x.get_text(" ",strip=True).lower() for x in soup.find_all(["a","button","nav"]))
                report["has_contact"]=any(k in texts for k in ["contact","call","email","book","quote","whatsapp"])
                report["has_social"]=any(k in texts for k in ["instagram","facebook","linkedin","twitter"])
                if not report["has_viewport"]: report["opportunities"].append("Improve mobile responsiveness")
                if not report["has_contact"]: report["opportunities"].append("Add a stronger contact / conversion CTA")
                if not report["has_social"]: report["opportunities"].append("Expose relevant social proof or social links")
        except Exception as e: report["error"]=str(e)
        return report
