"""Test Claude SDK directly to diagnose the error."""

import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient


async def test_sdk():
    print("Testing Claude SDK connection...")
    print(f"Python: {sys.executable}")
    print(f"PATH: {os.environ.get('PATH', 'NOT SET')[:200]}...")
    print()

    try:
        options = ClaudeAgentOptions(
            system_prompt="You are a helpful assistant.",
            permission_mode="bypassPermissions",
            max_turns=1,
        )

        print("Creating ClaudeSDKClient...")
        async with ClaudeSDKClient(options) as client:
            print("Client created successfully!")
            print("Sending test query...")
            await client.query("Say hello in exactly 3 words.")

            async for message in client.receive_response():
                print(f"Response: {message}")
                break

        print("\nSUCCESS: SDK is working!")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_sdk())
