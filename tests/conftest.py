"""
Pytest configuration and fixtures for the Research Agent test suite.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """Get the test data directory."""
    test_data = project_root / "tests" / "data"
    test_data.mkdir(exist_ok=True)
    return test_data


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DEBUG", "true")


@pytest.fixture
def temp_research_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for research sessions."""
    research_dir = tmp_path / "research_sessions"
    research_dir.mkdir()
    return research_dir


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF-like content for testing."""
    # Minimal PDF structure for testing
    return b"%PDF-1.4 minimal test content"


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings between tests."""
    yield
    # Cleanup if needed after each test
