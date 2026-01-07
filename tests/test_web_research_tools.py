"""
Unit tests for web_research_tools module.

These tests use mocks to avoid requiring API keys in CI.
Tests call the implementation functions directly (_*_impl functions).
"""

import json
import os

# Add parent directory to path for imports
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from web_research_tools import (
    ResearchConfig,
    _arxiv_search_impl,
    _download_pdfs_impl,
    _extract_filename_from_url,
    _is_pdf_url,
    _read_notes_impl,
    _read_pdf_impl,
    _save_note_impl,
    _web_search_impl,
    _write_report_impl,
)


class TestResearchConfig:
    """Tests for ResearchConfig class."""

    def test_set_output_dir(self, tmp_path):
        """Test setting output directory."""
        test_dir = str(tmp_path / "test_output")
        os.makedirs(test_dir, exist_ok=True)
        ResearchConfig.set_output_dir(test_dir)
        assert ResearchConfig.get_output_dir() == test_dir

    def test_create_session_folder(self, tmp_path):
        """Test creating a session folder."""
        base_dir = str(tmp_path)
        topic = "Test Research Topic"

        session_dir = ResearchConfig.create_session_folder(topic, base_dir)

        assert os.path.exists(session_dir)
        assert os.path.exists(os.path.join(session_dir, "pdfs"))
        assert os.path.exists(os.path.join(session_dir, "notes"))
        # Topic should be in folder name (with spaces preserved or converted)
        folder_name = os.path.basename(session_dir)
        assert "Test" in folder_name and "Research" in folder_name

    def test_create_session_folder_sanitizes_topic(self, tmp_path):
        """Test that special characters are removed from topic."""
        base_dir = str(tmp_path)
        topic = "Test/Research:Topic*With?Special<Chars>"

        session_dir = ResearchConfig.create_session_folder(topic, base_dir)

        # Should not contain special characters that are invalid in paths
        folder_name = os.path.basename(session_dir)
        assert "/" not in folder_name
        assert ":" not in folder_name
        assert "*" not in folder_name
        assert "?" not in folder_name
        assert "<" not in folder_name
        assert ">" not in folder_name

    def test_create_session_folder_truncates_long_topic(self, tmp_path):
        """Test that long topics are truncated."""
        base_dir = str(tmp_path)
        topic = "A" * 100  # Very long topic

        session_dir = ResearchConfig.create_session_folder(topic, base_dir)
        folder_name = os.path.basename(session_dir)

        # Folder name should be reasonable length (timestamp + truncated topic)
        assert len(folder_name) < 80

    def test_get_pdfs_dir(self, tmp_path):
        """Test getting PDFs directory."""
        test_dir = str(tmp_path / "session")
        os.makedirs(test_dir, exist_ok=True)
        ResearchConfig.set_output_dir(test_dir)

        pdfs_dir = ResearchConfig.get_pdfs_dir()
        assert pdfs_dir == os.path.join(test_dir, "pdfs")

    def test_get_notes_dir(self, tmp_path):
        """Test getting notes directory."""
        test_dir = str(tmp_path / "session")
        os.makedirs(test_dir, exist_ok=True)
        ResearchConfig.set_output_dir(test_dir)

        notes_dir = ResearchConfig.get_notes_dir()
        assert notes_dir == os.path.join(test_dir, "notes")


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_pdf_url_with_extension(self):
        """Test PDF URL detection with .pdf extension."""
        assert _is_pdf_url("https://arxiv.org/pdf/1234.5678.pdf") is True
        assert _is_pdf_url("https://example.com/paper.PDF") is True

    def test_is_pdf_url_with_patterns(self):
        """Test PDF URL detection with PDF patterns."""
        assert _is_pdf_url("https://arxiv.org/pdf/1234.5678") is True
        assert _is_pdf_url("https://example.com/download/pdf/paper") is True

    def test_is_pdf_url_not_pdf(self):
        """Test non-PDF URL detection."""
        assert _is_pdf_url("https://example.com/paper.html") is False
        assert _is_pdf_url("https://example.com/article") is False

    def test_extract_filename_from_url(self):
        """Test filename extraction from URL."""
        url = "https://arxiv.org/pdf/1234.5678.pdf"
        filename = _extract_filename_from_url(url)
        assert filename.endswith(".pdf")
        assert len(filename) <= 200

    def test_extract_filename_from_url_no_extension(self):
        """Test filename extraction when URL has no .pdf extension."""
        url = "https://arxiv.org/pdf/1234.5678"
        filename = _extract_filename_from_url(url)
        assert filename.endswith(".pdf")


