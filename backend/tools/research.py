"""SIA Free Web Research & DineMotion Website Analysis Tool
Zero-cost, local-first search and website UX analysis for restaurant client acquisition.
"""

import re
import urllib.parse
from typing import Any, Dict, List
import httpx
from bs4 import BeautifulSoup
from .base import BaseTool, ToolResult
from ..agent.permissions import RiskLevel
from ..memory.database import add_lead

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class ResearchTool(BaseTool):
    name = "research.search"
    description = "Searches the web for businesses, answers, or links using free search."
    risk_level = RiskLevel.LOW

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search", "analyze_website", "find_restaurant_leads"]},
                "query": {"type": "string", "description": "Search query"},
                "url": {"type": "string", "description": "Website URL to analyze"},
                "city": {"type": "string", "description": "City for business leads, defaults to Nagpur"},
            },
            "required": ["action"],
        }

    async def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        action = params.get("action", "search")

        try:
            if action == "search":
                query = params.get("query", "")
                if not query:
                    return ToolResult(success=False, error="Query parameter is required.")
                results = await self._search_duckduckgo(query)
                return ToolResult(
                    success=True,
                    data={"query": query, "results": results},
                    message=f"Sir, I found {len(results)} relevant results for '{query}'.",
                )

            elif action == "analyze_website":
                url = params.get("url", "")
                if not url:
                    return ToolResult(success=False, error="URL is required for analysis.")
                analysis = await self._analyze_website_ux(url)
                return ToolResult(
                    success=True,
                    data=analysis,
                    message=f"Sir, analysis of {url} completed. Score: {analysis.get('modern_score', 0)}/100.",
                )

            elif action == "find_restaurant_leads":
                city = params.get("city", "Nagpur")
                leads = await self._discover_restaurant_leads(city)
                return ToolResult(
                    success=True,
                    data={"city": city, "leads": leads},
                    message=f"Sir, I identified {len(leads)} restaurant prospects in {city} for DineMotion Studios.",
                )

            else:
                return ToolResult(success=False, error=f"Unknown research action: {action}")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message="Research operation failed.")

    async def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Free DuckDuckGo HTML parser without API keys."""
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        results = []

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                res = await client.get(url, headers=HEADERS)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.select(".result__body")
                    for link in links[:max_results]:
                        title_el = link.select_one(".result__title a")
                        snippet_el = link.select_one(".result__snippet")
                        if title_el:
                            href = title_el.get("href", "")
                            # Unwrap DDG redirect link if needed
                            if "uddg=" in href:
                                match = re.search(r"uddg=([^&]+)", href)
                                if match:
                                    href = urllib.parse.unquote(match.group(1))

                            results.append({
                                "title": title_el.get_text(strip=True),
                                "url": href,
                                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                            })
        except Exception:
            pass

        return results

    async def _analyze_website_ux(self, url: str) -> Dict[str, Any]:
        """Analyzes website for DineMotion: responsive meta, modern styling, CTA, menu UX."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        report = {
            "url": url,
            "has_viewport": False,
            "has_ssl": url.startswith("https"),
            "has_online_menu": False,
            "has_reservation_cta": False,
            "missing_features": [],
            "opportunities": [],
            "modern_score": 50,
            "title": "",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(url, headers=HEADERS)
                soup = BeautifulSoup(res.text, "html.parser")

                title = soup.title.string.strip() if soup.title else ""
                report["title"] = title

                # Viewport meta for mobile responsiveness
                vp = soup.find("meta", attrs={"name": "viewport"})
                report["has_viewport"] = vp is not None
                if not report["has_viewport"]:
                    report["missing_features"].append("Mobile viewport meta tag missing (bad on phones)")
                    report["opportunities"].append("Mobile optimization & responsive rebuild")

                # Check online menu
                menu_keywords = ["menu", "food", "dishes", "cuisine", "items", "catalog"]
                for a in soup.find_all(["a", "button", "nav"]):
                    text = a.get_text().lower()
                    if any(k in text for k in menu_keywords):
                        report["has_online_menu"] = True
                        break

                if not report["has_online_menu"]:
                    report["missing_features"].append("No interactive online digital menu found")
                    report["opportunities"].append("Add interactive digital visual menu with high-res photos")

                # Check reservation / call-to-action
                cta_keywords = ["book", "reserve", "table", "order", "whatsapp", "call"]
                for a in soup.find_all(["a", "button"]):
                    text = a.get_text().lower()
                    if any(k in text for k in cta_keywords):
                        report["has_reservation_cta"] = True
                        break

                if not report["has_reservation_cta"]:
                    report["missing_features"].append("No clear table reservation or direct WhatsApp CTA")
                    report["opportunities"].append("Implement direct 1-click WhatsApp booking & table reservation flow")

                # Score calculation
                score = 30
                if report["has_viewport"]:
                    score += 25
                if report["has_ssl"]:
                    score += 15
                if report["has_online_menu"]:
                    score += 15
                if report["has_reservation_cta"]:
                    score += 15
                report["modern_score"] = score

        except Exception as e:
            report["error"] = str(e)
            report["missing_features"].append(f"Site unreachable or slow: {e}")
            report["modern_score"] = 20

        return report

    async def _discover_restaurant_leads(self, city: str = "Nagpur") -> List[Dict[str, Any]]:
        """Finds sample real restaurant targets in Nagpur/city and creates lead records."""
        query = f"top popular restaurants in {city} official website"
        search_results = await self._search_duckduckgo(query, max_results=4)

        discovered = []
        for item in search_results:
            url = item["url"]
            name = item["title"].split("-")[0].split("|")[0].strip()

            analysis = await self._analyze_website_ux(url)
            issues_summary = "; ".join(analysis.get("missing_features", [])) or "Outdated visual layout and menu"
            pitch = f"Focus on mobile menu experience and direct table reservation for {city} diners."

            lead = await add_lead(
                business_name=name,
                website=url,
                contact="Via website / contact page",
                location=city,
                issues=issues_summary,
                pitch_angle=pitch,
            )
            discovered.append(lead)

        return discovered
