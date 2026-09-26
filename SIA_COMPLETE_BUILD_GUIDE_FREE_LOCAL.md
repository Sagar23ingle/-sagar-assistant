# SIA — COMPLETE FREE / LOCAL-FIRST BUILD GUIDE

This document is the implementation companion for `SIA_MASTER_BUILD_PROMPT.md`.

The original SIA requirements have been consolidated into one practical architecture. The most important change is that **paid cloud APIs are NOT required**. Local/open-source components are the default.

---

## 1. COST POLICY

SIA must work without:

- Claude API
- OpenAI API
- Gemini API
- ElevenLabs
- Google Cloud TTS
- Azure TTS
- Paid search APIs
- Paid automation platforms
- Paid hosting
- Paid vector databases

Optional cloud adapters may be added later, but they must never be required.

Core operation should be local.

---

# 2. RECOMMENDED ARCHITECTURE

```text
                    ┌─────────────────────┐
                    │     SIA UI          │
                    │ Desktop Command     │
                    │ Center / Voice UI   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Conversation Manager│
                    └──────────┬──────────┘
                               │
                 ┌─────────────▼─────────────┐
                 │      LOCAL AI BRAIN       │
                 │       Local LLM           │
                 └─────────────┬─────────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
      ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
      │ Memory      │  │ Permission  │  │ Tool Router │
      │ SQLite      │  │ Manager     │  │             │
      └─────────────┘  └──────┬──────┘  └──────┬──────┘
                               │                 │
                ┌──────────────┼─────────────────┼─────────────┐
                │              │                 │             │
             Browser         Files            Email        Computer
             YouTube         Tasks            Research      Control
                │              │                 │             │
                └──────────────┴─────────────────┴─────────────┘

Voice:
Microphone → Local STT → Conversation Manager → Local TTS → Speaker
```

---

# 3. PROJECT STRUCTURE

Use a maintainable structure:

```text
SIA/
│
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── components/
│   │   ├── styles/
│   │   ├── services/
│   │   └── state/
│   └── assets/
│
├── backend/
│   ├── main.py
│   ├── agent/
│   │   ├── conversation.py
│   │   ├── planner.py
│   │   ├── permissions.py
│   │   └── personality.py
│   │
│   ├── memory/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── retrieval.py
│   │
│   ├── voice/
│   │   ├── stt.py
│   │   ├── tts.py
│   │   ├── vad.py
│   │   └── wakeword.py
│   │
│   ├── tools/
│   │   ├── browser.py
│   │   ├── youtube.py
│   │   ├── files.py
│   │   ├── apps.py
│   │   ├── screenshots.py
│   │   ├── research.py
│   │   ├── email.py
│   │   └── tasks.py
│   │
│   └── security/
│       ├── secrets.py
│       └── audit.py
│
├── models/
├── data/
│   ├── sia.db
│   ├── logs/
│   └── exports/
│
├── scripts/
│   ├── install.ps1
│   ├── start.ps1
│   └── diagnose.ps1
│
├── tests/
├── config/
├── requirements.txt
├── .env.example
├── README.md
└── start_sia.bat
```

---

# 4. LOCAL AI BRAIN

SIA needs a local LLM runtime.

Use a replaceable adapter rather than hard-coding one model.

Concept:

```python
class LLMProvider:
    async def generate(self, messages, tools=None, context=None):
        raise NotImplementedError
```

Then:

```text
providers/
├── local_llm.py
└── optional_cloud.py
```

The local provider is the default.

A local runtime such as Ollama, llama.cpp, or another suitable open-source runtime may be used depending on Sagar's machine.

The development agent should:

1. Detect available hardware.
2. Check RAM/VRAM.
3. Recommend a reasonable local model size.
4. Download/configure only if Sagar explicitly agrees where large downloads are involved.
5. Keep the model replaceable.

Do not assume one model is universally best.

---

# 5. LOCAL STT

Use an open-source/local speech recognition implementation.

Possible architecture:

```text
Microphone
 ↓
Voice Activity Detection
 ↓
Local STT
 ↓
Transcript
 ↓
Language Detection
 ↓
Conversation Manager
```