class TestSaveNote:
    """Tests for _save_note_impl function."""

    @pytest.mark.asyncio
    async def test_save_note_creates_file(self, tmp_path):
        """Test that save_note creates a JSON file."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        result = await _save_note_impl(
            {
                "note_type": "finding",
                "title": "Test Finding",
                "content": "This is a test finding.",
                "source": "test_paper.pdf",
                "tags": ["test"],
            }
        )

        assert "is_error" not in result or not result.get("is_error")

        # Verify file was created
        notes_dir = os.path.join(session_dir, "notes")
        files = os.listdir(notes_dir)
        assert len(files) == 1
        assert files[0].endswith(".json")

    @pytest.mark.asyncio
    async def test_save_note_content(self, tmp_path):
        """Test that saved note has correct content."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        await _save_note_impl(
            {
                "note_type": "finding",
                "title": "Key Finding",
                "content": "Important discovery about AI.",
                "source": "paper.pdf",
            }
        )

        # Read the saved file
        notes_dir = os.path.join(session_dir, "notes")
        files = os.listdir(notes_dir)
        with open(os.path.join(notes_dir, files[0])) as f:
            note = json.load(f)

        assert note["title"] == "Key Finding"
        assert note["content"] == "Important discovery about AI."
        assert note["type"] == "finding"
        assert note["source"] == "paper.pdf"
        assert "timestamp" in note


class TestReadNotes:
    """Tests for _read_notes_impl function."""

    @pytest.mark.asyncio
    async def test_read_notes_empty(self, tmp_path):
        """Test reading notes from empty directory."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        result = await _read_notes_impl({})

        assert "content" in result
        assert "No" in result["content"][0]["text"] and "notes" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_read_notes_with_files(self, tmp_path):
        """Test reading multiple notes."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        # Save multiple notes
        for i in range(3):
            await _save_note_impl(
                {"note_type": "finding", "title": f"Note {i}", "content": f"Content {i}"}
            )

        result = await _read_notes_impl({})

        assert "content" in result
        assert "3 notes" in result["content"][0]["text"]


