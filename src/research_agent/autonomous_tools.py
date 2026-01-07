"""
Autonomous Research Agent Tools

Extended tools for fully autonomous research workflow:
- read_pdf: Extract text from downloaded PDFs
- save_note: Store research findings as structured notes
- read_notes: Retrieve saved notes for synthesis
- write_report: Generate final markdown research report
"""

import json
import os
from datetime import datetime

import pdfplumber
from claude_agent_sdk import create_sdk_mcp_server, tool

# Import existing tools from tools.py
from tools import download_pdfs, web_search

# =============================================================================
# PDF Reading Tool
# =============================================================================


async def _read_pdf_impl(args: dict) -> dict:
    """Extract text content from a PDF file in the papers folder."""
    filename = args["filename"]
    max_pages = args.get("max_pages")

    # Ensure filename is in papers folder
    if not filename.endswith(".pdf"):
        filename = f"{filename}.pdf"

    filepath = os.path.join("papers", filename)

    if not os.path.exists(filepath):
        return {
            "content": [
                {"type": "text", "text": f"Error: PDF file '{filename}' not found in papers folder"}
            ],
            "is_error": True,
        }

    try:
        extracted_text = []
        page_count = 0

        with pdfplumber.open(filepath) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages) if max_pages else total_pages

            for i, page in enumerate(pdf.pages[:pages_to_read]):
                page_count += 1
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {i + 1} ---\n{text}")

        if not extracted_text:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Warning: No text could be extracted from '{filename}'. The PDF may be image-based or encrypted.",
                    }
                ],
            }

        full_text = "\n\n".join(extracted_text)

        # Truncate if extremely long (keep first 50000 chars)
        if len(full_text) > 50000:
            full_text = (
                full_text[:50000]
                + f"\n\n[... Truncated. Total pages: {total_pages}, Read: {page_count} ...]"
            )

        result_text = f"PDF: {filename}\nPages read: {page_count}/{total_pages}\n\n{full_text}"

        return {
            "content": [{"type": "text", "text": result_text}],
        }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error reading PDF '{filename}': {str(e)}. The file may be corrupted or password-protected.",
                }
            ],
            "is_error": True,
        }


read_pdf = tool(
    name="read_pdf",
    description=(
        "Extract and read text content from a downloaded PDF file in the papers folder. "
        "Use this to analyze the content of research papers after downloading them. "
        "Returns the extracted text organized by page."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Name of the PDF file in the papers folder (e.g., '2403.02240.pdf')",
            },
            "max_pages": {
                "type": "integer",
                "description": "Maximum number of pages to read (optional, reads all if not specified)",
            },
        },
        "required": ["filename"],
    },
)(_read_pdf_impl)


# =============================================================================
# Research Notes Tool
# =============================================================================

NOTES_DIR = os.path.join("papers", "notes")


async def _save_note_impl(args: dict) -> dict:
    """Save a research note to the notes folder."""
    note_type = args["note_type"]
    title = args["title"]
    content = args["content"]
    source = args.get("source", "")
    tags = args.get("tags", [])

    # Ensure notes directory exists
    os.makedirs(NOTES_DIR, exist_ok=True)

    # Create note structure
    timestamp = datetime.now().isoformat()
    note = {
        "type": note_type,
        "title": title,
        "content": content,
        "source": source,
        "tags": tags,
        "timestamp": timestamp,
    }

    # Generate filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:50]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{note_type}_{safe_title}.json"
    filepath = os.path.join(NOTES_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(note, f, indent=2, ensure_ascii=False)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Note saved: {filename}\nType: {note_type}\nTitle: {title}",
                }
            ],
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error saving note: {str(e)}"}],
            "is_error": True,
        }


save_note = tool(
    name="save_note",
    description=(
        "Save a research note or finding to track progress during research. "
        "Use this to document key findings, paper summaries, insights, and synthesis points. "
        "Notes are saved as JSON files for later retrieval during report generation."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "note_type": {
                "type": "string",
                "enum": ["finding", "paper_summary", "insight", "synthesis"],
                "description": "Type of note: finding (key fact), paper_summary (paper overview), insight (connection/pattern), synthesis (combined understanding)",
            },
            "title": {
                "type": "string",
                "description": "Brief title for the note",
            },
            "content": {
                "type": "string",
                "description": "The detailed note content",
            },
            "source": {
                "type": "string",
                "description": "Source paper filename or URL (optional)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization (optional)",
            },
        },
        "required": ["note_type", "title", "content"],
    },
)(_save_note_impl)


# =============================================================================
# Read Notes Tool
# =============================================================================


