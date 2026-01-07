"""
Research Agent using Claude Agent SDK

Demonstrates two approaches:
1. Stateless query() - One-off research queries with no memory
2. ClaudeSDKClient - Multi-turn conversational research with memory

Plus integrated tools:
- Web Search (Tavily API) - Search for research papers, PDFs, and articles
- PDF Downloader - Download PDFs to local 'papers' folder

Usage:
    python research_agent.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from tools import list_downloaded_pdfs, research_tools_server

# =============================================================================
# APPROACH 1: Stateless Research (query) - No memory between calls
# =============================================================================


async def stateless_research_query(prompt: str, system_prompt: str = None) -> str:
    """
    Execute a single research query using the stateless query() approach.
    Each call starts fresh with no memory of previous interactions.

    Args:
        prompt: The research question to ask
        system_prompt: Optional custom system prompt for the agent

    Returns:
        The agent's response text
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=[],  # No tools needed for pure research queries
    )

    response_text = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text.append(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n--- Query completed in {message.duration_ms}ms ---")
            if message.total_cost_usd:
                print(f"--- Cost: ${message.total_cost_usd:.4f} ---")

    return "".join(response_text)


# =============================================================================
# APPROACH 2: Conversational Research (ClaudeSDKClient) - Memory across turns
# =============================================================================


class ConversationalResearchAgent:
    """
    A research agent that maintains conversation context across multiple exchanges.
    Claude remembers all previous messages in the session, enabling natural follow-ups.
    """

    def __init__(self, system_prompt: str = None):
        self.options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=[],  # Pure research, no tools
        )
        self.client = None
        self.turn_count = 0

    async def __aenter__(self):
        """Start the conversation session."""
        self.client = ClaudeSDKClient(self.options)
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End the conversation session."""
        if self.client:
            await self.client.disconnect()

    async def ask(self, question: str) -> str:
        """
        Ask a question in the ongoing conversation.
        Claude remembers all previous exchanges in this session.

        Args:
            question: The question to ask

        Returns:
            Claude's response
        """
        self.turn_count += 1
        await self.client.query(question)

        response_text = []
        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text.append(block.text)
            elif isinstance(message, ResultMessage):
                print(f"\n--- Turn {self.turn_count} completed in {message.duration_ms}ms ---")
                if message.total_cost_usd:
                    print(f"--- Cost: ${message.total_cost_usd:.4f} ---")

        return "".join(response_text)


# =============================================================================
# EXAMPLE 1: Stateless Research Session (No Memory)
# =============================================================================


async def run_stateless_example():
    """Demonstrate stateless queries - each query is independent."""

    health_research_prompt = """You are a health research assistant specializing in
nutrition and human physiology. Provide accurate, scientifically-backed information
in a clear and accessible manner. When discussing health topics:

1. Cite general scientific consensus where applicable
2. Use clear explanations suitable for a general audience
3. Note any important caveats or individual variations
4. Avoid giving specific medical advice - recommend consulting professionals when appropriate
"""

    print("=" * 60)
    print("STATELESS RESEARCH - Each Query is Independent")
    print("=" * 60)
    print()

    # Query 1
    print("QUERY 1: How does our body digest protein?")
    print("-" * 40)
    response = await stateless_research_query(
        prompt="Explain how the human body digests protein in 2-3 paragraphs.",
        system_prompt=health_research_prompt,
    )
    print(response)
    print()

    # Query 2 - Has NO memory of Query 1
    print("QUERY 2: What about the stomach specifically?")
    print("-" * 40)
    print("(Note: This query has NO context from Query 1)")
    response = await stateless_research_query(
        prompt="What happens in the stomach?",  # Vague without context
        system_prompt=health_research_prompt,
    )
    print(response)
    print()


# =============================================================================
# EXAMPLE 2: Conversational Research Session (With Memory)
# =============================================================================


async def run_conversational_example():
    """Demonstrate conversational research - Claude remembers context."""

    health_research_prompt = """You are a health research assistant specializing in
nutrition and human physiology. Provide accurate, scientifically-backed information.
Keep responses concise but informative. When discussing health topics, note important
caveats and recommend consulting professionals when appropriate."""

    print("=" * 60)
    print("CONVERSATIONAL RESEARCH - Claude Remembers Context")
    print("=" * 60)
    print()

    async with ConversationalResearchAgent(health_research_prompt) as agent:
        # Turn 1: Initial question
        print("TURN 1: Starting our research topic")
        print("-" * 40)
        response = await agent.ask(
            "I'd like to learn about protein digestion. "
            "Can you give me a brief overview of the process?"
        )
        print(response)
        print()

        # Turn 2: Follow-up - Claude remembers we're discussing protein digestion
        print("TURN 2: Follow-up question (Claude remembers context)")
        print("-" * 40)
        response = await agent.ask("What happens specifically in the stomach?")
        print(response)
        print()

        # Turn 3: Deeper dive - Claude still has full context
        print("TURN 3: Going deeper (still has full context)")
        print("-" * 40)
        response = await agent.ask(
            "You mentioned pepsin. How does it actually break down the proteins?"
        )
        print(response)
        print()

        # Turn 4: Comparative question - references previous discussion
        print("TURN 4: Comparative question")
        print("-" * 40)
        response = await agent.ask(
            "How does this compare to how the small intestine processes proteins?"
        )
        print(response)
        print()

        # Turn 5: Summary request - Claude can summarize entire conversation
        print("TURN 5: Summary of our conversation")
        print("-" * 40)
        response = await agent.ask(
            "Can you summarize the key points we've discussed about protein digestion?"
        )
        print(response)


# =============================================================================
# EXAMPLE 3: Interactive Research Session
# =============================================================================


async def run_interactive_example():
    """
    Run an interactive research session where the user can ask questions.
    Type 'quit' to exit the session.
    """

    research_prompt = """You are a knowledgeable research assistant. Provide accurate,
