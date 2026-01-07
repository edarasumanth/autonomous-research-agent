# Development Guide: Building the Autonomous Research Agent

This guide documents the step-by-step process used to create the Autonomous Research Agent application. Follow these steps to recreate the project or build similar applications with the Claude Agent SDK.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Claude Agent SDK Installation](#claude-agent-sdk-installation)
4. [Creating MCP Research Tools](#creating-mcp-research-tools)
5. [Building the Research Agent](#building-the-research-agent)
6. [Building the Chat Interface](#building-the-chat-interface)
7. [Creating the Streamlit Web UI](#creating-the-streamlit-web-ui)
8. [Docker Configuration](#docker-configuration)
9. [Testing and Debugging](#testing-and-debugging)
10. [Deployment](#deployment)
11. [Version Control and Releases](#version-control-and-releases)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Main programming language |
| Node.js | 18+ | Required for Claude CLI |
| Docker | Latest | Containerized deployment |
| Git | Latest | Version control |

### API Keys Required

1. **Anthropic API Key**
   - Sign up at: https://console.anthropic.com/
   - Used for Claude AI models (Opus, Sonnet, Haiku)

2. **Tavily API Key**
   - Sign up at: https://tavily.com/
   - Used for web search functionality

---

## Project Setup

### Step 1: Create Project Directory

```bash
mkdir autonomous-research-agent
cd autonomous-research-agent
```

### Step 2: Initialize Git Repository

```bash
git init
```

### Step 3: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Step 4: Create Project Structure

```bash
mkdir -p research_sessions scripts docs/screenshots
```

Final structure:
```
autonomous-research-agent/
├── venv/                    # Virtual environment
├── research_sessions/       # Output folder (auto-created)
├── scripts/                 # Start/stop scripts
├── docs/
│   └── screenshots/         # App screenshots
├── .env                     # API keys (not committed)
├── .env.example             # Template for .env
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker compose config
├── streamlit_app.py         # Web interface
├── chat_research_agent.py   # Chat agent logic
├── web_research_agent.py    # Structured agent
├── web_research_tools.py    # MCP tools
└── README.md                # Documentation
```

### Step 5: Create .gitignore

```gitignore
# Virtual environment
venv/
.venv/

# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*.egg-info/

# Research output
research_sessions/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

### Step 6: Create .env.example

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### Step 7: Create .env (local only)

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

---

## Claude Agent SDK Installation

### Step 1: Install Claude CLI (Node.js)

```bash
npm install -g @anthropic-ai/claude-code
```

### Step 2: Create requirements.txt

```txt
# Claude Agent SDK
claude-agent-sdk>=0.1.0

# Web Interface
streamlit>=1.28.0

# PDF Processing
pdfplumber>=0.10.0

# HTTP Requests
httpx>=0.25.0
aiohttp>=3.9.0

# Web Search
tavily-python>=0.3.0

# Async Support
anyio>=4.0.0

# Environment Variables
python-dotenv>=1.0.0
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```python
# test_sdk.py
from claude_agent_sdk import query, ClaudeAgentOptions

async def test():
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant.",
        permission_mode="bypassPermissions"
    )
    async for message in query(prompt="Say hello!", options=options):
        print(message)

import asyncio
asyncio.run(test())
```

---

## Creating MCP Research Tools

The Model Context Protocol (MCP) allows you to create custom tools that the Claude agent can use.

### Step 1: Create web_research_tools.py

```python
"""
MCP Tools for Web Research Agent

Provides tools for searching, downloading, reading PDFs, and taking notes.
"""

import os
import json
import httpx
import pdfplumber
from datetime import datetime
from dataclasses import dataclass
from tavily import TavilyClient

# Configuration class for managing output directories
@dataclass
class ResearchConfig:
    """Global configuration for research output."""
    _output_dir: str = "research_sessions"
    _current_session: str = None

    @classmethod
    def set_output_dir(cls, path: str):
        cls._output_dir = path
        cls._current_session = path

    @classmethod
    def get_output_dir(cls) -> str:
        return cls._current_session or cls._output_dir

    @classmethod
    def create_session_folder(cls, topic: str, base_dir: str = "research_sessions") -> str:
        """Create a new session folder with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() or c in " -_" else "" for c in topic)[:50]
        safe_topic = safe_topic.strip().replace(" ", "_")

        session_dir = os.path.join(base_dir, f"{timestamp}_{safe_topic}")
        os.makedirs(session_dir, exist_ok=True)
        os.makedirs(os.path.join(session_dir, "pdfs"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)

        cls._current_session = session_dir
        return session_dir
```

### Step 2: Define MCP Tool Functions

```python
# Web Search Tool
async def web_search(query: str, max_results: int = 10) -> dict:
    """Search the web for research papers and articles."""
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_domains=["arxiv.org", "scholar.google.com", "semanticscholar.org"]
    )

    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("content", "")[:500]
        })

    return {"results": results, "count": len(results)}


# Download PDFs Tool
async def download_pdfs(urls: list[str]) -> dict:
    """Download PDF files from URLs."""
    output_dir = ResearchConfig.get_output_dir()
    pdf_dir = os.path.join(output_dir, "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    downloaded = []
    failed = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    # Generate filename from URL
                    filename = url.split("/")[-1]
                    if not filename.endswith(".pdf"):
                        filename = f"{hash(url)}.pdf"

                    filepath = os.path.join(pdf_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    downloaded.append(filename)
            except Exception as e:
                failed.append({"url": url, "error": str(e)})

    return {"downloaded": downloaded, "failed": failed}


# Read PDF Tool
def read_pdf(filename: str) -> dict:
    """Extract text content from a PDF file."""
    output_dir = ResearchConfig.get_output_dir()
    filepath = os.path.join(output_dir, "pdfs", filename)

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filename}"}

    try:
        text_content = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages[:20]):  # Limit to 20 pages
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {i+1} ---\n{text}")

        full_text = "\n\n".join(text_content)
        return {
            "filename": filename,
            "content": full_text[:50000],  # Limit content size
            "pages": len(text_content)
        }
    except Exception as e:
        return {"error": str(e)}


# Save Note Tool
def save_note(title: str, content: str, note_type: str = "finding", source: str = "") -> dict:
    """Save a research note."""
    output_dir = ResearchConfig.get_output_dir()
    notes_dir = os.path.join(output_dir, "notes")
    os.makedirs(notes_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{title[:30].replace(' ', '_')}.json"

    note = {
        "title": title,
        "content": content,
        "type": note_type,
        "source": source,
        "created_at": datetime.now().isoformat()
    }

    filepath = os.path.join(notes_dir, filename)
    with open(filepath, "w") as f:
        json.dump(note, f, indent=2)

    return {"saved": filename, "title": title}


# Read Notes Tool
def read_notes() -> dict:
    """Read all saved notes."""
    output_dir = ResearchConfig.get_output_dir()
    notes_dir = os.path.join(output_dir, "notes")

    if not os.path.exists(notes_dir):
        return {"notes": [], "count": 0}

    notes = []
    for filename in os.listdir(notes_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(notes_dir, filename)
            with open(filepath, "r") as f:
                notes.append(json.load(f))

    return {"notes": notes, "count": len(notes)}


# Write Report Tool
def write_report(content: str, title: str = "Research Report") -> dict:
    """Write the final research report."""
    output_dir = ResearchConfig.get_output_dir()

    filepath = os.path.join(output_dir, "report.md")
    with open(filepath, "w") as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(content)

    return {"saved": "report.md", "path": filepath}
```

### Step 3: Create MCP Server Definition

```python
# MCP Server configuration for Claude Agent SDK
web_research_tools_server = {
    "type": "function",
    "tools": [
        {
            "name": "web_search",
            "description": "Search the web for research papers and academic articles",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            "handler": web_search
        },
        {
            "name": "download_pdfs",
            "description": "Download PDF files from URLs",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["urls"]
            },
            "handler": download_pdfs
        },
        {
            "name": "read_pdf",
            "description": "Extract and read text from a PDF file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"}
                },
                "required": ["filename"]
            },
            "handler": read_pdf
        },
        {
            "name": "save_note",
            "description": "Save a research finding or note",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "note_type": {"type": "string", "default": "finding"},
                    "source": {"type": "string", "default": ""}
                },
                "required": ["title", "content"]
            },
            "handler": save_note
        },
        {
            "name": "read_notes",
            "description": "Read all saved research notes",
            "parameters": {"type": "object", "properties": {}},
            "handler": read_notes
        },
        {
            "name": "write_report",
            "description": "Write the final research report in markdown",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "title": {"type": "string", "default": "Research Report"}
                },
                "required": ["content"]
            },
            "handler": write_report
        }
    ]
}
```

---

## Building the Research Agent

### Step 1: Create chat_research_agent.py

```python
"""
Chat-Based Research Agent

Conversational research agent that maintains context across interactions.
"""

import asyncio
import os
import json
from datetime import datetime
from typing import AsyncGenerator, Callable

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

from web_research_tools import web_research_tools_server, ResearchConfig
```

### Step 2: Define System Prompts

```python
RESEARCH_CHAT_SYSTEM_PROMPT = """You are an intelligent research assistant with access to powerful research tools.

## Available Tools

- **web_search**: Search for research papers and academic articles
- **download_pdfs**: Download PDF files from URLs
- **read_pdf**: Extract and read text from downloaded PDFs
- **save_note**: Save important findings and insights
- **read_notes**: Retrieve all saved notes
- **write_report**: Generate a comprehensive markdown report

## Research Workflow

When conducting research, ALWAYS follow these steps:
1. Start with web searches to find relevant papers (at least 2-3 searches)
2. Download the most promising PDFs (aim for 3-5 papers)
3. Read and analyze the papers thoroughly
4. Save key findings as notes using save_note
5. Synthesize and share insights with the user
6. **IMPORTANT**: ALWAYS use the write_report tool to generate a formal markdown report at the end

You MUST call write_report at the end of every research task.
"""
```

### Step 3: Create Streaming Chat Function

```python
async def chat_with_agent(
    user_message: str,
    chat_history: list[dict],
    mode: str = "research",
    research_session_path: str | None = None,
    on_tool_use: Callable[[str, dict], None] | None = None,
    model: str | None = None,
    on_complete: Callable[[float, float], None] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response from the agent.

    Args:
        user_message: The user's message
        chat_history: Previous messages
        mode: "research" or "followup"
        research_session_path: Path to session folder
        on_tool_use: Callback when tool is used
        model: Model to use (opus, sonnet, haiku)
        on_complete: Callback with (duration_ms, cost_usd)

    Yields:
        Chunks of the assistant's response
    """
    # Create session folder if needed
    if mode == "research":
        if research_session_path:
            ResearchConfig.set_output_dir(research_session_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = os.path.join("research_sessions", f"{timestamp}_chat")
            ResearchConfig.create_session_folder("chat_research", "research_sessions")

    # Configure agent options
    options = ClaudeAgentOptions(
        system_prompt=RESEARCH_CHAT_SYSTEM_PROMPT,
        mcp_servers={"research": web_research_tools_server},
        permission_mode="bypassPermissions",
        max_turns=50,
        max_budget_usd=3.0,
        model=model,
    )

    # Build conversation context
    conversation_prompt = ""
    for msg in chat_history[-10:]:
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

                            # Yield tool notifications
                            if tool_name == "web_search":
                                yield f"\n\n🔍 *Searching...*\n\n"
                            elif tool_name == "download_pdfs":
                                yield f"\n\n📥 *Downloading PDFs...*\n\n"
                            elif tool_name == "read_pdf":
                                yield f"\n\n📖 *Reading PDF...*\n\n"

                elif isinstance(message, ResultMessage):
                    if on_complete:
                        on_complete(
                            getattr(message, 'duration_ms', 0),
                            getattr(message, 'total_cost_usd', 0)
                        )

    except Exception as e:
        yield f"\n\n❌ Error: {str(e)}"
```

---

## Creating the Streamlit Web UI

### Step 1: Create streamlit_app.py Structure

```python
"""
Streamlit Web Interface for Autonomous Research Agent
"""

import streamlit as st
import asyncio
import os
import json
import random
import shutil
from datetime import datetime

from chat_research_agent import chat_with_agent
from web_research_tools import ResearchConfig

# Page configuration
st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

### Step 2: Add Custom CSS

```python
def load_custom_css():
    st.markdown("""
    <style>
    /* Main gradient background */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }

    /* Chat message styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 8px;
        transition: transform 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: rgba(0, 0, 0, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)
```

### Step 3: Initialize Session State

```python
def initialize_session_state():
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if "current_session_dir" not in st.session_state:
        st.session_state.current_session_dir = None

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "claude-sonnet-4-20250514"

    if "quick_topics" not in st.session_state:
        ALL_TOPICS = [
            {"icon": "🧠", "label": "Transformer Architectures", "query": "..."},
            {"icon": "🧬", "label": "CRISPR Gene Editing", "query": "..."},
            # ... more topics
        ]
        st.session_state.quick_topics = random.sample(ALL_TOPICS, 3)

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
```

### Step 4: Create Sidebar

```python
def render_sidebar():
    with st.sidebar:
        st.title("🔬 Research Agent")

        # Model selector
        model_options = {
            "🧠 Opus (Best)": "claude-opus-4-20250514",
            "⚡ Sonnet (Fast)": "claude-sonnet-4-20250514",
            "🚀 Haiku (Quick)": "claude-haiku-3-20250514"
        }
        selected = st.selectbox("Model", list(model_options.keys()))
        st.session_state.selected_model = model_options[selected]

        # New research button
        if st.button("➕ New Research", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.current_session_dir = None
            st.rerun()

        # Research history
        st.subheader("📚 Research History")
        sessions = get_research_sessions()
        for session in sessions:
            render_session_card(session)
```

### Step 5: Create Main Chat Interface

```python
def render_chat():
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me to research something..."):
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # Create session folder
        if not st.session_state.current_session_dir:
            st.session_state.current_session_dir = ResearchConfig.create_session_folder(
                prompt[:50], "research_sessions"
            )

        # Stream response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            async def stream_response():
                nonlocal full_response
                async for chunk in chat_with_agent(
                    prompt,
                    st.session_state.chat_messages[:-1],
                    mode="research",
                    research_session_path=st.session_state.current_session_dir,
                    model=st.session_state.selected_model
                ):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")

            asyncio.run(stream_response())
            response_placeholder.markdown(full_response)

        # Save assistant message
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": full_response
        })
```

### Step 6: Run the App

```python
def main():
    load_custom_css()
    initialize_session_state()
    render_sidebar()
    render_chat()

if __name__ == "__main__":
    main()
```

---

## Docker Configuration

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Claude CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p research_sessions

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  research-agent:
    build: .
    container_name: research-agent
    ports:
      - "8501:8501"
    env_file:
      - .env
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    volumes:
      - ./research_sessions:/app/research_sessions
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G
```

### Step 3: Create .dockerignore

```
venv/
__pycache__/
*.pyc
.env
.git/
.gitignore
*.md
research_sessions/
```

### Step 4: Build and Run

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

---

## Testing and Debugging

### Step 1: Test Individual Components

```python
# test_tools.py
import asyncio
from web_research_tools import web_search, download_pdfs, read_pdf

async def test_search():
    result = await web_search("transformer attention mechanism")
    print(f"Found {result['count']} results")
    for r in result['results'][:3]:
        print(f"  - {r['title']}")

asyncio.run(test_search())
```

### Step 2: Test Agent Locally

```bash
# Run Streamlit in development mode
streamlit run streamlit_app.py --server.runOnSave=true
```

### Step 3: Test Docker Container

```bash
# Check container status
docker-compose ps

# Check container logs
docker-compose logs -f

# Check resource usage
docker stats research-agent
```

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| "Claude CLI not found" | Install Node.js and run `npm install -g @anthropic-ai/claude-code` |
| "API key not found" | Check `.env` file exists with correct keys |
| "PDF download failed" | Some papers are paywalled; agent will continue with available papers |
| "Slow first response" | First query takes ~10s for SDK warm-up; subsequent queries are faster |
| "Container not starting" | Check logs with `docker-compose logs -f` |

---

## Deployment

### Option 1: Docker (Recommended)

```bash
# Production deployment
docker-compose up -d

# Access at http://localhost:8501
```

### Option 2: Local Python

```bash
# Windows
scripts\start.bat local

# Linux/Mac
./scripts/start.sh local
```

### Option 3: Cloud Deployment

For cloud deployment (AWS, GCP, Azure):

1. Push Docker image to container registry
2. Deploy to container service (ECS, Cloud Run, AKS)
3. Configure environment variables for API keys
4. Set up persistent volume for `research_sessions/`

---

## Version Control and Releases

### Step 1: Commit Changes

```bash
git add .
git commit -m "Your commit message"
```

### Step 2: Push to GitHub

```bash
git remote add origin https://github.com/username/repo.git
git branch -M main
git push -u origin main
```

### Step 3: Create Release Tag

```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

### Step 4: Create GitHub Release

```bash
gh release create v1.0.0 --title "v1.0.0 - Initial Release" --notes "Release notes here"
```

---

## Summary

This guide covered:

1. **Project Setup** - Directory structure, virtual environment, git initialization
2. **Claude Agent SDK** - Installation and configuration
3. **MCP Tools** - Creating custom tools for web search, PDF handling, notes
4. **Research Agent** - Building the conversational agent with streaming
5. **Streamlit UI** - Creating the web interface with session management
6. **Docker** - Containerization for easy deployment
7. **Testing** - Debugging and troubleshooting
8. **Deployment** - Running in production
9. **Version Control** - Git workflow and releases

For questions or issues, refer to:
- [Claude Agent SDK Documentation](https://github.com/anthropics/claude-code)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Project Issues](https://github.com/edarasumanth/autonomous-research-agent/issues)
