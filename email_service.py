"""
Email Service for Research Agent

Sends research reports via SMTP email when research completes.
Uses Python stdlib only (smtplib, email.mime).
"""

import logging
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# Default sender email for the research agent
DEFAULT_SENDER_EMAIL = "edarasumanth@gmail.com"


@dataclass
class EmailConfig:
    """Email configuration for sending reports."""

    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = DEFAULT_SENDER_EMAIL
    email_to: str = ""

    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Load email configuration from environment variables."""
        return cls(
            enabled=os.getenv("EMAIL_ENABLED", "false").lower() == "true",
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            email_from=os.getenv("EMAIL_FROM", DEFAULT_SENDER_EMAIL),
            email_to=os.getenv("EMAIL_TO", ""),
        )

    def is_valid(self) -> bool:
        """Check if email configuration is complete (excluding recipient)."""
        return all(
            [
                self.smtp_host,
                self.smtp_user,
                self.smtp_password,
                self.email_from,
            ]
        )

    def is_smtp_configured(self) -> bool:
        """Check if SMTP settings are configured for sending emails."""
        return all(
            [
                self.smtp_host,
                self.smtp_user,
                self.smtp_password,
            ]
        )


def markdown_to_html(markdown_content: str) -> str:
    """
    Convert markdown to basic HTML for email.

    Handles:
    - Headers (h1-h4)
    - Bold and italic
    - Code blocks and inline code
    - Lists (unordered and ordered)
    - Links
    - Horizontal rules
    - Paragraphs
    """
    html = markdown_content

    # Escape HTML entities first
    html = html.replace("&", "&amp;")
    html = html.replace("<", "&lt;")
    html = html.replace(">", "&gt;")

    # Code blocks (must be before other formatting)
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        r'<pre style="background: #f4f4f4; padding: 12px; border-radius: 4px; '
        r'overflow-x: auto; font-family: monospace;"><code>\2</code></pre>',
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(
        r"`([^`]+)`",
        r'<code style="background: #f4f4f4; padding: 2px 6px; border-radius: 3px; '
        r'font-family: monospace;">\1</code>',
        html,
    )

    # Headers
    html = re.sub(
        r"^#### (.+)$",
        r'<h4 style="color: #333; margin: 16px 0 8px 0;">\1</h4>',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^### (.+)$",
        r'<h3 style="color: #333; margin: 20px 0 10px 0;">\1</h3>',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^## (.+)$",
        r'<h2 style="color: #333; margin: 24px 0 12px 0;">\1</h2>',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^# (.+)$",
        r'<h1 style="color: #333; margin: 28px 0 14px 0;">\1</h1>',
        html,
        flags=re.MULTILINE,
    )

    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links
    html = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color: #667eea;">\1</a>',
        html,
    )

    # Horizontal rules
    html = re.sub(
        r"^---+$",
        r'<hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">',
        html,
        flags=re.MULTILINE,
    )

    # Unordered lists
    html = re.sub(
        r"^- (.+)$",
        r'<li style="margin: 4px 0;">\1</li>',
        html,
        flags=re.MULTILINE,
    )

    # Ordered lists
    html = re.sub(
        r"^\d+\. (.+)$",
        r'<li style="margin: 4px 0;">\1</li>',
        html,
        flags=re.MULTILINE,
    )

    # Wrap consecutive list items in <ul> or <ol>
    html = re.sub(
        r"((?:<li[^>]*>.*?</li>\n?)+)",
        r'<ul style="padding-left: 24px; margin: 12px 0;">\1</ul>',
        html,
    )

    # Paragraphs - wrap remaining text blocks
    lines = html.split("\n")
    result = []
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_block:
                result.append("</p>")
                in_block = False
            result.append("")
        elif stripped.startswith("<"):
            if in_block:
                result.append("</p>")
                in_block = False
            result.append(line)
        else:
            if not in_block:
                result.append('<p style="margin: 12px 0; line-height: 1.6;">')
                in_block = True
            result.append(line)

    if in_block:
        result.append("</p>")

    html = "\n".join(result)

    return html


def create_email_html(report_content: str, topic: str) -> str:
    """Create a complete HTML email with styling."""
    report_html = markdown_to_html(report_content)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
             max-width: 800px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9;">

    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px;">
        <h1 style="margin: 0; font-size: 24px;">Research Report</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">{topic}</p>
    </div>

    <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        {report_html}
    </div>

    <div style="text-align: center; margin-top: 24px; color: #666; font-size: 14px;">
        <p>Generated by Autonomous Research Agent</p>
    </div>
</body>
</html>"""


def send_email_report(
    report_content: str,
    topic: str,
    recipient: str,
    config: EmailConfig | None = None,
) -> tuple[bool, str]:
    """
    Send a research report via email.

    Args:
        report_content: Markdown content of the research report
        topic: Research topic (used in subject line)
        recipient: Recipient email address (required)
        config: Email configuration (loads from env if None)

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not recipient or not recipient.strip():
        return False, "No recipient email specified"

    # Basic email validation
    if "@" not in recipient or "." not in recipient:
        return False, "Invalid email address format"

    recipient = recipient.strip()

    if config is None:
        config = EmailConfig.from_env()

    if not config.is_smtp_configured():
        return False, "SMTP settings are not configured. Please configure SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env"

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Research Report: {topic[:50]}"
        msg["From"] = config.email_from or DEFAULT_SENDER_EMAIL
        msg["To"] = recipient

        # Plain text version
        text_part = MIMEText(report_content, "plain", "utf-8")

        # HTML version
        html_content = create_email_html(report_content, topic)
        html_part = MIMEText(html_content, "html", "utf-8")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        context = ssl.create_default_context()
        sender = config.email_from or DEFAULT_SENDER_EMAIL

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls(context=context)
            server.login(config.smtp_user, config.smtp_password)
            server.sendmail(sender, recipient, msg.as_string())

        logger.info(f"Email sent successfully to {recipient}")
        return True, f"Report sent to {recipient}"

    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP authentication failed. Check your email credentials."
        logger.error(error_msg)
        return False, error_msg

    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def test_email_connection(config: EmailConfig | None = None) -> tuple[bool, str]:
    """
    Test SMTP connection without sending an email.

    Returns:
        Tuple of (success: bool, message: str)
    """
    if config is None:
        config = EmailConfig.from_env()

    if not config.is_smtp_configured():
        return False, "SMTP settings are not configured"

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls(context=context)
            server.login(config.smtp_user, config.smtp_password)

        return True, "SMTP connection successful"

    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your credentials."

    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"

    except Exception as e:
        return False, f"Connection failed: {str(e)}"
