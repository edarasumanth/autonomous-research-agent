"""
Tests for email_service module.
"""

import pytest

from email_service import DEFAULT_SENDER_EMAIL, EmailConfig, create_email_html, markdown_to_html


class TestEmailConfig:
    """Tests for EmailConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EmailConfig()
        assert config.enabled is False
        assert config.smtp_host == "smtp.gmail.com"
        assert config.smtp_port == 587
        assert config.smtp_user == ""
        assert config.smtp_password == ""
        assert config.email_from == DEFAULT_SENDER_EMAIL

    def test_default_sender_email(self):
        """Test that default sender email is set correctly."""
        assert DEFAULT_SENDER_EMAIL == "edarasumanth@gmail.com"

    def test_is_valid_when_incomplete(self):
        """Test that incomplete config is not valid."""
        config = EmailConfig(smtp_host="smtp.gmail.com")
        assert config.is_valid() is False

    def test_is_valid_when_complete(self):
        """Test that complete config is valid (excludes recipient)."""
        config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="password123",
            email_from="user@gmail.com",
        )
        assert config.is_valid() is True

    def test_is_smtp_configured_when_missing_settings(self):
        """Test that SMTP is not configured when settings are missing."""
        config = EmailConfig(smtp_host="smtp.gmail.com")
        assert config.is_smtp_configured() is False

    def test_is_smtp_configured_when_complete(self):
        """Test that SMTP is configured when all required settings are present."""
        config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_user="user@gmail.com",
            smtp_password="password123",
        )
        assert config.is_smtp_configured() is True


class TestMarkdownToHtml:
    """Tests for markdown to HTML conversion."""

    def test_headers(self):
        """Test header conversion."""
        result = markdown_to_html("# Heading 1")
        assert "<h1" in result
        assert "Heading 1" in result

        result = markdown_to_html("## Heading 2")
        assert "<h2" in result

        result = markdown_to_html("### Heading 3")
        assert "<h3" in result

    def test_bold_text(self):
        """Test bold text conversion."""
        result = markdown_to_html("This is **bold** text")
        assert "<strong>bold</strong>" in result

    def test_italic_text(self):
        """Test italic text conversion."""
        result = markdown_to_html("This is *italic* text")
        assert "<em>italic</em>" in result

    def test_inline_code(self):
        """Test inline code conversion."""
        result = markdown_to_html("Use `code` here")
        assert "<code" in result
        assert "code" in result

    def test_links(self):
        """Test link conversion."""
        result = markdown_to_html("[Click here](https://example.com)")
        assert '<a href="https://example.com"' in result
        assert "Click here" in result

    def test_horizontal_rule(self):
        """Test horizontal rule conversion."""
        result = markdown_to_html("---")
        assert "<hr" in result

    def test_unordered_list(self):
        """Test unordered list conversion."""
        result = markdown_to_html("- Item 1\n- Item 2")
        assert "<li" in result
        assert "Item 1" in result
        assert "Item 2" in result


class TestCreateEmailHtml:
    """Tests for creating complete HTML email."""

    def test_creates_html_document(self):
        """Test that complete HTML document is created."""
        result = create_email_html("# Test Report\n\nSome content", "Test Topic")
        assert "<!DOCTYPE html>" in result
        assert "<html>" in result
        assert "</html>" in result

    def test_includes_topic(self):
        """Test that topic is included in email."""
        result = create_email_html("Content", "My Research Topic")
        assert "My Research Topic" in result

    def test_includes_content(self):
        """Test that report content is included."""
        result = create_email_html("## Key Findings\n\nImportant results", "Topic")
        assert "Key Findings" in result
        assert "Important results" in result

    def test_includes_styling(self):
        """Test that email includes styling."""
        result = create_email_html("Content", "Topic")
        assert "style=" in result
        assert "font-family" in result

    def test_includes_branding(self):
        """Test that email includes Research Agent branding."""
        result = create_email_html("Content", "Topic")
        assert "Research" in result
