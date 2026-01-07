"""
Chat-Based Research Agent

Conversational research agent that maintains context across interactions.
Supports both research initiation and follow-up Q&A about completed research.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncGenerator, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from web_research_agent import get_session_pdfs, get_session_report
from web_research_tools import ResearchConfig, web_research_tools_server

# =============================================================================
# Chat System Prompts
# =============================================================================

RESEARCH_CHAT_SYSTEM_PROMPT = """You are an intelligent research assistant with access to powerful research tools. You help users explore academic topics through conversation.

## Your Capabilities

You can:
1. **Conduct Research**: Search for papers, download PDFs, read and analyze them, take notes, and generate reports
2. **Answer Questions**: Help users understand research topics conversationally
3. **Clarify and Guide**: Ask clarifying questions to better understand what the user needs

## Available Tools

- **web_search**: Search for research papers and academic articles
- **download_pdfs**: Download PDF files from URLs
- **read_pdf**: Extract and read text from downloaded PDFs
- **save_note**: Save important findings and insights
- **read_notes**: Retrieve all saved notes
- **write_report**: Generate a comprehensive markdown report

## Interaction Style

- Be conversational and helpful
- When the user asks about a research topic, offer to search for relevant papers
- Explain your findings in accessible language
- Ask clarifying questions if the request is ambiguous
- Summarize key points from papers you analyze
- When you've gathered enough information, offer to generate a formal report

## Research Workflow

When conducting research:
1. Start with web searches to find relevant papers
2. Download the most promising PDFs
3. Read and analyze the papers
4. Save key findings as notes
5. Synthesize and share insights with the user
6. Offer to generate a formal report when appropriate

Be proactive but not overwhelming. Share interesting findings as you discover them.
"""


FOLLOWUP_CHAT_SYSTEM_PROMPT = """You are a knowledgeable research assistant helping the user understand a completed research session.

## Context

The user has completed research on a specific topic. You have access to:
- The research report (provided below)
- The downloaded papers in the session
- The research notes taken during analysis

## Your Role

1. Answer questions about the research findings
2. Explain concepts from the papers in simpler terms
3. Draw connections between different papers
4. Provide additional context or clarification
5. Help the user understand the implications of the findings

## Guidelines

- Reference specific papers and findings when answering
- Be conversational and educational
- If asked about something not covered in the research, acknowledge the limitation
- Suggest follow-up research directions if relevant

## Research Report

{report_content}

## Papers Analyzed

{papers_list}
"""


# =============================================================================
# Chat Message Types
# =============================================================================


@dataclass
class ChatMessage:
    """A single chat message."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_name: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatSession:
    """A chat session with message history."""

    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    research_session_path: str | None = None
    mode: str = "research"  # "research" or "followup"
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# Streaming Chat Function
# =============================================================================


