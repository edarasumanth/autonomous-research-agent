"""
Configuration management for the Research Agent.

Handles environment variables, settings, and configuration validation.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))

    # Paths - Use environment variable or /app for Docker, otherwise project root
    base_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("BASE_DIR", "/app" if os.path.exists("/app") else str(Path.cwd()))
        )
    )
    research_sessions_dir: Path = field(default=None)
    papers_dir: Path = field(default=None)

    # Application Settings
    app_name: str = "Autonomous Research Agent"
    app_version: str = "1.0.0"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # Streamlit Settings
    streamlit_port: int = field(default_factory=lambda: int(os.getenv("STREAMLIT_PORT", "8501")))
    streamlit_host: str = field(default_factory=lambda: os.getenv("STREAMLIT_HOST", "0.0.0.0"))

    # Research Settings
    max_papers: int = field(default_factory=lambda: int(os.getenv("MAX_PAPERS", "10")))
    default_search_depth: str = field(
        default_factory=lambda: os.getenv("DEFAULT_SEARCH_DEPTH", "standard")
    )

    def __post_init__(self):
        """Initialize computed fields after dataclass creation."""
        if self.research_sessions_dir is None:
            self.research_sessions_dir = self.base_dir / "research_sessions"
        if self.papers_dir is None:
            self.papers_dir = self.base_dir / "papers"

        # Create directories if they don't exist
        self.research_sessions_dir.mkdir(parents=True, exist_ok=True)
        self.papers_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """
        Validate required settings.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is not set")

        if not self.tavily_api_key:
            errors.append("TAVILY_API_KEY is not set")

        return errors

    @property
    def is_valid(self) -> bool:
        """Check if all required settings are configured."""
        return len(self.validate()) == 0

    def get_api_keys(self) -> dict[str, str]:
        """Get API keys as a dictionary."""
        return {
            "anthropic": self.anthropic_api_key,
            "tavily": self.tavily_api_key,
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    load_dotenv(override=True)
    settings = Settings()
    return settings
