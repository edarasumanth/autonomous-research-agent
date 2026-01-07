"""Test chat agent directly to diagnose the error."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_research_agent import chat_with_agent


async def test_chat():
    print("Testing chat agent...")
    print()

    try:
        response_text = ""
        async for chunk in chat_with_agent(
            user_message="Hello, can you hear me?",
            chat_history=[],
            mode="research",
            research_session_path=None,
        ):
            # Replace emojis for Windows console
            chunk = chunk.replace("\U0001f50d", "[SEARCH]")
            chunk = chunk.replace("\U0001f4e5", "[DOWNLOAD]")
            chunk = chunk.replace("\U0001f4d6", "[READ]")
            chunk = chunk.replace("\U0001f4dd", "[NOTE]")
            chunk = chunk.replace("\U0001f4c4", "[REPORT]")
            chunk = chunk.replace("\u274c", "[ERROR]")
            print(chunk, end="", flush=True)
            response_text += chunk

        print("\n\nSUCCESS: Chat agent responded!")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_chat())
