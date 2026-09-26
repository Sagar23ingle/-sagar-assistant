# SIA — ORIGINAL UI/UX & VISUAL DESIGN SYSTEM

## DESIGN PRINCIPLE

SIA is not a JARVIS clone, not Siri, and not a generic chatbot.

The interface should feel like:

> **A personal AI presence living inside the computer.**

The UI should be quiet when nothing is happening and become visually alive when SIA is listening, thinking, speaking, or working.

---

# 1. VISUAL PERSONALITY

Keywords:

- futuristic
- minimal
- intelligent
- premium
- calm
- responsive
- slightly mysterious
- functional
- original

Avoid:

- Iron Man reactor replicas
- excessive neon
- sci-fi HUD clutter
- giant dashboards
- unnecessary graphs
- generic AI gradients
- excessive glassmorphism

---

# 2. COLOR SYSTEM

```css
:root {
  --bg-0: #05070d;
  --bg-1: #0a0f1c;
  --bg-2: #111827;

  --cyan: #00d9ff;
  --indigo: #617cff;
  --white: #f4f7ff;

  --success: #00e58a;
  --warning: #ffb020;
  --danger: #ff4d6d;

  --text: #edf2ff;
  --text-muted: #98a3bd;

  --border: rgba(255,255,255,0.08);
  --glass: rgba(15,22,38,0.62);
}
```

Use cyan primarily for SIA's active state.

Use amber only for confirmations/warnings.

Use red only for errors/destructive actions.

---

# 3. TYPOGRAPHY

Primary:

```text
Inter
Segoe UI
system-ui
```

Use:

- 32px display
- 24px headings
- 18px section headings
- 16px body
- 14px secondary
- 12px labels

Never sacrifice readability for futuristic styling.

---

# 4. MAIN SCREEN

The main screen should have five visual zones:

```text
TOP
Status + Settings

CENTER
SIA Core

MIDDLE
Conversation / Current Context

LOWER
Activity when working

BOTTOM
Talk or Type
```

The screen should breathe.

Do not fill every pixel.

---

# 5. SIA CORE

The SIA Core is the visual identity.

Do not create a generic glowing orb.

Use a custom combination of:

- circular waveform
- subtle geometric rings
- central pulse
- tiny particle field
- audio-reactive motion

The exact shape should be original.

---

# 6. CORE STATES

## IDLE

Appearance:

- small/medium core
- very slow movement
- low glow
- almost silent animation

Meaning:

> SIA is present and ready.

---

## LISTENING

Appearance:

- brighter cyan
- waveform responds to microphone
- central pulse expands
- subtle outward rings

Meaning:

> SIA is listening.

---

## THINKING

Appearance:

- geometric rings rotate
- waveform disappears
- movement becomes more structured
- blue/indigo emphasis

Meaning:

> SIA is processing.

---

## SPEAKING

Appearance:

- waveform responds to audio
- pulse follows speech rhythm
- subtle glow changes

Meaning:

> SIA is speaking.

---

## WORKING

Appearance:

- core remains active
- progress ring
- subtle moving particles

Meaning:

> SIA is performing a task.

---

## SUCCESS

Appearance:

- brief cyan/green expansion
- return to idle

Never make success animation obnoxious.

---

## ERROR

Appearance:

- short red pulse
- tiny shake
- return to stable state

---

# 7. CONVERSATION UI

Messages should feel integrated into the environment.

SIA messages:

```text
┌───────────────────────────────┐
│ SIA                           │
│ Alright, Sir. I'm checking it │
└───────────────────────────────┘
```

Sagar messages:

```text
                         ┌──────────────────────┐
                         │ Find restaurants.    │
                         └──────────────────────┘
```

Use:

- subtle glass
- thin borders
- small radius
- no cartoon chat bubbles

---

# 8. INPUT BAR

Bottom-center:

```text
┌──────────────────────────────────────────────┐
│ Talk or type...                       ◉  ↑   │
└──────────────────────────────────────────────┘
```

Controls:

- text input
- microphone
- send
- stop when speaking

Voice button should visibly react.

---

# 9. LIVE TRANSCRIPTION

During voice:

```text
Listening...

"Find restaurants in Nagpur whose websites..."
```