class TestWriteReport:
    """Tests for _write_report_impl function."""

    @pytest.mark.asyncio
    async def test_write_report_creates_file(self, tmp_path):
        """Test that write_report creates a markdown file."""
        session_dir = str(tmp_path / "session")
        os.makedirs(session_dir, exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        result = await _write_report_impl(
            {
                "title": "Test Research Report",
                "executive_summary": "This is a test report summary.",
                "findings": ["Finding 1", "Finding 2"],
                "references": ["Reference 1"],
            }
        )

        assert "is_error" not in result or not result.get("is_error")
        assert os.path.exists(os.path.join(session_dir, "report.md"))

    @pytest.mark.asyncio
    async def test_write_report_content(self, tmp_path):
        """Test that report has correct content."""
        session_dir = str(tmp_path / "session")
        os.makedirs(session_dir, exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        await _write_report_impl(
            {
                "title": "My Research",
                "executive_summary": "Summary of findings.",
                "findings": ["Key finding 1", "Key finding 2"],
            }
        )

        with open(os.path.join(session_dir, "report.md")) as f:
            content = f.read()

        assert "# Research Report: My Research" in content
        assert "Summary of findings" in content
        assert "Key finding 1" in content
        assert "Generated:" in content


class TestReadPdf:
    """Tests for _read_pdf_impl function."""

    @pytest.mark.asyncio
    async def test_read_pdf_file_not_found(self, tmp_path):
        """Test reading non-existent PDF."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "pdfs"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        result = await _read_pdf_impl({"filename": "nonexistent.pdf"})

        assert result.get("is_error") is True
        assert "not found" in result["content"][0]["text"].lower()


class TestWebSearch:
    """Tests for _web_search_impl function with mocked API."""

    @pytest.mark.asyncio
    async def test_web_search_no_api_key(self):
        """Test web search without API key."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}):
            result = await _web_search_impl({"query": "test query"})

            assert result.get("is_error") is True
            assert "TAVILY_API_KEY" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_web_search_success(self):
        """Test web search with mocked Tavily response."""
        mock_response = {
            "results": [
                {
                    "title": "Test Paper 1",
                    "url": "https://arxiv.org/pdf/1234.pdf",
                    "content": "Abstract of test paper 1",
                },
                {
                    "title": "Test Paper 2",
                    "url": "https://arxiv.org/abs/5678",
                    "content": "Abstract of test paper 2",
                },
            ]
        }

        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
            with patch("web_research_tools.TavilyClient") as MockClient:
                mock_instance = MagicMock()
                mock_instance.search.return_value = mock_response
                MockClient.return_value = mock_instance

                result = await _web_search_impl(
                    {"query": "transformer architecture", "max_results": 5}
                )

                assert "is_error" not in result or not result.get("is_error")
                assert "Found 2 results" in result["content"][0]["text"]
                assert "Test Paper 1" in result["content"][0]["text"]


class TestArxivSearch:
    """Tests for _arxiv_search_impl function with mocked ArXiv API."""

    @pytest.mark.asyncio
    async def test_arxiv_search_success(self):
        """Test ArXiv search with mocked response."""
        from datetime import datetime

        # Create mock paper objects
        mock_paper1 = MagicMock()
        mock_paper1.title = "Attention Is All You Need"
        mock_paper1.pdf_url = "https://arxiv.org/pdf/1706.03762.pdf"
        mock_paper1.entry_id = "http://arxiv.org/abs/1706.03762"
        mock_paper1.summary = "We propose a new simple network architecture, the Transformer."
        mock_paper1.published = datetime(2017, 6, 12)
        mock_paper1.categories = ["cs.CL", "cs.LG"]

        mock_author1 = MagicMock()
        mock_author1.name = "Ashish Vaswani"
        mock_author2 = MagicMock()
        mock_author2.name = "Noam Shazeer"
        mock_paper1.authors = [mock_author1, mock_author2]

        mock_paper2 = MagicMock()
        mock_paper2.title = "BERT: Pre-training of Deep Bidirectional Transformers"
        mock_paper2.pdf_url = "https://arxiv.org/pdf/1810.04805.pdf"
        mock_paper2.entry_id = "http://arxiv.org/abs/1810.04805"
        mock_paper2.summary = "We introduce BERT, a new language representation model."
        mock_paper2.published = datetime(2018, 10, 11)
        mock_paper2.categories = ["cs.CL"]

        mock_author3 = MagicMock()
        mock_author3.name = "Jacob Devlin"
        mock_paper2.authors = [mock_author3]

        with patch("web_research_tools.arxiv.Client") as mock_client_class:
            with patch("web_research_tools.arxiv.Search"):
                mock_client = MagicMock()
                mock_client.results.return_value = [mock_paper1, mock_paper2]
                mock_client_class.return_value = mock_client

                result = await _arxiv_search_impl(
                    {"query": "transformer attention", "max_results": 5}
                )

                assert "is_error" not in result or not result.get("is_error")
                text = result["content"][0]["text"]
                assert "Found 2 ArXiv papers" in text
                assert "Attention Is All You Need" in text
                assert "BERT" in text
                assert "arxiv.org/pdf" in text

    @pytest.mark.asyncio
    async def test_arxiv_search_no_results(self):
        """Test ArXiv search with no results."""
        with patch("web_research_tools.arxiv.Client") as mock_client_class:
            with patch("web_research_tools.arxiv.Search"):
                mock_client = MagicMock()
                mock_client.results.return_value = []
                mock_client_class.return_value = mock_client

                result = await _arxiv_search_impl({"query": "xyznonexistent123"})

                text = result["content"][0]["text"]
                assert "No ArXiv papers found" in text

    @pytest.mark.asyncio
    async def test_arxiv_search_with_category(self):
        """Test ArXiv search with category filter."""
        from datetime import datetime

        mock_paper = MagicMock()
        mock_paper.title = "Test ML Paper"
        mock_paper.pdf_url = "https://arxiv.org/pdf/2301.00000.pdf"
        mock_paper.entry_id = "http://arxiv.org/abs/2301.00000"
        mock_paper.summary = "A test paper about machine learning."
        mock_paper.published = datetime(2023, 1, 1)
        mock_paper.categories = ["cs.LG", "stat.ML"]

        mock_author = MagicMock()
        mock_author.name = "Test Author"
        mock_paper.authors = [mock_author]

        with patch("web_research_tools.arxiv.Client") as mock_client_class:
            with patch("web_research_tools.arxiv.Search") as mock_search_class:
                mock_client = MagicMock()
                mock_client.results.return_value = [mock_paper]
                mock_client_class.return_value = mock_client

                result = await _arxiv_search_impl(
                    {"query": "machine learning", "category": "cs.LG", "max_results": 10}
                )

                # Verify Search was called with category
                mock_search_class.assert_called_once()
                call_kwargs = mock_search_class.call_args
                assert "cs.LG" in call_kwargs[1]["query"]

                text = result["content"][0]["text"]
                assert "Test ML Paper" in text

    @pytest.mark.asyncio
    async def test_arxiv_search_error_handling(self):
        """Test ArXiv search error handling."""
        with patch("web_research_tools.arxiv.Client") as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")

            result = await _arxiv_search_impl({"query": "test query"})

            assert result.get("is_error") is True
            assert "ArXiv search error" in result["content"][0]["text"]


class TestDownloadPdfs:
    """Tests for _download_pdfs_impl function with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_download_pdfs_empty_urls(self, tmp_path):
        """Test downloading with empty URL list."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "pdfs"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        result = await _download_pdfs_impl({"urls": []})

        assert "No URLs provided" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_download_pdfs_success(self, tmp_path):
        """Test downloading PDFs with mocked HTTP response."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "pdfs"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 fake pdf content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()

        with patch("web_research_tools.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client

            result = await _download_pdfs_impl({"urls": ["https://example.com/paper.pdf"]})

            assert "Successful: 1" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_download_pdfs_failure(self, tmp_path):
        """Test handling of download failures."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "pdfs"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        with patch("web_research_tools.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client

            result = await _download_pdfs_impl({"urls": ["https://example.com/paper.pdf"]})

            assert "Failed: 1" in result["content"][0]["text"]


class TestIntegration:
    """Integration tests for the research workflow."""

    @pytest.mark.asyncio
    async def test_full_note_workflow(self, tmp_path):
        """Test complete note-taking workflow."""
        session_dir = str(tmp_path / "session")
        os.makedirs(os.path.join(session_dir, "notes"), exist_ok=True)
        ResearchConfig.set_output_dir(session_dir)

        # Save notes
        await _save_note_impl(
            {
                "note_type": "finding",
                "title": "Finding 1",
                "content": "First important finding",
                "source": "paper1.pdf",
            }
        )
        await _save_note_impl(
            {
                "note_type": "finding",
                "title": "Finding 2",
                "content": "Second important finding",
                "source": "paper2.pdf",
            }
        )

        # Read notes
        notes_result = await _read_notes_impl({})
        assert "2 notes" in notes_result["content"][0]["text"]

        # Write report
        await _write_report_impl(
            {
                "title": "Research Summary",
                "executive_summary": "This is a summary of findings.",
                "findings": ["Finding 1", "Finding 2"],
            }
        )

        assert os.path.exists(os.path.join(session_dir, "report.md"))
