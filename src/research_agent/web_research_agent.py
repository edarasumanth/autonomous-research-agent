"""
Web Research Agent

Autonomous research agent for web interface with per-session folder support.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Callable, Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from web_research_tools import web_research_tools_server, ResearchConfig


# =============================================================================
# Research Request Data Structure
# =============================================================================

@dataclass
class ResearchRequest:
    """Structured input for autonomous research agent."""
    topic: str
    background: str
    depth: Literal["quick", "standard", "deep"] = "standard"
    max_papers: int = 10
    time_period: str | None = None
    domains: list[str] = field(default_factory=list)
    completion_criteria: str | None = None
    max_searches: int = 20
    model: str | None = None  # e.g., "claude-sonnet-4-20250514", "claude-opus-4-20250514"


@dataclass
class ResearchProgress:
    """Track research progress for UI updates."""
    status: str = "initializing"
    phase: str = ""
    searches: int = 0
    downloads: int = 0
    pdfs_read: int = 0
    notes_saved: int = 0
    report_generated: bool = False
    current_action: str = ""
    log_messages: list[str] = field(default_factory=list)
    error: str | None = None


# =============================================================================
# System Prompt
# =============================================================================

AUTONOMOUS_SYSTEM_PROMPT = """You are an autonomous research agent. Complete the research request WITHOUT asking any clarifying questions. Work independently using your available tools until the research objective is achieved.

## CRITICAL OPERATING PRINCIPLES

1. **NO QUESTIONS**: Never ask for clarification. Make reasonable assumptions and proceed.
2. **AUTONOMOUS EXECUTION**: Execute step-by-step without waiting for user input.
3. **COMPREHENSIVE OUTPUT**: Produce a complete research report using write_report tool.

## AVAILABLE TOOLS

- **web_search**: Search for research papers and academic articles
- **download_pdfs**: Download PDF files from URLs found in search results
- **read_pdf**: Extract text content from downloaded PDFs
- **save_note**: Save findings, paper summaries, and insights
- **read_notes**: Retrieve all saved notes for synthesis
- **write_report**: Generate the final markdown research report

## RESEARCH WORKFLOW

1. **Planning**: Identify 3-5 different search angles
2. **Information Gathering**: Execute multiple web_search queries
3. **Content Acquisition**: Download relevant PDFs
4. **Content Analysis**: Use read_pdf and save_note for each paper
5. **Synthesis & Reporting**: Use read_notes then write_report

## COMPLETION CRITERIA

- Multiple search angles explored (at least 3 queries)
- Relevant papers downloaded and analyzed (aim for 3-5 minimum)
- Key findings documented using save_note
- Final report generated using write_report

## ERROR HANDLING

- If search returns no results: Try alternative terms
- If PDF fails: Note it and continue with others
- The write_report tool MUST be called at the end
"""


def format_research_request(request: ResearchRequest) -> str:
    """Format the research request as a prompt."""
    domains_str = ", ".join(request.domains) if request.domains else "All relevant academic domains"
    time_str = request.time_period or "Any time period"
    criteria_str = request.completion_criteria or "Agent determines completion based on standard criteria"

    depth_descriptions = {
        "quick": "Quick overview - find 2-3 key papers and summarize main points",
        "standard": "Standard depth - find 5-7 papers, analyze thoroughly, provide comprehensive synthesis",
        "deep": "Deep analysis - exhaustive search, 10+ papers, detailed analysis",
    }

    return f"""## Research Request

**Topic**: {request.topic}

**Background Context**:
{request.background}

**Research Parameters**:
- Depth: {request.depth} ({depth_descriptions[request.depth]})
- Maximum Papers: {request.max_papers}
- Time Period: {time_str}
- Focus Domains: {domains_str}

**Completion Criteria**:
{criteria_str}

**Resource Limits**:
- Maximum Web Searches: {request.max_searches}

---