Show partial transcript subtly.

When final:

```text
You:
Find restaurants in Nagpur...
```

---

# 10. ACTIVITY VIEW

When SIA is working, show a compact activity card.

Example:

```text
WORKING

Finding restaurant prospects

✓ Search completed
✓ 12 businesses found
✓ 8 websites checked
→ Analyzing UX...
```

Keep it concise.

---

# 11. CONTEXT VIEW

Expandable right-side panel:

```text
CURRENT CONTEXT

Project
DineMotion Studios

Task
Restaurant outreach

Progress
8 / 20

Pending
3 follow-ups
```

Do not show this panel permanently if it distracts from conversation.

---

# 12. SETTINGS DESIGN

Use a clean side navigation:

```text
SIA

Conversation
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

Each section should use simple cards.

---

# 13. VOICE SETTINGS

Controls:

- TTS engine
- local voice/model
- speed
- volume
- language
- test button

Show:

```text
LOCAL VOICE
● Ready

Language
Auto

Speed
1.0x
```

Never display API keys.

---

# 14. PERSONALITY SETTINGS

Allow:

```text
Response style
○ Concise
● Natural
○ Detailed

Playfulness
██████░░

Sarcasm
████░░░░

Proactive behavior
ON
```

Defaults should match SIA's personality specification.

---

# 15. MEMORY UI

Example:

```text
MEMORY

Personal
12 memories

Projects
27 memories

Preferences
9 memories

Recent
5 memories
```

Each memory should be:

- viewable
- editable
- deletable

Provide:

```text
Search memory...
```

---

# 16. PERMISSIONS UI

Show tools:

```text
Browser                  Allowed
Files                    Ask
Email read               Allowed
Email send               Ask
File delete              Always confirm
System changes           Always confirm
```

Use clear status indicators.

---

# 17. ACTIVITY LOG

A chronological local log:

```text
10:32  Opened Chrome
10:35  Searched YouTube
10:40  Analyzed website
10:44  Drafted client email
10:45  Waiting for confirmation
```

Allow filtering by:

- Browser
- Files
- Email
- Research
- System

---

# 18. NOTIFICATIONS

Notifications should be subtle.

Examples:

```text
SIA
Follow-up due for Goel Mobile.
```

Do not interrupt unnecessarily.

Support quiet hours.

---

# 19. RESPONSIVE DESIGN

Desktop:

- full SIA Core
- context panel
- activity panel

Tablet:

- collapsible context

Mobile:

- smaller core
- full-width chat
- bottom input
- simplified navigation

---

# 20. MICRO-INTERACTIONS

Use short transitions:

- 150–300ms
- ease-out entrances
- ease-in exits

Every animation must communicate something.

Respect:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
```

---

# 21. ACCESSIBILITY

Minimum:

- keyboard navigation
- visible focus
- readable contrast
- ARIA labels
- reduced motion
- adequate button size
- screen-reader-friendly status

---

# 22. DESKTOP APP FEEL

The app should not look like a website opened in Chrome.

Prefer:

- frameless/minimal desktop shell where practical
- subtle window background
- custom title bar only if it improves usability
- native OS notifications where appropriate
- global keyboard shortcut
- minimize-to-tray option

The user should feel that SIA is part of the computer.

---

# 23. OPTIONAL AMBIENT MODE

When SIA is idle, provide an optional ambient mode.

Example:

- small floating SIA Core
- minimal status
- no chat window
- wake word active if enabled

Clicking/shortcut expands into the full command center.

This helps SIA feel like an assistant rather than an app.

---

# 24. ORIGINALITY RULE

Do NOT reproduce:

- JARVIS HUD
- Iron Man reactor
- Siri visual design
- Alexa visual design
- ChatGPT UI exactly
- another product's trademark interface

Take inspiration from futuristic computing, but create a distinct SIA visual language.

---

# 25. FINAL UI FEEL

When Sagar opens SIA, the first impression should be:

> "She's here."

When SIA listens:

> "She's paying attention."

When SIA thinks:

> "She's working."

When SIA speaks:

> "She's responding."

When SIA performs a task:

> "She's actually doing it."

The interface exists to reinforce the assistant's intelligence and presence—not to distract from it.