well-reasoned responses. When uncertain, acknowledge limitations. Keep responses
focused and conversational."""

    print("=" * 60)
    print("INTERACTIVE RESEARCH SESSION")
    print("Type your questions. Type 'quit' to exit.")
    print("=" * 60)
    print()

    async with ConversationalResearchAgent(research_prompt) as agent:
        while True:
            try:
                user_input = input(f"\n[Turn {agent.turn_count + 1}] You: ").strip()

                if user_input.lower() in ("quit", "exit", "q"):
                    print(f"\nSession ended after {agent.turn_count} turns.")
                    break

                if not user_input:
                    continue

                print(f"\n[Turn {agent.turn_count + 1}] Assistant:")
                print("-" * 40)
                response = await agent.ask(user_input)
                print(response)

            except KeyboardInterrupt:
                print(f"\n\nSession interrupted after {agent.turn_count} turns.")
                break


# =============================================================================
# EXAMPLE 4: Guided Analysis Session
# =============================================================================


async def run_guided_analysis():
    """
    Demonstrate a guided multi-turn analysis where we progressively
    explore a topic with follow-up questions based on responses.
    """

    analysis_prompt = """You are an analytical research assistant skilled at
breaking down complex topics. Provide structured, evidence-based analysis.
Be concise but thorough."""

    print("=" * 60)
    print("GUIDED ANALYSIS - Progressive Topic Exploration")
    print("=" * 60)
    print()

    async with ConversationalResearchAgent(analysis_prompt) as agent:
        # Phase 1: Introduction
        print("PHASE 1: Topic Introduction")
        print("-" * 40)
        response = await agent.ask(
            "I want to analyze the impact of sleep on cognitive performance. "
            "What are the main areas we should explore?"
        )
        print(response)
        print()

        # Phase 2: Deep dive into first aspect
        print("PHASE 2: Memory Consolidation Deep Dive")
        print("-" * 40)
        response = await agent.ask(
            "Let's focus on memory consolidation first. "
            "How does sleep affect different types of memory?"
        )
        print(response)
        print()

        # Phase 3: Practical implications
        print("PHASE 3: Practical Implications")
        print("-" * 40)
        response = await agent.ask(
            "Based on what we've discussed, what are the practical implications "
            "for someone trying to learn a new skill?"
        )
        print(response)
        print()

        # Phase 4: Counter-arguments
        print("PHASE 4: Examining Limitations")
        print("-" * 40)
        response = await agent.ask(
            "What are some limitations or counter-arguments to the points we've covered?"
        )
        print(response)
        print()

        # Phase 5: Synthesis
        print("PHASE 5: Final Synthesis")
        print("-" * 40)
        response = await agent.ask(
            "Please synthesize our discussion into 3-4 key takeaways about "
            "sleep and cognitive performance."
        )
        print(response)


# =============================================================================
# EXAMPLE 5: Web Search and PDF Download (MCP Server Integration)
# =============================================================================


async def run_web_search_example():
    """
    Demonstrate the web search and PDF download tools using MCP server integration.
    Claude uses tools autonomously to search for papers and download PDFs.
    """
    print("=" * 60)
    print("WEB SEARCH & PDF DOWNLOAD EXAMPLE")
    print("Using Claude Agent SDK with MCP tools")
    print("=" * 60)
    print()

    # Check for Tavily API key
    if not os.getenv("TAVILY_API_KEY"):
        print("WARNING: TAVILY_API_KEY environment variable not set.")
        print("Get a free API key at https://app.tavily.com")
        print("Set it with: export TAVILY_API_KEY=your-key-here")
        print()
        return

    user_query = input("Enter a research topic to search for: ").strip()
    if not user_query:
        user_query = "transformer architecture deep learning"
        print(f"Using default query: {user_query}")

    # Create streaming prompt (required for MCP tools)
    async def streaming_prompt():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": f"Search for research papers about: {user_query}\n\n"
                f"After finding results, download any PDF files to the 'papers' folder.",
            },
            "parent_tool_use_id": None,
            "session_id": "default",
        }

    options = ClaudeAgentOptions(
        system_prompt="""You are a research assistant with access to web search and PDF download tools.