Begin autonomous research now. Execute completely without asking questions. Use tools proactively and produce a final comprehensive report.
"""


# =============================================================================
# Main Research Function
# =============================================================================

async def run_web_research(
    request: ResearchRequest,
    progress_callback: Callable[[ResearchProgress], None] | None = None,
    base_dir: str = "research_sessions"
) -> dict:
    """
    Execute autonomous research with progress callbacks for web UI.

    Args:
        request: Research request configuration
        progress_callback: Optional callback for progress updates
        base_dir: Base directory for research sessions

    Returns:
        dict with session_dir, report_path, duration, cost, and statistics
    """
    # Create session folder
    session_dir = ResearchConfig.create_session_folder(request.topic, base_dir)

    # Save request metadata
    metadata = {
        "topic": request.topic,
        "background": request.background,
        "depth": request.depth,
        "max_papers": request.max_papers,
        "time_period": request.time_period,
        "domains": request.domains,
        "model": request.model or "claude-sonnet-4-20250514",  # Default model
        "created_at": datetime.now().isoformat(),
    }
    with open(os.path.join(session_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Initialize progress
    progress = ResearchProgress(status="running", phase="Starting research...")

    def update_progress():
        if progress_callback:
            progress_callback(progress)

    def log(message: str):
        progress.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        update_progress()

    log(f"Created session folder: {session_dir}")
    log(f"Topic: {request.topic}")
    log(f"Depth: {request.depth}, Max papers: {request.max_papers}")

    # Build prompts
    user_prompt = format_research_request(request)

    # Configure for autonomous operation
    options = ClaudeAgentOptions(
        system_prompt=AUTONOMOUS_SYSTEM_PROMPT,
        mcp_servers={"research": web_research_tools_server},
        permission_mode="bypassPermissions",
        max_turns=100,
        max_budget_usd=5.0,
        model=request.model,  # Use specified model or SDK default
    )

    start_time = datetime.now()
    report_path = None

    try:
        async with ClaudeSDKClient(options) as client:
            await client.query(user_prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            if block.text.strip():
                                short_text = block.text[:100] + "..." if len(block.text) > 100 else block.text
                                log(f"Agent: {short_text}")

                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name
                            if tool_name.startswith("mcp__research__"):
                                tool_name = tool_name.replace("mcp__research__", "")

                            if tool_name == "web_search":
                                progress.searches += 1
                                query = block.input.get("query", "")[:50]
                                progress.current_action = f"Searching: {query}..."
                                log(f"🔍 Web search: \"{query}...\"")

                            elif tool_name == "download_pdfs":
                                urls = block.input.get("urls", [])
                                progress.downloads += len(urls)
                                progress.current_action = f"Downloading {len(urls)} PDFs..."
                                log(f"📥 Downloading {len(urls)} PDFs")

                            elif tool_name == "read_pdf":
                                progress.pdfs_read += 1
                                filename = block.input.get("filename", "")
                                progress.current_action = f"Reading: {filename}"
                                log(f"📖 Reading PDF: {filename}")

                            elif tool_name == "save_note":
                                progress.notes_saved += 1
                                note_type = block.input.get("note_type", "")
                                title = block.input.get("title", "")[:40]
                                progress.current_action = f"Saving note: {title}"
                                log(f"📝 Note [{note_type}]: {title}")

                            elif tool_name == "read_notes":
                                progress.current_action = "Gathering all findings..."
                                log("📚 Reading all notes for synthesis")

                            elif tool_name == "write_report":
                                progress.report_generated = True
                                progress.current_action = "Generating final report..."
                                log("📄 Generating final report")
                                report_path = os.path.join(session_dir, "report.md")

                            update_progress()

                elif isinstance(message, ResultMessage):
                    duration_sec = message.duration_ms / 1000
                    cost = message.total_cost_usd

                    end_time = datetime.now()
                    total_time = (end_time - start_time).total_seconds()

                    progress.status = "completed"
                    progress.phase = "Research complete!"
                    progress.current_action = ""

                    log(f"✅ Research completed in {total_time:.1f}s")
                    log(f"💰 Cost: ${cost:.4f}" if cost else "💰 Cost: N/A")

                    # Save completion metadata
                    completion_data = {
                        "completed_at": datetime.now().isoformat(),
                        "duration_seconds": total_time,
                        "api_duration_seconds": duration_sec,
                        "cost_usd": cost,
                        "num_turns": message.num_turns,
                        "stats": {
                            "searches": progress.searches,
                            "downloads": progress.downloads,
                            "pdfs_read": progress.pdfs_read,
                            "notes_saved": progress.notes_saved,
                            "report_generated": progress.report_generated,
                        }
                    }
                    with open(os.path.join(session_dir, "completion.json"), "w") as f:
                        json.dump(completion_data, f, indent=2)

                    update_progress()

                    return {
                        "session_dir": session_dir,
                        "report_path": report_path,
                        "duration_seconds": total_time,
                        "api_duration_seconds": duration_sec,
                        "cost_usd": cost,
                        "num_turns": message.num_turns,
                        "stats": {
                            "searches": progress.searches,
                            "downloads": progress.downloads,
                            "pdfs_read": progress.pdfs_read,
                            "notes_saved": progress.notes_saved,
                            "report_generated": progress.report_generated,
                        }
                    }

    except Exception as e:
        progress.status = "error"
        progress.error = str(e)
        log(f"❌ Error: {str(e)}")
        update_progress()

        return {
            "session_dir": session_dir,
            "error": str(e),
            "stats": {
                "searches": progress.searches,
                "downloads": progress.downloads,
                "pdfs_read": progress.pdfs_read,
                "notes_saved": progress.notes_saved,
                "report_generated": progress.report_generated,
            }
        }

    return {"session_dir": session_dir, "stats": {}}


# =============================================================================
# Session Management Utilities
# =============================================================================

def list_research_sessions(base_dir: str = "research_sessions") -> list[dict]:
    """List all research sessions with metadata."""
    sessions = []

    if not os.path.exists(base_dir):
        return sessions

    for folder in sorted(os.listdir(base_dir), reverse=True):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        session = {
            "folder": folder,
            "path": folder_path,
            "topic": folder.split("_", 2)[-1] if "_" in folder else folder,
        }

        # Load metadata if exists
        metadata_path = os.path.join(folder_path, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                session["metadata"] = json.load(f)

        # Load completion data if exists
        completion_path = os.path.join(folder_path, "completion.json")
        if os.path.exists(completion_path):
            with open(completion_path, "r", encoding="utf-8") as f:
                session["completion"] = json.load(f)

        # Check for report
        session["has_report"] = os.path.exists(os.path.join(folder_path, "report.md"))

        # List PDFs
        pdfs_dir = os.path.join(folder_path, "pdfs")
        if os.path.exists(pdfs_dir):
            session["pdfs"] = [f for f in os.listdir(pdfs_dir) if f.endswith(".pdf")]
        else:
            session["pdfs"] = []

        sessions.append(session)

    return sessions


def get_session_report(session_path: str) -> str | None:
    """Get the report content for a session."""
    report_path = os.path.join(session_path, "report.md")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def get_session_pdfs(session_path: str) -> list[str]:
    """Get list of PDFs in a session."""
    pdfs_dir = os.path.join(session_path, "pdfs")
    if os.path.exists(pdfs_dir):
        return [f for f in os.listdir(pdfs_dir) if f.endswith(".pdf")]
    return []


def get_pdf_path(session_path: str, filename: str) -> str | None:
    """Get full path to a PDF file."""
    pdf_path = os.path.join(session_path, "pdfs", filename)
    if os.path.exists(pdf_path):
        return pdf_path
    return None
