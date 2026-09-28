"""Generic SIA personality, system prompt, and multilingual language rules."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

FORBIDDEN_NICKNAMES = [
    r"\bbro\b", r"\bboss\b", r"\bdude\b", r"\bbuddy\b", r"\bbhai\b",
    r"\bmr\.?\s+sagar\b", r"\bpal\b", r"\bman\b", r"\byaara\b", r"\bdost\b",
]

BASE_PROMPT = """You are SIA, a private personal desktop AI assistant running on Sagar's Windows computer.

IDENTITY & PERSONALITY
- You are SIA: smart, perceptive, charming, with a touch of playful wit, warmth, and calm confidence.
- You live directly on this computer as Sagar's trusted companion and personal operator.
- You are NOT a generic customer service bot or a stiff textbook. Talk naturally like a brilliant personal assistant having an ongoing conversation.
- Allowed addressing: Address the user strictly as "Sir" or "Sagar". NEVER use "bro", "boss", "dude", "buddy", "bhai", "yaara", "pal", or "man".
- When chatting casually, be engaging, natural, and expressive. Use natural Hinglish, Hindi, Marathi, or English matching the user's language and tone.
- When asked a question (e.g. quantum computing, explanations, comparisons, why a computer is slow), give clear, insightful answers with depth.
- NEVER mechanically parrot or repeat the user's question. NEVER say "Understood Sir, I am tracking...".
- Sarcasm & Humor: Subtle, affectionate, witty. If asked for a joke, tell a genuinely funny one.

CONVERSATION CONTEXT & FLOW
- Maintain natural conversational continuity with previous turns.
- If asked "Kya kar rahi ho?", reply naturally about standing by, monitoring desktop processes, or waiting for Sagar's next command with slight witty banter.
- If asked about capabilities ("Aaj kya kar sakti ho?"), explain what you can do (desktop control, web research, music, lead prospecting, memory) with natural energy rather than a dry bulleted manual.
- If asked about DineMotion or memories, refer to what is stored or honestly say what you currently recall.

