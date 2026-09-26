# SIA — Sagar's Personal AI Companion & Computer Agent

> **"She isn't just a chatbot. She lives inside your computer."**

SIA is a local-first, free personal AI assistant created specifically for Sagar. She understands natural conversation in **English, Hindi, Marathi, and Hinglish**, possesses persistent long-term memory, controls the Windows desktop, plays YouTube, assists with **DineMotion Studios** client acquisition, and speaks with a natural neural female voice—all without requiring paid APIs or subscriptions.

---

## ⚡ Quick Start

Double-click:
```text
start_sia.bat
```
This starts the local SIA Core server and automatically opens your desktop command center at `http://127.0.0.1:8000`.

To run system health diagnostics anytime:
```text
diagnose_sia.bat
```

---

## 💎 Core Capabilities

### 1. Identity & Personality
- **Addressing:** SIA will **only** address you as **"Sir"** or **"Sagar"**. Forbidden nicknames (Bro, Boss, Dude, Buddy, Bhai) are strictly blocked.
- **Honest & Witty:** SIA is **not a yes-person**. If an idea has flaws, she will challenge it with wit and logic.
- **Accountability:** Reminds you about procrastination, pending tasks, and follow-ups.

### 2. Voice & Natural Interaction
- **Speech-to-Text:** Speak naturally in English, Hindi, or Marathi.
- **Wake Word:** Say *"Hey Sia"* to wake her up.
- **Push-to-Talk:** Hold the **Spacebar** anywhere in the window to talk.
- **Free Neural Voice:** Powered by edge-tts neural voices:
  - English: `en-IN-NeerjaNeural`
  - Hindi: `hi-IN-SwaraNeural`
  - Marathi: `mr-IN-AarohiNeural`
- **Interruption / Barge-in:** Press **Escape** or click the red Stop button to interrupt SIA speaking instantly.

### 3. Computer Control & Automation
- **YouTube:** Say *"Sia, YouTube pe Arijit Singh ka song laga"* — SIA searches and plays it immediately.
- **Applications:** *"Open Notepad"*, *"Calculator kholo"*, *"Launch Chrome"*, *"Open VS Code"*.
- **Screenshots:** *"Take screenshot"* captures the desktop and saves it to `data/exports/`.
- **Files:** View, search, and manage project files safely.

### 4. DineMotion Studios Prospecting Engine
- Say *"Sia, Nagpur ke restaurants dhund"* — SIA automatically searches popular restaurant websites, runs a UX audit (mobile viewport, online digital menu, reservation CTA), records the opportunities, and prepares personalized outreach drafts.

### 5. Persistent Local Memory (SQLite)
- *"Sia, remember this..."* saves persistent notes across sessions.
- Context drawer shows active projects, pending to-dos, and memories.
- Stored completely privately on your computer in `data/sia.db`.

### 6. Safety & Permissions
- **Low Risk (Auto):** YouTube, Web search, App launching, reading memory.
- **Medium Risk (Confirmation Required):** Sending emails, writing files.
- **High Risk (Explicit Confirmation):** Deleting files, system changes.

---

## 📁 Project Architecture

```text
SIA/
├── backend/
│   ├── main.py                  # FastAPI + WebSocket server
│   ├── config.py                # Configuration loader
│   ├── agent/
│   │   ├── conversation.py      # Conversation manager & Local AI brain
│   │   ├── permissions.py       # 3-tier safety & approval engine
│   │   └── personality.py       # SIA identity & anti-nickname sanitizer
│   ├── memory/
│   │   ├── database.py          # SQLite engine (memories, tasks, leads)
│   │   └── models.py            # Pydantic data models
│   ├── voice/
│   │   └── tts.py               # Free neural & SAPI5 fallback TTS
│   ├── tools/
│   │   ├── youtube.py           # Real YouTube automation
│   │   ├── apps.py              # Windows app launcher
│   │   ├── browser.py           # Web browser navigation
│   │   ├── research.py          # Free search & DineMotion UX audit
│   │   ├── files.py             # File operations
│   │   ├── tasks.py             # Task & reminder management
│   │   ├── memory_tool.py       # Memory persistence
│   │   └── email.py             # Email drafting & confirmed sending
│   └── security/
│       ├── audit.py             # Action audit logging
│       └── secrets.py           # Local secrets management
├── frontend/
│   ├── index.html               # Main desktop command center
│   ├── styles/
│   │   ├── main.css             # Theme tokens & layout
│   │   ├── core.css             # SIA Core visualizer styles
│   │   └── components.css       # Chat, cards, drawers, modals
│   └── src/
│       ├── app.js               # Event coordinator & shortcuts
│       ├── core-visualizer.js   # Canvas audio-reactive SIA Core
│       ├── voice-controller.js  # STT, wake-word, audio analyser
│       ├── chat-manager.js      # Message & action card rendering
│       └── api-client.js        # WebSocket & REST client
├── data/
│   ├── sia.db                   # Persistent SQLite database
│   ├── logs/                    # Audit logs
│   └── exports/                 # Screenshots & audio exports
├── tests/                       # Automated test suite (16 tests)
├── config/
│   └── settings.json            # User & assistant settings
├── start_sia.bat                # 1-Click Desktop Launcher
├── diagnose_sia.bat             # Diagnostic tool
└── install_sia.bat              # Setup script
```

---

## 🧪 Testing

To run the automated test suite anytime:
```bash
.\.venv\Scripts\python.exe -m pytest tests -v
```
All 16 tests verify personality rules, SQLite persistence, permissions, tools, and voice generation.