async def _read_notes_impl(args: dict) -> dict:
    """Read all saved research notes."""
    note_type_filter = args.get("note_type", "all")
    tag_filter = args.get("tags", [])

    if not os.path.exists(NOTES_DIR):
        return {
            "content": [
                {"type": "text", "text": "No notes found. The notes folder does not exist yet."}
            ],
        }

    notes = []

    try:
        for filename in sorted(os.listdir(NOTES_DIR)):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(NOTES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                note = json.load(f)

            # Apply filters
            if note_type_filter != "all" and note.get("type") != note_type_filter:
                continue

            if tag_filter:
                note_tags = note.get("tags", [])
                if not any(tag in note_tags for tag in tag_filter):
                    continue

            notes.append(note)

        if not notes:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"No notes found matching filters (type: {note_type_filter}, tags: {tag_filter})",
                    }
                ],
            }

        # Format notes for output
        output_lines = [f"Found {len(notes)} research notes:\n"]

        for i, note in enumerate(notes, 1):
            output_lines.append(f"\n{'='*60}")
            output_lines.append(f"Note {i}: [{note['type'].upper()}] {note['title']}")
            output_lines.append(f"Source: {note.get('source', 'N/A')}")
            output_lines.append(f"Tags: {', '.join(note.get('tags', [])) or 'None'}")
            output_lines.append(f"Time: {note['timestamp']}")
            output_lines.append(f"\n{note['content']}")

        return {
            "content": [{"type": "text", "text": "\n".join(output_lines)}],
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error reading notes: {str(e)}"}],
            "is_error": True,
        }


read_notes = tool(
    name="read_notes",
    description=(
        "Read all saved research notes for synthesis and report generation. "
        "Returns notes organized by type with their full content. "
        "Use this before writing the final report to gather all findings."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "note_type": {
                "type": "string",
                "enum": ["all", "finding", "paper_summary", "insight", "synthesis"],
                "description": "Filter by note type (default: 'all')",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by tags - returns notes with any matching tag (optional)",
            },
        },
    },
)(_read_notes_impl)


# =============================================================================
# Write Report Tool
# =============================================================================


async def _write_report_impl(args: dict) -> dict:
    """Generate and save the final research report."""
    title = args["title"]
    executive_summary = args["executive_summary"]
    findings = args.get("findings", [])
    paper_summaries = args.get("paper_summaries", [])
    methodology = args.get("methodology", "")
    references = args.get("references", [])

    # Generate report content
    timestamp = datetime.now()
    report_lines = [
        f"# Research Report: {title}",
        f"\n*Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
        "\n---\n",
        "## Executive Summary\n",
        executive_summary,
        "\n---\n",
    ]

    # Key Findings
    if findings:
        report_lines.append("## Key Findings\n")
        for i, finding in enumerate(findings, 1):
            report_lines.append(f"{i}. {finding}\n")
        report_lines.append("\n---\n")

    # Paper Summaries
    if paper_summaries:
        report_lines.append("## Paper Summaries\n")
        for summary in paper_summaries:
            if isinstance(summary, dict):
                report_lines.append(f"### {summary.get('title', 'Untitled')}\n")
                report_lines.append(f"**Source:** {summary.get('source', 'N/A')}\n")
                report_lines.append(f"{summary.get('content', '')}\n")
            else:
                report_lines.append(f"{summary}\n")
        report_lines.append("\n---\n")

    # Methodology
    if methodology:
        report_lines.append("## Research Methodology\n")
        report_lines.append(f"{methodology}\n")
        report_lines.append("\n---\n")

    # References
    if references:
        report_lines.append("## References\n")
        for i, ref in enumerate(references, 1):
            report_lines.append(f"{i}. {ref}")
        report_lines.append("\n")

    # Footer
    report_lines.append("\n---\n")
    report_lines.append("*Generated by Autonomous Research Agent*")

    report_content = "\n".join(report_lines)

    # Save report
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:50]
    filename = f"research_report_{safe_title}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join("papers", filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        result_text = f"Report saved successfully!\n\nFile: {filepath}\n\n{'='*60}\nREPORT PREVIEW:\n{'='*60}\n\n{report_content}"

        return {
            "content": [{"type": "text", "text": result_text}],
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error saving report: {str(e)}"}],
            "is_error": True,
        }


write_report = tool(
    name="write_report",
    description=(
        "Generate and save the final research report as a markdown file. "
        "Call this when research is complete to produce the final output. "
        "The report is saved to the papers folder."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the research report",
            },
            "executive_summary": {
                "type": "string",
                "description": "2-3 paragraph summary of key findings and conclusions",
            },
            "findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of key findings (each as a complete sentence)",
            },
            "paper_summaries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                "description": "Summaries of analyzed papers",
            },
            "methodology": {
                "type": "string",
                "description": "Description of research approach and search strategies used",
            },
            "references": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of references/citations",
            },
        },
        "required": ["title", "executive_summary"],
    },
)(_write_report_impl)


# =============================================================================
# Create MCP Server with All Autonomous Tools
# =============================================================================

autonomous_tools_server = create_sdk_mcp_server(
    name="autonomous_research",
    version="1.0.0",
    tools=[
        web_search,  # From tools.py
        download_pdfs,  # From tools.py
        read_pdf,  # New
        save_note,  # New
        read_notes,  # New
        write_report,  # New
    ],
)
