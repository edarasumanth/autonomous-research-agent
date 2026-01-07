# Autonomous Research Agent

[![CI](https://github.com/edarasumanth/autonomous-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/edarasumanth/autonomous-research-agent/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/edarasumanth/autonomous-research-agent/graph/badge.svg)](https://codecov.io/gh/edarasumanth/autonomous-research-agent)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered research assistant built with the Claude Agent SDK. This application autonomously searches for academic papers, downloads PDFs, analyzes content, and generates comprehensive research reports.

## Features

- **Chat-Based Research**: Natural language interface for research queries
- **Autonomous Workflow**: Searches, downloads, reads, and synthesizes papers automatically
- **PDF Analysis**: Extracts and analyzes content from academic papers
- **Report Generation**: Creates comprehensive markdown reports with citations
- **Session Management**: Organizes research by topic with persistent storage
- **Follow-up Q&A**: Ask questions about completed research sessions

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Claude CLI)
- Docker & Docker Compose (for containerized deployment)
- API Keys:
  - [Anthropic API Key](https://console.anthropic.com/)
  - [Tavily API Key](https://tavily.com/)

### Setup

1. **Clone and configure:**
   ```bash
   cd "My First Project"
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run with Docker (Recommended):**
   ```bash
   docker-compose up -d
   ```
   Access at: http://localhost:8501

3. **Or run locally:**
   ```bash
   # Windows
   scripts\start.bat local

   # Linux/Mac
   chmod +x scripts/*.sh
   ./scripts/start.sh local
   ```

## Usage

### Starting the Application

**Docker:**
```bash
docker-compose up -d          # Start
docker-compose logs -f        # View logs
docker-compose down           # Stop
docker-compose up -d --build  # Rebuild
```

**Local:**
```bash
# Windows
scripts\start.bat local
scripts\stop.bat local

# Linux/Mac
./scripts/start.sh local
./scripts/stop.sh local
```

### Using the Research Agent

1. Open http://localhost:8501 in your browser
2. Type a research query like:
   - "Research attention mechanisms in transformers"
   - "Find papers on CRISPR gene editing"
   - "Investigate mixture of experts architectures"
3. Wait for the agent to search, download, and analyze papers
4. View the generated report and downloaded PDFs
5. Ask follow-up questions about the research

## Project Structure

```
autonomous-research-agent/
├── streamlit_app.py         # Web interface
├── chat_research_agent.py   # Chat-based research agent
├── web_research_agent.py    # Structured research agent
├── web_research_tools.py    # MCP tools (search, download, read)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── .env.example            # Environment variables template
├── .dockerignore           # Docker build exclusions
├── scripts/
│   ├── start.bat           # Windows start script
│   ├── start.sh            # Unix start script
│   ├── stop.bat            # Windows stop script
│   └── stop.sh             # Unix stop script
└── research_sessions/      # Research output (auto-created)
    └── {timestamp}_{topic}/
        ├── pdfs/           # Downloaded papers
        ├── notes/          # Research notes
        ├── report.md       # Generated report
        ├── metadata.json   # Session metadata
        └── completion.json # Completion stats
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Yes |
| `TAVILY_API_KEY` | Tavily API key for web search | Yes |

### Docker Configuration

Edit `docker-compose.yml` to customize:
- Port mapping (default: 8501)
- Volume mounts
- Resource limits

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
streamlit run streamlit_app.py
```

### Building Docker Image

```bash
docker build -t research-agent .
docker run -p 8501:8501 --env-file .env research-agent
```

## Architecture

The application uses the Claude Agent SDK with MCP (Model Context Protocol) tools:

- **web_search**: Search for academic papers using Tavily
- **download_pdfs**: Download PDF files from URLs
- **read_pdf**: Extract text from PDFs using pdfplumber
- **save_note**: Save research findings
- **read_notes**: Retrieve saved notes
- **write_report**: Generate markdown reports

## Troubleshooting

### Common Issues

1. **"Failed to start Claude Code"**
   - Ensure Claude CLI is installed: `npm install -g @anthropic-ai/claude-code`
   - Check that Node.js is in PATH

2. **"API key not found"**
   - Verify `.env` file exists with correct keys
   - Restart the application after changing `.env`

3. **PDF download failures**
   - Some papers may be behind paywalls
   - The agent will continue with available papers

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Built with [Claude Agent SDK](https://github.com/anthropics/claude-code)
- Web interface powered by [Streamlit](https://streamlit.io/)
- Web search by [Tavily](https://tavily.com/)
