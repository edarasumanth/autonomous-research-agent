"""
Autonomous Research Agent

A fully autonomous research agent that works independently towards research goals
without asking questions. The user provides comprehensive input upfront, and the
agent executes the research workflow autonomously.

Usage:
    python autonomous_agent.py
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from autonomous_tools import autonomous_tools_server

# =============================================================================
# Research Request Data Structure
# =============================================================================


@dataclass
class ResearchRequest:
    """Structured input for autonomous research agent."""

    # Core research specification
    topic: str  # Main research question/topic
    background: str  # Context and background information

    # Scope constraints
    depth: Literal["quick", "standard", "deep"] = "standard"  # Research depth
    max_papers: int = 10  # Maximum papers to download
    time_period: str | None = None  # e.g., "2020-2024"
    domains: list[str] = field(default_factory=list)  # Focus domains

    # Completion criteria (optional - agent infers if not provided)
    completion_criteria: str | None = None

    # Safety limits
    max_searches: int = 20  # Maximum web searches


# =============================================================================
# System Prompt for Autonomous Operation
# =============================================================================

AUTONOMOUS_SYSTEM_PROMPT = """You are an autonomous research agent. You will receive a comprehensive research request and must complete it WITHOUT asking any clarifying questions. Work independently using your available tools until the research objective is achieved.

## CRITICAL OPERATING PRINCIPLES

1. **NO QUESTIONS**: Never ask the user for clarification. Make reasonable assumptions based on the provided context. If something is ambiguous, choose the most logical interpretation and proceed.

2. **AUTONOMOUS EXECUTION**: Execute your research plan step-by-step without waiting for user input. Use tools proactively and iteratively until objectives are met.

3. **COMPREHENSIVE OUTPUT**: Your goal is to produce a complete research report at the end using the write_report tool.

## AVAILABLE TOOLS

- **web_search**: Search for research papers and academic articles. Use varied search terms for comprehensive coverage.
- **download_pdfs**: Download PDF files from URLs found in search results.
- **read_pdf**: Extract text content from downloaded PDFs to analyze their content.
- **save_note**: Save important findings, paper summaries, and insights as you research.
- **read_notes**: Retrieve all saved notes for synthesis before writing the report.
- **write_report**: Generate the final markdown research report.

## RESEARCH WORKFLOW

Execute these phases in order:

### Phase 1: Planning
- Parse the research request completely
- Identify 3-5 different search angles/terms to explore
- Consider: main topic, subtopics, related concepts, specific techniques

### Phase 2: Information Gathering
- Execute multiple web_search queries with varied search terms
- Try different phrasings if initial searches yield few results
- Identify papers and sources to download

### Phase 3: Content Acquisition
- Download relevant PDFs using download_pdfs
- Prioritize papers that appear most relevant to the research question

### Phase 4: Content Analysis
- Use read_pdf to extract content from each downloaded paper
- Use save_note to document:
  - "paper_summary" for each paper analyzed
  - "finding" for key facts and data
  - "insight" for connections and patterns you notice

### Phase 5: Synthesis & Reporting
- Use read_notes to gather all documented findings
- Synthesize the information into coherent conclusions
- Use write_report to generate the final comprehensive report

## COMPLETION CRITERIA

Research is complete when ALL of these conditions are met:
1. Multiple search angles have been explored (at least 3 different queries)
2. Relevant papers have been downloaded and analyzed (aim for 3-5 minimum)
3. Key findings have been documented using save_note
4. A final report has been generated using write_report

## ERROR HANDLING

- If a search returns no results: Try alternative search terms
- If a PDF fails to download: Note it and continue with other sources
- If a PDF cannot be read: Skip it and continue with others
- If running low on search budget: Focus on highest-priority aspects

## IMPORTANT GUIDELINES

