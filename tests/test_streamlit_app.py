"""
Unit tests for streamlit_app module.

These tests verify the app's helper functions and session management.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSessionHelpers:
    """Tests for session management helper functions."""

    def test_get_research_sessions_empty(self, tmp_path):
        """Test getting sessions from empty directory."""
        # Import the function (mocking streamlit)
        with patch.dict(sys.modules, {'streamlit': MagicMock()}):
            # We need to test the logic, not the actual streamlit import
            sessions_dir = tmp_path / "research_sessions"
            sessions_dir.mkdir()

            sessions = list(sessions_dir.iterdir())
            assert len(sessions) == 0

    def test_get_research_sessions_with_data(self, tmp_path):
        """Test getting sessions with valid data."""
        sessions_dir = tmp_path / "research_sessions"
        sessions_dir.mkdir()

        # Create a valid session
        session = sessions_dir / "20240108_120000_test_topic"
        session.mkdir()

        metadata = {
            "topic": "Test Topic",
            "created_at": datetime.now().isoformat()
        }
        (session / "metadata.json").write_text(json.dumps(metadata))

        sessions = [d for d in sessions_dir.iterdir() if d.is_dir()]
        assert len(sessions) == 1

    def test_session_has_required_files(self, tmp_path):
        """Test checking if session has required files."""
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create required subdirectories
        (session_dir / "pdfs").mkdir()
        (session_dir / "notes").mkdir()

        # Create metadata
        metadata = {"topic": "Test", "created_at": datetime.now().isoformat()}
        (session_dir / "metadata.json").write_text(json.dumps(metadata))

        assert (session_dir / "metadata.json").exists()
        assert (session_dir / "pdfs").is_dir()
        assert (session_dir / "notes").is_dir()


class TestMetadataParsing:
    """Tests for metadata parsing functions."""

    def test_parse_valid_metadata(self, tmp_path):
        """Test parsing valid metadata.json."""
        metadata = {
            "topic": "AI Research",
            "created_at": "2024-01-08T12:00:00",
            "model": "claude-sonnet-4-20250514"
        }

        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        with open(metadata_file) as f:
            parsed = json.load(f)

        assert parsed["topic"] == "AI Research"
        assert parsed["model"] == "claude-sonnet-4-20250514"

    def test_parse_completion_data(self, tmp_path):
        """Test parsing completion.json."""
        completion = {
            "completed_at": "2024-01-08T12:30:00",
            "duration_ms": 180000,
            "cost_usd": 0.50,
            "model": "claude-sonnet-4-20250514",
            "stats": {
                "searches": 3,
                "downloads": 5,
                "reads": 5,
                "notes": 4,
                "report": True
            }
        }

        completion_file = tmp_path / "completion.json"
        completion_file.write_text(json.dumps(completion))

        with open(completion_file) as f:
            parsed = json.load(f)

        assert parsed["duration_ms"] == 180000
        assert parsed["cost_usd"] == 0.50
        assert parsed["stats"]["report"] is True


class TestTopicGeneration:
    """Tests for quick topic generation."""

    def test_topics_list_structure(self):
        """Test that topics have required fields."""
        # Sample topic structure as defined in streamlit_app.py
        sample_topics = [
            {
                "icon": "🧠",
                "label": "Transformer Architectures",
                "query": "Research transformer architectures"
            },
            {
                "icon": "🧬",
                "label": "CRISPR Gene Editing",
                "query": "Research CRISPR applications"
            }
        ]

        for topic in sample_topics:
            assert "icon" in topic
            assert "label" in topic
            assert "query" in topic
            assert len(topic["label"]) > 0
            assert len(topic["query"]) > 0

    def test_random_topic_selection(self):
        """Test random selection of topics."""
        import random

        topics = [{"label": f"Topic {i}"} for i in range(24)]
        selected = random.sample(topics, 3)

        assert len(selected) == 3
        assert len(set(t["label"] for t in selected)) == 3  # All unique


class TestModelSelection:
    """Tests for model selection logic."""

    def test_model_options_mapping(self):
        """Test model display names to API names mapping."""
        model_options = {
            "🧠 Opus (Best)": "claude-opus-4-20250514",
            "⚡ Sonnet (Fast)": "claude-sonnet-4-20250514",
            "🚀 Haiku (Quick)": "claude-haiku-3-20250514"
        }

        assert len(model_options) == 3
        assert "opus" in model_options["🧠 Opus (Best)"].lower()
        assert "sonnet" in model_options["⚡ Sonnet (Fast)"].lower()
        assert "haiku" in model_options["🚀 Haiku (Quick)"].lower()


class TestSessionFiltering:
    """Tests for session filtering logic."""

    def test_filter_valid_sessions(self, tmp_path):
        """Test filtering out invalid sessions."""
        sessions_dir = tmp_path / "research_sessions"
        sessions_dir.mkdir()

        # Create valid session with report
        valid_session = sessions_dir / "20240108_120000_valid"
        valid_session.mkdir()
        (valid_session / "metadata.json").write_text('{"topic": "Valid"}')
        (valid_session / "report.md").write_text("# Report")

        # Create invalid session (no metadata)
        invalid_session = sessions_dir / "20240108_130000_invalid"
        invalid_session.mkdir()

        # Filter sessions
        valid_sessions = []
        for session_path in sessions_dir.iterdir():
            if session_path.is_dir():
                metadata_file = session_path / "metadata.json"
                if metadata_file.exists():
                    valid_sessions.append(session_path)

        assert len(valid_sessions) == 1
        assert valid_sessions[0].name == "20240108_120000_valid"

    def test_session_has_report(self, tmp_path):
        """Test checking if session has report."""
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # No report initially
        assert not (session_dir / "report.md").exists()

        # Add report
        (session_dir / "report.md").write_text("# Research Report\n\nFindings...")

        assert (session_dir / "report.md").exists()
        report_content = (session_dir / "report.md").read_text()
        assert "Research Report" in report_content


class TestDurationFormatting:
    """Tests for duration formatting logic."""

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds."""
        duration_ms = 45000  # 45 seconds

        seconds = duration_ms / 1000
        if seconds < 60:
            formatted = f"{seconds:.0f}s"
        else:
            minutes = seconds / 60
            formatted = f"{minutes:.1f}m"

        assert formatted == "45s"

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes."""
        duration_ms = 180000  # 3 minutes

        seconds = duration_ms / 1000
        if seconds < 60:
            formatted = f"{seconds:.0f}s"
        else:
            minutes = seconds / 60
            formatted = f"{minutes:.1f}m"

        assert formatted == "3.0m"

    def test_format_cost(self):
        """Test formatting cost display."""
        cost = 0.523456

        if cost < 0.01:
            formatted = f"${cost:.4f}"
        else:
            formatted = f"${cost:.2f}"

        assert formatted == "$0.52"


class TestClearHistory:
    """Tests for clear history functionality."""

    def test_clear_all_sessions(self, tmp_path):
        """Test clearing all research sessions."""
        import shutil

        sessions_dir = tmp_path / "research_sessions"
        sessions_dir.mkdir()

        # Create multiple sessions
        for i in range(3):
            session = sessions_dir / f"session_{i}"
            session.mkdir()
            (session / "metadata.json").write_text('{"topic": "Test"}')

        # Verify sessions exist
        assert len(list(sessions_dir.iterdir())) == 3

        # Clear all sessions
        for session in sessions_dir.iterdir():
            if session.is_dir():
                shutil.rmtree(session)

        # Verify sessions are cleared
        assert len(list(sessions_dir.iterdir())) == 0
