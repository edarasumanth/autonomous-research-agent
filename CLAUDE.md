# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A research agent built with the Claude Agent SDK demonstrating three interaction patterns:
1. **Stateless** (`query()`) - One-off queries with no memory between calls
2. **Conversational** (`ClaudeSDKClient`) - Multi-turn sessions with memory across exchanges
3. **Autonomous** (`autonomous_agent.py`) - Fully autonomous goal-driven research without user intervention

## Commands

```bash
# Activate virtual environment (Windows)
source ./venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run the research agent (interactive menu)
python research_agent.py

# Run the autonomous research agent (CLI)
python autonomous_agent.py

# Run the web interface
streamlit run streamlit_app.py
```

## Architecture

### Web Interface (`streamlit_app.py`)

Production-ready Streamlit web interface for the research agent:

**Features:**
- Elegant, intuitive UI with gradient styling
- Left sidebar showing research history (folder structure)
- Per-query folder organization in `research_sessions/`
- PDF viewer with download capability
- Real-time progress tracking during research
- Markdown report rendering

**Folder Structure:**
```
research_sessions/
├── 20240106_103000_LLMs_for_code/
│   ├── metadata.json      # Research request details
│   ├── completion.json    # Stats and timing
│   ├── report.md          # Final research report
│   ├── pdfs/              # Downloaded papers
│   │   └── *.pdf
│   └── notes/             # Research notes
│       └── *.json
└── 20240106_110000_RAG_systems/
    └── ...
```

**Key Files:**
- `streamlit_app.py` - Main web application
- `web_research_agent.py` - Agent with session folder support
- `web_research_tools.py` - Tools with configurable output directories

### Autonomous Agent (`autonomous_agent.py`)

Fully autonomous research agent that works towards goals independently:

**Key Features:**
- User provides comprehensive input upfront (topic, background, constraints)
- Agent works autonomously without asking clarifying questions
- Uses tools: `web_search`, `download_pdfs`, `read_pdf`, `save_note`, `read_notes`, `write_report`
- Self-determines completion based on research goals
- Outputs comprehensive markdown report to `papers/` folder

**Usage:**
```python
from autonomous_agent import ResearchRequest, run_autonomous_research

request = ResearchRequest(
    topic="Your research topic",
    background="Detailed context and what you want to learn...",
    depth="standard",  # quick/standard/deep
    max_papers=10,
    time_period="2020-2024",
    domains=["machine learning", "biology"],
)

result = await run_autonomous_research(request)
```

**Workflow Phases:**
1. Planning - Parse request, identify search strategies
2. Searching - Execute varied web searches
3. Downloading - Acquire relevant PDFs
4. Reading - Extract and analyze PDF content
5. Note-taking - Document findings progressively
6. Reporting - Generate final markdown report

### Two Approaches in `research_agent.py`

**Stateless Approach** (`query()`):
- `stateless_research_query(prompt, system_prompt)` - Single query, fresh session each time
- No context preserved between calls
- Best for independent, one-off questions

**Conversational Approach** (`ClaudeSDKClient`):
- `ConversationalResearchAgent` class - Maintains session across multiple turns
- Uses async context manager pattern (`async with`)
- `ask(question)` method sends queries while preserving conversation history
- Claude remembers all previous exchanges in the session

### Example Functions

| Function | Description |
|----------|-------------|
| `run_stateless_example()` | Demonstrates independent queries with no memory |
| `run_conversational_example()` | Multi-turn protein digestion research with follow-ups |
| `run_interactive_example()` | Interactive chat session (type 'quit' to exit) |
| `run_guided_analysis()` | Progressive 5-phase topic exploration |

## SDK Usage Patterns

**Stateless (no memory):**
```python
async for message in query(prompt=prompt, options=options):
    # Handle AssistantMessage, ResultMessage
```

**Conversational (with memory):**
```python
async with ClaudeSDKClient(options) as client:
    await client.query("First question")
    async for msg in client.receive_response():
        # Process response

    await client.query("Follow-up question")  # Claude remembers context
    async for msg in client.receive_response():
        # Process response
```