async def chat_with_agent(
    user_message: str,
    chat_history: list[dict],
    mode: str = "research",
    research_session_path: str | None = None,
    on_tool_use: Callable[[str, dict], None] | None = None,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response from the agent.

    Args:
        user_message: The user's message
        chat_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        mode: "research" for new research, "followup" for Q&A about completed research
        research_session_path: Path to research session for followup mode
        on_tool_use: Callback when a tool is used
        model: Model to use (e.g., "claude-sonnet-4-20250514")

    Yields:
        Chunks of the assistant's response
    """
    # Build system prompt based on mode
    if mode == "followup" and research_session_path:
        report = get_session_report(research_session_path) or "No report available."
        pdfs = get_session_pdfs(research_session_path)
        papers_list = "\n".join(f"- {pdf}" for pdf in pdfs) if pdfs else "No papers downloaded."

        system_prompt = FOLLOWUP_CHAT_SYSTEM_PROMPT.format(
            report_content=report[:10000],  # Limit to avoid context overflow
            papers_list=papers_list,
        )

        # In followup mode, we don't need research tools
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            permission_mode="bypassPermissions",
            model=model,
        )
    else:
        # Research mode with tools
        if research_session_path:
            ResearchConfig.set_output_dir(research_session_path)
        else:
            # Create new session folder
            ResearchConfig.create_session_folder("chat_research", "research_sessions")

        options = ClaudeAgentOptions(
            system_prompt=RESEARCH_CHAT_SYSTEM_PROMPT,
            mcp_servers={"research": web_research_tools_server},
            permission_mode="bypassPermissions",
            max_turns=50,
            max_budget_usd=3.0,
            model=model,
        )

    # Build conversation for the API
    # Format: alternating user/assistant messages
    conversation_prompt = ""
    for msg in chat_history[-10:]:  # Keep last 10 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            conversation_prompt += f"\n\nUser: {content}"
        elif role == "assistant":
            conversation_prompt += f"\n\nAssistant: {content}"

    conversation_prompt += f"\n\nUser: {user_message}\n\nAssistant:"

    # Stream the response
    try:
        async with ClaudeSDKClient(options) as client:
            await client.query(conversation_prompt.strip())

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            if block.text:
                                yield block.text

                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name
                            if tool_name.startswith("mcp__research__"):
                                tool_name = tool_name.replace("mcp__research__", "")

                            if on_tool_use:
                                on_tool_use(tool_name, block.input)

                            # Yield tool usage notification
                            if tool_name == "web_search":
                                query = block.input.get("query", "")[:50]
                                yield f"\n\n🔍 *Searching: {query}...*\n\n"
                            elif tool_name == "download_pdfs":
                                count = len(block.input.get("urls", []))
                                yield f"\n\n📥 *Downloading {count} PDFs...*\n\n"
                            elif tool_name == "read_pdf":
                                filename = block.input.get("filename", "")
                                yield f"\n\n📖 *Reading: {filename}*\n\n"
                            elif tool_name == "save_note":
                                title = block.input.get("title", "")[:40]
                                yield f"\n\n📝 *Saving note: {title}*\n\n"
                            elif tool_name == "write_report":
                                yield "\n\n📄 *Generating report...*\n\n"

                elif isinstance(message, ResultMessage):
                    # End of response
                    pass

    except Exception as e:
        import traceback

        error_tb = traceback.format_exc()
        yield f"\n\n❌ Error: {str(e)}\n\n```\n{error_tb}\n```"


# =============================================================================
# Synchronous Wrapper for Streamlit
# =============================================================================


def run_chat_sync(
    user_message: str,
    chat_history: list[dict],
    mode: str = "research",
    research_session_path: str | None = None,
) -> tuple[str, list[dict]]:
    """
    Synchronous wrapper for chat function.
    Returns (response_text, tool_uses)
    """
    tool_uses = []

    def on_tool(name, input_data):
        tool_uses.append({"name": name, "input": input_data})

    async def run():
        chunks = []
        async for chunk in chat_with_agent(
            user_message, chat_history, mode, research_session_path, on_tool
        ):
            chunks.append(chunk)
        return "".join(chunks)

    response = asyncio.run(run())
    return response, tool_uses


# =============================================================================
# Quick Research via Chat
# =============================================================================


async def quick_research_chat(
    topic: str,
    depth: str = "quick",
    on_message: Callable[[str], None] | None = None,
) -> dict:
    """
    Conduct quick research via chat interface.

    Args:
        topic: Research topic
        depth: "quick", "standard", or "deep"
        on_message: Callback for streaming messages

    Returns:
        dict with session_dir and results
    """
    # Create session
    session_dir = ResearchConfig.create_session_folder(topic, "research_sessions")

    # Save metadata
    metadata = {
        "topic": topic,
        "depth": depth,
        "mode": "chat",
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(session_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    depth_instructions = {
        "quick": "Do a quick search, find 2-3 key papers, and summarize the main points.",
        "standard": "Conduct thorough research with 5-7 papers and provide comprehensive analysis.",
        "deep": "Do exhaustive research with 10+ papers, detailed analysis, and generate a formal report.",
    }

    prompt = f"""Please research the following topic: {topic}

{depth_instructions.get(depth, depth_instructions["standard"])}

Start by searching for relevant papers, then download and analyze them. Share your findings as you go, and generate a report at the end."""

    response_text = ""
    tool_count = {"searches": 0, "downloads": 0, "reads": 0, "notes": 0, "report": False}

    def on_tool(name, input_data):
        if name == "web_search":
            tool_count["searches"] += 1
        elif name == "download_pdfs":
            tool_count["downloads"] += len(input_data.get("urls", []))
        elif name == "read_pdf":
            tool_count["reads"] += 1
        elif name == "save_note":
            tool_count["notes"] += 1
        elif name == "write_report":
            tool_count["report"] = True

    async for chunk in chat_with_agent(
        prompt,
        [],
        mode="research",
        research_session_path=session_dir,
        on_tool_use=on_tool,
    ):
        response_text += chunk
        if on_message:
            on_message(chunk)

    # Save completion data
    completion = {
        "completed_at": datetime.now().isoformat(),
        "stats": tool_count,
    }
    with open(os.path.join(session_dir, "completion.json"), "w") as f:
        json.dump(completion, f, indent=2)

    return {
        "session_dir": session_dir,
        "response": response_text,
        "stats": tool_count,
    }