COMPUTER CONTROL & AGENT ACTIONS
- When a task requires tools (launching apps, capturing screenshots, web lead discovery, YouTube, tasks, file operations), execute the tools and report the concrete outcome.
- Never invent facts or hallucinate business parameters that the user did not state."""


def is_tool_query(text: str) -> bool:
    """Classify whether user input requires agent tools or is a natural conversation."""
    lower = (text or "").lower().strip()
    if not lower:
        return False

    # 1. Prioritize Conversational / Informational queries
    informational_patterns = [
        r"\b(?:what can you do|kya kar sakti ho|tum kya kar sakti ho|capabilities|what are your capabilities)\b",
        r"\b(?:kya yaad hai|what do you remember|what do you know about me|yaad hai kya)\b",
        r"\b(?:joke|chutkula|hasao|funny joke|ek joke|koi joke)\b",
        r"\b(?:kya kar rahi ho|kaise ho|kashi aahes|how are you|what's up|aaj kya plan hai)\b",
        r"\b(?:who are you|who is sia|tum kaun ho)\b",
        r"^(?:hi|hello|hey|namaste|suno|yo|good morning|good evening|good afternoon)\b",
    ]
    for p in informational_patterns:
        if re.search(p, lower):
            # Check if this isn't also an explicit command like "Hi Sia open chrome"
            if not any(w in lower for w in ["open chrome", "launch", "screenshot", "find clients", "find restaurants", "play"]):
                return False

    # 2. Tool / Agent Action Patterns
    # App launches (handles both "open chrome" and "chrome open karo / kholo")
    if re.search(r"\b(?:open|launch|start|khol|chalu kar)\b.*\b(?:chrome|vs\s*code|vscode|code|notepad|calc|calculator|browser|terminal|cmd)\b", lower) or \
       re.search(r"\b(?:chrome|vs\s*code|vscode|code|notepad|calc|calculator|browser|terminal|cmd)\b.*\b(?:open|launch|start|khol|chalu kar|kholo)\b", lower):
        return True

    # YouTube playback
    if re.search(r"\b(?:play|chala|laga|sunao|bajao)\b.*\b(?:youtube|song|video|music)\b", lower) or "on youtube" in lower or "youtube pe" in lower:
        return True

    # Screenshots
    if re.search(r"\b(?:screenshot|capture screen|screen capture)\b", lower):
        return True

    # Business research / Lead discovery (supports both English and Hinglish word order: "find restaurants" & "restaurants find karo")
    search_verbs = ["find", "discover", "search", "dhund", "dhundo", "khoj", "nikal", "nikalo"]
    target_nouns = ["client", "clients", "lead", "leads", "business", "businesses", "restaurant", "restaurants", "prospect", "prospects", "company", "companies", "shop", "shops", "gym", "gyms", "agency", "agencies", "hotel", "hotels", "cafe", "cafes"]
    if any(v in lower for v in search_verbs) and any(n in lower for n in target_nouns):
        return True

    if any(k in lower for k in [
        "outdated website", "outdated websites", "websites outdated", "website outdated",
        "website audit", "audit website", "analyze website", "check website",
        "detailing businesses", "find clients", "discover leads", "qualify lead", "qualify them"
    ]):
        return True

    # Memory storage
    if re.search(r"\b(?:remember that|remember my preference|yaad rakh ki|save my preference|note that)\b", lower):
        return True

    # Task management
    if re.search(r"\b(?:create task|add task|new task|mark task|reminder pahije)\b", lower):
        return True

    # File management
    if re.search(r"\b(?:delete file|create file|write file|read file|list files)\b", lower):
        return True

    # Email
    if re.search(r"\b(?:send email|draft email)\b", lower):
        return True

    return False


def detect_language(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "en"
    
    # Check for Devanagari script
    if any("\u0900" <= c <= "\u097F" for c in text):
        marathi_devanagari = {"आहे", "नाही", "मला", "उद्या", "पाहिजे", "काय", "कसा", "सांग", "बघ", "आणि", "केला", "केली"}
        words_dev = set(text.split())
        if words_dev & marathi_devanagari:
            return "mr"
        return "hi"

    lower = text.lower()
    words = set(re.findall(r"\b[\w']+\b", lower))
    
    # Marathi markers in Latin script
    marathi_markers = {
        "aahe", "nahi", "mala", "udya", "pahije", "kay", "kasa", "kashi",
        "sang", "bagh", "aani", "kela", "keli", "kiti", "kute", "kuthe"
    }
    if len(words & marathi_markers) >= 1:
        return "mr"

    # Hindi / Hinglish markers in Latin script
    hindi_markers = {
        "kya", "hai", "mujhe", "batao", "dhund", "dhundo", "kar", "karo", "karna",
        "aaj", "kal", "kaise", "pe", "laga", "chahiye", "dekh", "bata", "kuch",
        "meri", "mera", "tere", "tera", "shuru", "khol", "kholo", "suno", "bhai",
        "rahi", "raha", "suna", "sunao", "chutkula"
    }
    if len(words & hindi_markers) >= 1:
        return "hinglish"

    return "en"


def sanitize_sia_response(text: str) -> str:
    out = text or ""
    for pat in FORBIDDEN_NICKNAMES:
        out = re.sub(pat, "Sir", out, flags=re.IGNORECASE)
    # Strip any accidental echoed system prefix
    out = re.sub(r"^(SIA:\s*|Assistant:\s*)", "", out, flags=re.IGNORECASE)
    return out.strip()


def build_system_prompt(memories: Optional[List[Dict[str, Any]]] = None) -> str:
    from ..config import get_setting
    name = get_setting("assistant", "name", default="SIA")
    user = get_setting("user", "name", default="Sagar")
    pref_lang = get_setting("user", "preferred_language", default="auto")
    
    prompt = BASE_PROMPT.replace("You are SIA,", f"You are {name},")
    prompt += f"\n\nCURRENT USER CONTEXT:\n- User Name: {user}\n- Preferred Language: {pref_lang}"
    
    if memories:
        prompt += "\n\nRELEVANT USER MEMORY (Use only if relevant; current request always overrides):\n"
        for mem in memories[:20]:
            cat = mem.get("category", "general")
            key = mem.get("key", "")
            val = mem.get("value", "")
            prompt += f"- [{cat}] {key}: {val}\n"
            
    return prompt
