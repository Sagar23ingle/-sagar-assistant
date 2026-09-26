# SIA V2 Assistant Rebuild Patch

This overlay is designed for the existing `-sagar-assistant` repository.

## What changed

- Removed business-specific branding/context from the assistant identity.
- Replaced keyword-only tool routing with a model-driven hybrid agent.
- Added Gemini function calling with multi-step tool execution.
- Kept Ollama as a local fallback so the assistant does not depend on cloud quota.
- Added generic business operations: prospect discovery, company research, qualification, lead saving and outreach drafting.
- Added a new original holographic center avatar HUD with transcript/audio-aware mouth animation.
- Added Gemini neural TTS support with `Charon` as the default voice and configurable alternatives.
- Added real settings persistence, including assistant name, AI provider, model and voice.
- API keys are stored only in `config/local_secrets.json` or `GEMINI_API_KEY`, never in tracked settings.
- Removed the fixed Nagpur business workflow.

## Gemini quota reality

Gemini Free Tier is **not unlimited**. Keep `AI mode = Hybrid` so Gemini is the smart cloud layer while Ollama provides a local fallback when cloud usage is unavailable.

## Merge

Copy the files in this overlay into the matching paths in your existing repository and install the updated `requirements.txt`.