A local Whisper-family implementation is a reasonable starting point if the hardware supports it.

Requirements:

- English
- Hindi
- Marathi
- Hinglish
- noise tolerance
- partial/live transcription when practical

The STT implementation must be behind:

```python
class STTProvider:
    async def transcribe(self, audio):
        ...
```

---

# 6. LOCAL TTS

TTS must be local/open-source by default.

Architecture:

```python
class TTSProvider:
    async def speak(self, text, language=None, emotion=None):
        ...
```

Test local engines/models for:

- English
- Hindi
- Marathi
- Hinglish

Do not assume one model will produce perfect Marathi/Hinglish.

If necessary:

```text
Language Detector
       ↓
┌──────┼─────────┐
English Hindi  Marathi
  ↓       ↓       ↓
TTS-A   TTS-B   TTS-C
       ↓
Same SIA personality
```

The user experience should remain consistent even if different local models are used internally.

No paid cloud TTS fallback is required.

---

# 7. VOICE STATES

Implement:

```text
IDLE
LISTENING
THINKING
SPEAKING
WORKING
SUCCESS
WARNING
ERROR
```

Frontend state must be driven by actual backend events.

Example:

```text
LISTENING
   ↓
TRANSCRIBING
   ↓
THINKING
   ↓
TOOL_EXECUTION
   ↓
SPEAKING
   ↓
IDLE
```

---

# 8. INTERRUPTION

When Sagar says "stop":

1. Cancel TTS playback.
2. Cancel pending speech generation where possible.
3. Stop active response audio.
4. Return UI to listening/idle.
5. Allow a new request immediately.

Never allow overlapping SIA speech.

---

# 9. MEMORY

Use SQLite.

Suggested schema:

```sql
memories
---------
id
category
key
value
importance
created_at
updated_at

conversations
-------------
id
session_id
role
content
timestamp

tasks
-----
id
title
description
due_at
priority
status
created_at

projects
--------
id
name
description
status

leads
-----
id
business_name
website
contact
location
issues
pitch_angle
status
follow_up_at

actions
-------
id
tool
description
permission_level
result
timestamp
```

Provide memory APIs:

```text
remember()
recall()
search_memory()
update_memory()
delete_memory()
```

---

# 10. PERMISSION ENGINE

Every tool must have a permission level.

```python
LOW
MEDIUM
HIGH
```

Example:

```text
browser.open_url        LOW
youtube.play            LOW
email.read              LOW
email.send              MEDIUM
file.rename             MEDIUM
file.delete             HIGH
password.change         HIGH
financial_action        HIGH
```

The tool router must check permissions BEFORE execution.

---

# 11. TOOL EXECUTION

Never let the LLM execute arbitrary shell commands.

Instead:

```text
LLM request
 ↓
Tool parser
 ↓
Schema validation
 ↓
Permission check
 ↓
Confirmation if required
 ↓
Tool execution
 ↓
Result validation
 ↓
Response
```

---

# 12. COMPUTER CONTROL

For Windows, use free/local libraries.

Possible tools:

- Python subprocess
- PyAutoGUI
- Playwright
- Selenium
- Windows-native APIs where appropriate

Capabilities:

- launch apps
- open folders
- open URLs
- keyboard/mouse automation
- screenshots
- browser interaction
- file organization

Use allowlists for sensitive operations.

---

# 13. YOUTUBE

Implement a real YouTube tool.

Flow:

```text
"Sia, YouTube pe X laga"
        ↓
Interpret song
        ↓
Open browser / existing browser
        ↓
Search YouTube
        ↓
Choose result
        ↓
Play
        ↓
Return result
```

If automatic clicking fails, report the actual failure.

---

# 14. WEB RESEARCH

Avoid paid APIs.

Use:

- browser search
- direct HTTP requests
- BeautifulSoup
- Playwright
- local parsing

Architecture:

```text
Query
 ↓
Search
 ↓
Collect public pages
 ↓
Extract text
 ↓
Analyze
 ↓
Return structured findings
```

Use sensible rate limiting.

Do not bypass:

- authentication
- CAPTCHAs
- access controls
- private pages

---

# 15. DINEMOTION LEAD ENGINE

Create a reusable pipeline:

```text
Business discovery
      ↓
Website detection
      ↓
Website fetch
      ↓
Website analysis
      ↓
Opportunity detection
      ↓
Lead record
      ↓
Personalized pitch
      ↓
Review
      ↓
Optional outreach
```

Website analysis should look at:

- responsive behavior
- visual age
- menu experience
- CTA
- booking/contact
- obvious UX issues
- performance signals
- missing modern features

Never invent an issue that was not actually observed.

---

# 16. EMAIL

Gmail integration should be isolated.

Capabilities:

```text
read
search
summarize
draft
follow-up
send
```

Sending requires confirmation.

Example UI:

```text
┌─────────────────────────────────────┐
│ SEND EMAIL?                         │
│                                     │
│ To: client@example.com              │
│ Subject: Website redesign           │
│                                     │
│ [Cancel]                [Send]      │
└─────────────────────────────────────┘
```

Never expose OAuth tokens in frontend code.

---

# 17. TASK SYSTEM

Tasks should be locally stored.

Support:

- one-time reminders
- recurring reminders
- priorities
- due dates
- completion
- overdue status

Use OS scheduling/background process where appropriate.

---

# 18. PROACTIVE ENGINE

Do not continuously interrupt Sagar.

Use an event queue:

```text
Task due
Email arrived
Follow-up due
Workflow completed
System warning
      ↓
Proactive Engine
      ↓
Should I interrupt?
      ↓
Notification / quiet
```

Allow settings:

- proactive ON/OFF
- quiet hours
- notification level

---

# 19. FRONTEND UI

The UI should be original.

### Visual direction

- near-black/deep navy background
- cyan/indigo accents
- subtle glass
- thin borders
- restrained glow
- clean modern typography
- futuristic but not cliché

Do not copy JARVIS.

---

# 20. MAIN SCREEN

Desktop:

```text
┌────────────────────────────────────────────────────┐
│ SIA                                  ● READY       │
│                                                    │
│                                                    │
│                  ╭──────────╮                      │
│                  │ SIA CORE  │                      │
│                  ╰──────────╯                      │
│                                                    │
│      Current activity / short contextual text     │
│                                                    │
│  SIA: "Alright, Sir. I'm checking the websites."  │
│                                                    │
│                         You: "Find restaurants..." │
│                                                    │
│ ┌────────────────────────────────────────────────┐ │
│ │ Talk or type...                         🎙  ↑  │ │
│ └────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

Do not make the interface overcrowded.

---

# 21. SIA CORE DESIGN

Central hero element:

- SVG/canvas-based animated core
- waveform ring
- center pulse
- state-dependent motion

States:

### Idle
Slow, subtle.

### Listening
Waveform responds to microphone.

### Thinking
Rotating geometry.

### Speaking
Responds to speech amplitude if available.

### Working
Shows task progress.

### Success
Short confirmation burst.

### Error
Short warning state.

---

# 22. CHAT

SIA:

- left
- subtle cyan glass

Sagar:

- right
- subtle blue glass

Keep messages readable.

Support:

- text
- code
- links
- action results
- progress states
- confirmation cards

---

# 23. ACTIVITY PANEL

When SIA works:

```text
ACTIVITY

Finding restaurants...
✓ 12 businesses found
✓ 9 websites checked
✓ 5 potential prospects identified
→ Preparing personalized pitches...
```

Technical logs remain hidden unless opened.

---

# 24. SETTINGS

Settings sections:

```text
Voice
Speech
Personality
Memory
Permissions
Automation
Privacy
Appearance
About
```

Allow Sagar to change:

- voice
- TTS model
- STT model
- microphone
- wake word
- language
- speaking speed
- personality intensity
- sarcasm level
- proactive behavior
- memory
- permissions

---

# 25. PRIVACY CENTER

Create a visible privacy page.

Show:

- local memory status
- internet usage
- connected services
- microphone status
- recent external actions
- clear memory
- export memory
- delete selected memory

Default:

> Local-first.

---

# 26. ACTION LOG

Record important actions:

```text
11:02
Opened Chrome

