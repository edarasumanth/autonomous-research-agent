# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [1.0.0] - 2025-01-07

### Added
- **Chat-Based Research Interface**: Natural language interface for research queries via Streamlit web UI
- **Autonomous Research Workflow**: Fully autonomous search, download, analysis, and report generation
- **PDF Analysis**: Extract and analyze content from academic papers using pdfplumber
- **Report Generation**: Create comprehensive markdown reports with citations
- **Session Management**: Organize research by topic with persistent storage in `research_sessions/`
- **Follow-up Q&A**: Ask questions about completed research sessions
- **MCP Tools**:
  - `web_search` - Search for academic papers using Tavily
  - `download_pdfs` - Download PDF files from URLs
  - `read_pdf` - Extract text from PDFs
  - `save_note` - Save research findings
  - `read_notes` - Retrieve saved notes
  - `write_report` - Generate markdown reports
- **Docker Support**: Containerized deployment with Docker and Docker Compose
- **Cross-Platform Scripts**: Start/stop scripts for Windows and Unix
- **GitHub Actions CI**: Automated testing, linting, and Docker builds
- **PyPI Publishing Workflow**: Automated package publishing on release

### Infrastructure
- Python 3.11+ support
- Streamlit web interface
- Claude Agent SDK integration
- Tavily API for web search
- pdfplumber for PDF processing

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| [1.0.0] | 2025-01-07 | Initial release |

[Unreleased]: https://github.com/edarasumanth/autonomous-research-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/edarasumanth/autonomous-research-agent/releases/tag/v1.0.0