When the user asks about a research topic:
1. Use the web_search tool to find relevant research papers and articles
2. Present the search results clearly with titles and URLs
3. Identify any PDF URLs from the results
4. Use the download_pdfs tool to download the PDFs to the local 'papers' folder

Be helpful and provide summaries of what you find.""",
        mcp_servers={"research": research_tools_server},
        permission_mode="bypassPermissions",
    )

    print()
    print("-" * 40)
    print("Claude is searching and processing...")
    print("-" * 40)
    print()

    async for message in query(prompt=streaming_prompt(), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"\n[Using tool: {block.name}]")
                elif isinstance(block, ToolResultBlock):
                    print("[Tool completed]")

        elif isinstance(message, ResultMessage):
            print()
            print(f"--- Completed in {message.duration_ms}ms ---")
            if message.total_cost_usd:
                print(f"--- Cost: ${message.total_cost_usd:.4f} ---")

    # Show downloaded files
    pdfs = list_downloaded_pdfs()
    if pdfs:
        print()
        print("-" * 40)
        print(f"PDFs in 'papers' folder ({len(pdfs)} files):")
        for pdf in pdfs[:10]:
            print(f"  - {pdf}")
        if len(pdfs) > 10:
            print(f"  ... and {len(pdfs) - 10} more")


async def run_interactive_search():
    """
    Interactive research session with web search capabilities using MCP server.
    Claude handles the search and download autonomously.
    """
    print("=" * 60)
    print("INTERACTIVE RESEARCH SESSION WITH WEB SEARCH")
    print("Chat naturally with Claude about research topics!")
    print("Type 'quit' to exit, 'list' to see downloaded PDFs")
    print("=" * 60)
    print()

    # Check for Tavily API key
    if not os.getenv("TAVILY_API_KEY"):
        print("WARNING: TAVILY_API_KEY environment variable not set.")
        print("Get a free API key at https://app.tavily.com")
        print()
        return

    options = ClaudeAgentOptions(
        system_prompt="""You are a research assistant with access to these tools:

1. web_search: Search for research papers, articles, and PDFs on any topic
2. download_pdfs: Download PDF files from URLs to the local 'papers' folder

Help the user find and download research papers. When they ask about a topic,
search for relevant papers and offer to download any PDFs found.

Be conversational and helpful. Summarize search results clearly.""",
        mcp_servers={"research": research_tools_server},
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options) as client:
        turn_count = 0

        while True:
            try:
                user_input = input(f"\n[Turn {turn_count + 1}] You: ").strip()

                if user_input.lower() in ("quit", "exit", "q"):
                    print(f"\nSession ended after {turn_count} turns.")
                    break

                if user_input.lower() == "list":
                    pdfs = list_downloaded_pdfs()
                    if pdfs:
                        print(f"\nDownloaded PDFs ({len(pdfs)} files):")
                        for pdf in pdfs:
                            print(f"  - {pdf}")
                    else:
                        print("\nNo PDFs downloaded yet.")
                    continue

                if not user_input:
                    continue

                turn_count += 1
                await client.query(user_input)

                print(f"\n[Turn {turn_count}] Assistant:")
                print("-" * 40)

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                print(block.text)
                            elif isinstance(block, ToolUseBlock):
                                print(f"\n[Using tool: {block.name}]")
                            elif isinstance(block, ToolResultBlock):
                                print("[Tool completed]")

                    elif isinstance(message, ResultMessage):
                        print(f"\n--- Turn {turn_count} completed in {message.duration_ms}ms ---")

            except KeyboardInterrupt:
                print(f"\n\nSession interrupted after {turn_count} turns.")
                break


# =============================================================================
# Main Entry Point
# =============================================================================


async def main():
    """Run the research agent examples."""

    print("\n" + "=" * 60)
    print("RESEARCH AGENT DEMONSTRATION")
    print("Stateless vs Conversational Approaches + Web Tools")
    print("=" * 60 + "\n")

    # Menu for selecting which example to run
    print("Select an example to run:")
    print("1. Stateless Research (no memory between queries)")
    print("2. Conversational Research (memory across turns)")
    print("3. Interactive Research Session (chat with the agent)")
    print("4. Guided Analysis (progressive topic exploration)")
    print("5. Web Search & PDF Download (search papers, download PDFs)")
    print("6. Interactive Search Session (chat with web search tools)")
    print("7. Run examples 1 and 2 (comparison)")
    print()

    choice = input("Enter choice (1-7): ").strip()

    if choice == "1":
        await run_stateless_example()
    elif choice == "2":
        await run_conversational_example()
    elif choice == "3":
        await run_interactive_example()
    elif choice == "4":
        await run_guided_analysis()
    elif choice == "5":
        await run_web_search_example()
    elif choice == "6":
        await run_interactive_search()
    elif choice == "7":
        await run_stateless_example()
        print("\n" + "=" * 60 + "\n")
        await run_conversational_example()
    else:
        print("Invalid choice. Running conversational example by default.")
        await run_conversational_example()

    print("\n" + "=" * 60)
    print("Research session complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
