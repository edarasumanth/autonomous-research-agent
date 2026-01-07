# Contributing to Autonomous Research Agent

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Claude CLI)
- Git

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/autonomous-research-agent.git
   cd autonomous-research-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Development Workflow

### Branching Strategy

- `main` - Stable release branch
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Making Changes

1. **Create a new branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and test locally:**
   ```bash
   # Run the application
   streamlit run streamlit_app.py

   # Run tests
   pytest -v
   ```

3. **Format and lint your code:**
   ```bash
   # Format with Black
   black .

   # Lint with Ruff
   ruff check .
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add PDF text extraction caching
fix: resolve timeout issue in web search
docs: update installation instructions
```

## Submitting Changes

### Pull Request Process

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what and why
   - Link to related issues (if any)

3. **Wait for review** - maintainers will review and provide feedback

4. **Address feedback** and push updates as needed

### PR Checklist

Before submitting, ensure:

- [ ] Code follows the project style (Black, Ruff)
- [ ] Tests pass locally
- [ ] New features include tests (if applicable)
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages follow conventions

## Project Structure

```
autonomous-research-agent/
├── streamlit_app.py         # Main web interface
├── chat_research_agent.py   # Chat-based agent
├── web_research_agent.py    # Structured research agent
├── web_research_tools.py    # MCP tools implementation
├── autonomous_agent.py      # CLI autonomous agent
├── autonomous_tools.py      # CLI tools
├── tools.py                 # Shared tool utilities
├── tests/                   # Test files
└── scripts/                 # Utility scripts
```

## Adding New Features

### Adding a New Tool

1. Define the tool function in `web_research_tools.py`:
   ```python
   async def your_tool(param: str) -> str:
       """Tool description."""
       # Implementation
       return result
   ```

2. Register the tool in the tools list

3. Add tests for the new tool

### Adding UI Components

1. Add components to `streamlit_app.py`
2. Follow existing patterns for state management
3. Test with various screen sizes

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_tools.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Use `pytest` fixtures for setup
- Mock external API calls

## Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests

Include:
- Use case description
- Proposed solution (if any)
- Alternatives considered

## Questions?

- Open a [GitHub Issue](https://github.com/edarasumanth/autonomous-research-agent/issues)
- Check existing issues for answers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