11:05
Searched YouTube

11:10
Drafted email
Waiting for confirmation

11:12
Email sent after confirmation
```

Keep logs local.

---

# 27. DESIGN SYSTEM

Use CSS variables.

Example:

```css
:root {
  --bg: #070a12;
  --panel: rgba(20, 25, 40, 0.65);
  --cyan: #00d9ff;
  --blue: #4f7cff;
  --green: #00e58a;
  --amber: #ffb020;
  --red: #ff4d6d;
  --text: #eef2ff;
  --muted: #9aa4bd;
  --border: rgba(255,255,255,0.08);
}
```

Use restrained color.

---

# 28. RESPONSIVE DESIGN

Desktop is primary.

Tablet:

- compact context panel

Mobile:

- smaller SIA Core
- full-width conversation
- bottom interaction bar
- simplified navigation

---

# 29. ACCESSIBILITY

Implement:

- keyboard navigation
- focus indicators
- ARIA labels
- readable contrast
- reduced motion
- proper button sizes
- screen-reader-friendly controls

---

# 30. PERFORMANCE

Target:

- smooth UI
- minimal background CPU
- lazy-load heavy resources
- avoid unnecessary polling
- do not keep GPU-heavy effects running continuously
- unload inactive models where practical

Voice models and LLMs may be the largest resource consumers; expose resource status.

---

# 31. INSTALLATION

For Windows, create:

```text
install_sia.bat
start_sia.bat
diagnose_sia.bat
```

Installation flow:

```text
Check Python/runtime
 ↓
Create virtual environment
 ↓
Install dependencies
 ↓
Create directories
 ↓
Check audio
 ↓
Check local model runtime
 ↓
Run diagnostics
 ↓
Launch SIA
```

---

# 32. DIAGNOSTICS

Create a diagnostics command that reports:

```text
SIA Diagnostics

✓ Python
✓ Database
✓ Local LLM runtime
✓ STT
✓ TTS
✓ Microphone
✓ Audio output
✓ Browser
✓ Computer control
✓ Memory
✓ Permissions
```

If something fails:

```text
✗ TTS
Reason: model not installed
Fix: ...
```

---

# 33. TESTING

Test:

### Text

- conversation
- language switching
- personality
- context

### Memory

- create
- retrieve
- edit
- delete

### Voice

- microphone
- STT
- TTS
- interruption

### Computer

- launch application
- browser
- YouTube
- file operations

### Security

- confirmation
- blocked destructive actions
- secret handling

### UI

- responsive
- animations
- accessibility
- settings

---

# 34. BUILD ORDER

### Milestone 1

Working local text assistant:

- local LLM
- personality
- memory
- polished UI

### Milestone 2

Voice:

- STT
- TTS
- microphone
- interruption

### Milestone 3

Computer:

- apps
- browser
- YouTube
- files

### Milestone 4

Work agent:

- tasks
- research
- DineMotion lead engine

### Milestone 5

Communication:

- Gmail
- drafts
- confirmations
- follow-ups

### Milestone 6

Autonomy:

- proactive tasks
- monitoring
- multi-step workflows

### Milestone 7

Polish:

- performance
- security
- accessibility
- installer
- diagnostics

---

# 35. IMPORTANT DEVELOPMENT RULE

Never tell Sagar:

> "This is done"

unless the feature has actually been tested.

Never replace a requested capability with:

- fake data
- fake progress
- fake AI responses
- fake browser actions
- fake voice
- placeholder buttons

Temporary mocks are allowed during development but must be clearly marked and replaced before completion.

---

# 36. FINAL PRODUCT

The final SIA should feel like:

> **A real female AI assistant living inside Sagar's Windows computer.**

Sagar should be able to say:

> "Hey Sia."

and naturally talk to her.

She should:

- listen
- understand
- remember
- speak
- reason
- disagree
- help
- research
- act
- control the computer
- manage tasks
- find DineMotion leads
- draft outreach
- safely interact with email
- protect privacy
- operate without mandatory paid APIs

That is the target.