- Be thorough but efficient - don't repeat searches unnecessarily
- Document findings as you go using save_note (don't wait until the end)
- The write_report tool MUST be called at the end to produce the final output
- Include proper citations/references in your report
"""


# =============================================================================
# Request Formatting
# =============================================================================


def format_research_request(request: ResearchRequest) -> str:
    """Format the research request as a prompt for the agent."""

    domains_str = ", ".join(request.domains) if request.domains else "All relevant academic domains"
    time_str = request.time_period if request.time_period else "Any time period"
    criteria_str = (
        request.completion_criteria
        if request.completion_criteria
        else "Agent determines completion based on standard criteria"
    )

    depth_descriptions = {
        "quick": "Quick overview - find 2-3 key papers and summarize main points",
        "standard": "Standard depth - find 5-7 papers, analyze thoroughly, provide comprehensive synthesis",
        "deep": "Deep analysis - exhaustive search, 10+ papers, detailed analysis of methodology and findings",
    }

    return f"""## Research Request

**Topic**: {request.topic}

**Background Context**:
{request.background}

**Research Parameters**:
- Depth: {request.depth} ({depth_descriptions[request.depth]})
- Maximum Papers to Analyze: {request.max_papers}
- Time Period: {time_str}
- Focus Domains: {domains_str}

**Completion Criteria**:
{criteria_str}

**Resource Limits**:
- Maximum Web Searches: {request.max_searches}

---

Begin your autonomous research now. Execute your plan completely without asking questions. Use your tools proactively and produce a final comprehensive report when done.
"""


# =============================================================================
# Main Execution Function
# =============================================================================


async def run_autonomous_research(request: ResearchRequest) -> dict:
    """
    Execute fully autonomous research workflow.

    Args:
        request: ResearchRequest with all research parameters

    Returns:
        dict with report_path, duration, cost, and statistics
    """
    print("\n" + "=" * 70)
    print("AUTONOMOUS RESEARCH AGENT")
    print("=" * 70)
    print(f"\nTopic: {request.topic}")
    print(f"Depth: {request.depth}")
    print(f"Max Papers: {request.max_papers}")
    print(f"Max Searches: {request.max_searches}")
    print("\n" + "-" * 70)
    print("Agent is now working autonomously. Please wait...")
    print("-" * 70 + "\n")

    # Build prompts
    user_prompt = format_research_request(request)

    # Configure for autonomous operation
    options = ClaudeAgentOptions(
        system_prompt=AUTONOMOUS_SYSTEM_PROMPT,
        mcp_servers={"research": autonomous_tools_server},
        permission_mode="bypassPermissions",
        max_turns=100,  # Safety limit on conversation turns
        max_budget_usd=5.0,  # Cost safety limit
    )

    # Track statistics
    stats = {
        "tool_calls": [],
        "searches": 0,
        "downloads": 0,
        "pdfs_read": 0,
        "notes_saved": 0,
        "report_generated": False,
    }

    start_time = datetime.now()
    final_text = ""

    # Execute the autonomous research using ClaudeSDKClient
    async with ClaudeSDKClient(options) as client:
        await client.query(user_prompt)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Print agent's thoughts/text
                        if block.text.strip():
                            print(
                                f"\n[Agent]: {block.text[:200]}{'...' if len(block.text) > 200 else ''}"
                            )
                            final_text += block.text

                    elif isinstance(block, ToolUseBlock):
                        # Log tool usage - strip mcp prefix if present
                        tool_name = block.name
                        if tool_name.startswith("mcp__research__"):
                            tool_name = tool_name.replace("mcp__research__", "")
                        stats["tool_calls"].append(tool_name)

                        # Update specific counters
                        if tool_name == "web_search":
                            stats["searches"] += 1
                            query_text = block.input.get("query", "")[:50]
                            print(f'\n[Tool] web_search: "{query_text}..."')
                        elif tool_name == "download_pdfs":
                            urls = block.input.get("urls", [])
                            stats["downloads"] += len(urls)
                            print(f"\n[Tool] download_pdfs: {len(urls)} URLs")
                        elif tool_name == "read_pdf":
                            stats["pdfs_read"] += 1
                            filename = block.input.get("filename", "")
                            print(f"\n[Tool] read_pdf: {filename}")
                        elif tool_name == "save_note":
                            stats["notes_saved"] += 1
                            note_type = block.input.get("note_type", "")
                            title = block.input.get("title", "")[:40]
                            print(f"\n[Tool] save_note: [{note_type}] {title}")
                        elif tool_name == "read_notes":
                            print("\n[Tool] read_notes: Gathering all findings")
                        elif tool_name == "write_report":
                            stats["report_generated"] = True
                            title = block.input.get("title", "")[:50]
                            print(f"\n[Tool] write_report: {title}")
                        else:
                            print(f"\n[Tool] {tool_name}")

                    elif isinstance(block, ToolResultBlock):
                        # Tool results are processed internally
                        pass

            elif isinstance(message, ResultMessage):
                # Final result with metrics
                duration_sec = message.duration_ms / 1000
                cost = message.total_cost_usd

                end_time = datetime.now()
                total_time = (end_time - start_time).total_seconds()

                print("\n" + "=" * 70)
                print("RESEARCH COMPLETE")
                print("=" * 70)
                print(f"\nDuration: {total_time:.1f} seconds")
                print(f"API Time: {duration_sec:.1f} seconds")
                print(f"Cost: ${cost:.4f}" if cost else "Cost: N/A")
                print(f"Turns: {message.num_turns}")
                print("\nStatistics:")
                print(f"  - Web searches: {stats['searches']}")
                print(f"  - PDFs downloaded: {stats['downloads']}")
                print(f"  - PDFs analyzed: {stats['pdfs_read']}")
                print(f"  - Notes saved: {stats['notes_saved']}")
                print(f"  - Report generated: {'Yes' if stats['report_generated'] else 'No'}")

                return {
                    "duration_seconds": total_time,
                    "api_duration_seconds": duration_sec,
                    "cost_usd": cost,
                    "num_turns": message.num_turns,
                    "stats": stats,
                }

    return {"stats": stats}


# =============================================================================
# Interactive Input Collection
# =============================================================================


def collect_research_request() -> ResearchRequest:
    """Collect research parameters from user interactively."""

    print("\n" + "=" * 70)
    print("AUTONOMOUS RESEARCH AGENT - INPUT COLLECTION")
    print("=" * 70)
    print("\nProvide all research parameters upfront.")
    print("The agent will then work autonomously without further input.\n")

    # Topic
    print("-" * 40)
    topic = input("Research Topic:\n> ").strip()
    while not topic:
        print("Topic is required.")
        topic = input("Research Topic:\n> ").strip()

    # Background
    print("\n" + "-" * 40)
    print("Background Context (provide as much detail as possible):")
    print("(Enter a blank line when done)")
    background_lines = []
    while True:
        line = input()
        if line == "":
            if background_lines:
                break
            print("Please provide some background context:")
        else:
            background_lines.append(line)
    background = "\n".join(background_lines)

    # Depth
    print("\n" + "-" * 40)
    depth_input = (
        input("Research Depth [quick/standard/deep] (default: standard):\n> ").strip().lower()
    )
    depth = depth_input if depth_input in ["quick", "standard", "deep"] else "standard"

    # Max papers
    print("\n" + "-" * 40)
    papers_input = input("Maximum papers to analyze (default: 10):\n> ").strip()
    try:
        max_papers = int(papers_input) if papers_input else 10
    except ValueError:
        max_papers = 10

    # Time period
    print("\n" + "-" * 40)
    time_period = input("Time period (e.g., '2020-2024', leave blank for any):\n> ").strip() or None

    # Domains
    print("\n" + "-" * 40)
    domains_input = input("Focus domains (comma-separated, leave blank for all):\n> ").strip()
    domains = [d.strip() for d in domains_input.split(",") if d.strip()] if domains_input else []

    # Completion criteria
    print("\n" + "-" * 40)
    print("Custom completion criteria (optional, leave blank for default):")
    criteria = input("> ").strip() or None

    # Max searches
    print("\n" + "-" * 40)
    searches_input = input("Maximum web searches (default: 20):\n> ").strip()
    try:
        max_searches = int(searches_input) if searches_input else 20
    except ValueError:
        max_searches = 20

    return ResearchRequest(
        topic=topic,
        background=background,
        depth=depth,
        max_papers=max_papers,
        time_period=time_period,
        domains=domains,
        completion_criteria=criteria,
        max_searches=max_searches,
    )


# =============================================================================
# Example Requests
# =============================================================================


def get_example_request() -> ResearchRequest:
    """Return an example research request for testing."""
    return ResearchRequest(
        topic="Attention mechanisms in protein structure prediction",
        background="""
AlphaFold2 revolutionized protein structure prediction using transformer architectures
with attention mechanisms. I want to understand specifically how attention mechanisms
contribute to the model's ability to predict protein structures, including:

- Types of attention used (self-attention, cross-attention, axial attention, etc.)
- How attention patterns correlate with protein structural features
- Comparison with non-attention-based approaches (CNNs, RNNs)
- Recent improvements and variants building on AlphaFold2's approach
        """.strip(),
        depth="standard",
        max_papers=8,
        time_period="2020-2024",
        domains=["bioinformatics", "deep learning", "structural biology", "machine learning"],
        completion_criteria=None,
        max_searches=15,
    )


# =============================================================================
# Main Entry Point
# =============================================================================


async def main():
    """Main entry point with menu options."""

    print("\n" + "=" * 70)
    print("AUTONOMOUS RESEARCH AGENT")
    print("=" * 70)
    print("\nOptions:")
    print("  1. Enter research parameters interactively")
    print("  2. Run example research (protein structure prediction)")
    print("  3. Exit")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == "1":
        request = collect_research_request()
    elif choice == "2":
        request = get_example_request()
        print(f"\nUsing example request: {request.topic}")
    else:
        print("Exiting.")
        return

    # Confirm before starting
    print("\n" + "-" * 70)
    print("RESEARCH REQUEST SUMMARY")
    print("-" * 70)
    print(f"Topic: {request.topic}")
    print(f"Depth: {request.depth}")
    print(f"Max Papers: {request.max_papers}")
    print(f"Time Period: {request.time_period or 'Any'}")
    print(f"Domains: {', '.join(request.domains) if request.domains else 'All'}")
    print(f"Max Searches: {request.max_searches}")
    print("-" * 70)

    confirm = input("\nStart autonomous research? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return

    # Run the research
    await run_autonomous_research(request)

    print("\n" + "=" * 70)
    print("Done! Check the papers/ folder for:")
    print("  - Downloaded PDFs")
    print("  - Research notes (papers/notes/)")
    print("  - Final report (papers/research_report_*.md)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
