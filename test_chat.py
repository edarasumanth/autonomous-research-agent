"""Quick test of the chat research interface."""

import asyncio
import sys
import io

# Fix Windows console encoding for Unicode/emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from chat_research_agent import quick_research_chat

async def main():
    print("=" * 60)
    print("TESTING CHAT RESEARCH INTERFACE")
    print("=" * 60)
    print("\nTopic: Prompt Engineering Techniques")
    print("Depth: quick")
    print("\n" + "-" * 60)
    print("STARTING RESEARCH...")
    print("-" * 60 + "\n")

    def on_message(chunk):
        # Replace emojis with text equivalents for Windows console
        chunk = chunk.replace("🔍", "[SEARCH]")
        chunk = chunk.replace("📥", "[DOWNLOAD]")
        chunk = chunk.replace("📖", "[READ]")
        chunk = chunk.replace("📝", "[NOTE]")
        chunk = chunk.replace("📄", "[REPORT]")
        chunk = chunk.replace("❌", "[ERROR]")
        print(chunk, end="", flush=True)

    result = await quick_research_chat(
        topic="Prompt Engineering Techniques for LLMs",
        depth="quick",
        on_message=on_message
    )

    print("\n\n" + "=" * 60)
    print("RESEARCH COMPLETE")
    print("=" * 60)
    print(f"\nSession folder: {result['session_dir']}")
    print(f"\nStats:")
    print(f"  - Searches: {result['stats']['searches']}")
    print(f"  - Downloads: {result['stats']['downloads']}")
    print(f"  - PDFs Read: {result['stats']['reads']}")
    print(f"  - Notes: {result['stats']['notes']}")
    print(f"  - Report Generated: {result['stats']['report']}")

if __name__ == "__main__":
    asyncio.run(main())
