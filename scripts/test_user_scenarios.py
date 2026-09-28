"""Test all 6 user-specified scenarios to verify natural fast conversation vs agent workflow."""
import asyncio
import os
import sys
import time

try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.agent.conversation import conversation_manager
from backend.memory.database import init_db

async def test_scenarios():
    print("==================================================")
    print("TESTING 6 CRITICAL USER SCENARIOS")
    print("==================================================")
    await init_db()

    scenarios = [
        ("1. Hi Sia", "Hi Sia", False),
        ("2. Kya kar rahi ho?", "Kya kar rahi ho?", False),
        ("3. Aaj kya kar sakti ho?", "Aaj kya kar sakti ho?", False),
        ("4. Mere DineMotion ke baare me kya yaad hai?", "Mere DineMotion ke baare me kya yaad hai?", False),
        ("5. Mere liye ek funny joke suna.", "Mere liye ek funny joke suna.", False),
        ("6. Nagpur ke restaurants find karo jinki websites outdated hain.", "Nagpur ke restaurants find karo jinki websites outdated hain.", True),
    ]

    for label, query, should_be_tool in scenarios:
        states_observed = []
        tokens_streamed = []

        async def on_state(state, details=None):
            states_observed.append(state)

        async def on_token(token):
            tokens_streamed.append(token)

        start = time.perf_counter()
        res = await conversation_manager.process_user_input(
            query,
            generate_audio=False,
            stream_callback=on_token,
            state_callback=on_state
        )
        duration = time.perf_counter() - start

        tool_result = res.get("tool_result")
        has_tool = tool_result is not None
        response_text = res.get("response_text", "")
        final_state = res.get("state")

        print(f"\n--- {label} ---")
        print(f"Query: '{query}'")
        print(f"Time: {duration:.2f}s")
        print(f"States observed: {states_observed}")
        print(f"Final state: {final_state}")
        print(f"Tokens streamed count: {len(tokens_streamed)}")
        print(f"Tool executed: {has_tool} (Expected: {should_be_tool})")
        print(f"Response: {response_text[:120]}...")

        # Assertions
        if not should_be_tool:
            assert "thinking" not in states_observed, f"Thinking state should NOT be triggered for {label}!"
            assert "Sir" in response_text or "Sagar" in response_text or len(response_text) > 10, f"Natural response expected for {label}"
            print(f"  -> PASS: Fast conversational path executed cleanly!")
        else:
            assert "thinking" in states_observed or has_tool, f"Tool/Agent state expected for {label}!"
            assert has_tool, f"Tool result expected for {label}!"
            print(f"  -> PASS: Real Agent/Tool workflow executed cleanly!")

    print("\n==================================================")
    print("ALL 6 SCENARIOS TESTED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_scenarios())
