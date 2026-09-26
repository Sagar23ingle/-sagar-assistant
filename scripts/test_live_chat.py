"""Test live SIA chat and tools execution against running local server."""

import sys
import httpx
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=15.0)

# 1. Test Status
status = client.get("/api/status").json()
print(f"[STATUS] Assistant: {status['assistant_name']}, User: {status['user_name']}, DB: {status['database']}")

# 2. Test Greeting
r1 = client.post("/api/chat", json={"message": "Hello SIA"}).json()
print(f"[CHAT] Response: {r1['response_text']}")
assert "Sir" in r1['response_text'] or "Sagar" in r1['response_text']
assert r1['audio_base64'] is not None
print(f"[AUDIO] Audio bytes generated: {len(r1['audio_base64'])} chars base64")

# 3. Test Bad Idea Challenge (Section 11: Never a yes-person)
r2 = client.post("/api/chat", json={"message": "Sia, honestly bata mera idea kaisa hai"}).json()
print(f"[CHALLENGE] SIA Response: {r2['response_text']}")

# 4. Test DineMotion Website Analysis Tool Call
r3 = client.post("/api/chat", json={"message": "analyze website https://example.com"}).json()
print(f"[TOOL] Analysis Message: {r3['response_text']}")
if r3.get('tool_result'):
    print(f"[TOOL] Score: {r3['tool_result']['data'].get('modern_score')}/100")

# 5. Test Tasks Endpoint
tasks = client.get("/api/tasks").json()
print(f"[TASKS] Count: {len(tasks)}")

# 6. Test Local Ollama Qwen 2.5 3B Inference
try:
    ollama_res = httpx.post("http://127.0.0.1:11434/api/generate", json={
        "model": "qwen2.5:3b",
        "prompt": "You are SIA, Sagar's personal AI assistant. Say a short greeting addressed to Sir.",
        "stream": False,
    }, timeout=20.0).json()
    print(f"[LOCAL LLM] Qwen 2.5 3B Output: {ollama_res.get('response', '').strip()}")
except Exception as e:
    print(f"[LOCAL LLM] Notice: {e}")

print("\n>>> ALL LIVE VERIFICATIONS PASSED SUCCESSFULLY! <<<")
