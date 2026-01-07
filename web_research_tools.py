"""
Web Research Tools with Configurable Output Directory

Tools for the web-based autonomous research agent with per-session folder support.
"""

import json
import os
import re
import threading
from datetime import datetime
from urllib.parse import unquote, urlparse

import arxiv
import httpx
import pdfplumber
from claude_agent_sdk import create_sdk_mcp_server, tool
from tavily import TavilyClient

# =============================================================================
# Configuration - Thread-safe output directory management
# =============================================================================


class ResearchConfig:
    """Thread-safe configuration for research sessions."""

    _local = threading.local()
    _default_base_dir = "research_sessions"

    @classmethod
    def set_output_dir(cls, output_dir: str):
        """Set the output directory for the current session."""
        cls._local.output_dir = output_dir
        # Create subdirectories
        os.makedirs(os.path.join(output_dir, "pdfs"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "notes"), exist_ok=True)

    @classmethod
    def get_output_dir(cls) -> str:
        """Get the current output directory."""
        return getattr(cls._local, "output_dir", cls._default_base_dir)

    @classmethod
    def get_pdfs_dir(cls) -> str:
        """Get the PDFs subdirectory."""
        return os.path.join(cls.get_output_dir(), "pdfs")

    @classmethod
    def get_notes_dir(cls) -> str:
        """Get the notes subdirectory."""
        return os.path.join(cls.get_output_dir(), "notes")

    @classmethod
    def create_session_folder(cls, topic: str, base_dir: str = "research_sessions") -> str:
        """Create a new session folder with timestamp and topic."""
        os.makedirs(base_dir, exist_ok=True)

        # Create safe folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)[:50]
        folder_name = f"{timestamp}_{safe_topic}"

        output_dir = os.path.join(base_dir, folder_name)
        cls.set_output_dir(output_dir)

        return output_dir


# =============================================================================
# Web Search Tool
# =============================================================================


def _is_pdf_url(url: str) -> bool:
    """Check if a URL likely points to a PDF document."""
    url_lower = url.lower()
    if url_lower.endswith(".pdf"):
        return True
    pdf_patterns = [r"\.pdf\?", r"\.pdf#", r"/pdf/", r"arxiv\.org/pdf/", r"download.*pdf"]
    return any(re.search(pattern, url_lower) for pattern in pdf_patterns)


async def _web_search_impl(args: dict) -> dict:
    """Search for research papers using Tavily API."""
    query = args["query"]
    max_results = args.get("max_results", 10)

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "content": [{"type": "text", "text": "Error: TAVILY_API_KEY not set"}],
            "is_error": True,
        }

    try:
        client = TavilyClient(api_key=api_key)
        enhanced_query = f"{query} research paper PDF academic"

        include_domains = [
            "arxiv.org",
            "scholar.google.com",
            "pubmed.ncbi.nlm.nih.gov",
            "ncbi.nlm.nih.gov",
            "sciencedirect.com",
            "nature.com",
            "science.org",
            "ieee.org",
            "acm.org",
            "researchgate.net",
            "semanticscholar.org",
            "biorxiv.org",
            "medrxiv.org",
            "plos.org",
            "frontiersin.org",
            "mdpi.com",
            "springer.com",
            "wiley.com",
            "cell.com",
        ]

        response = client.search(
            query=enhanced_query,
            max_results=max_results,
            search_depth="advanced",
            include_domains=include_domains,
        )

        results = response.get("results", [])
        pdf_urls = [r.get("url", "") for r in results if _is_pdf_url(r.get("url", ""))]

        output_lines = [f"Found {len(results)} results for: {query}\n"]
        if pdf_urls:
            output_lines.append(f"PDF URLs found: {len(pdf_urls)}\n")

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:200]
            is_pdf = "📄 [PDF]" if url in pdf_urls else ""
            output_lines.extend([f"\n{i}. {title} {is_pdf}", f"   URL: {url}", f"   {content}..."])

        if pdf_urls:
            output_lines.append("\n\nPDF URLs for download:")
            output_lines.extend(f"  - {url}" for url in pdf_urls)

        return {"content": [{"type": "text", "text": "\n".join(output_lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Search error: {str(e)}"}], "is_error": True}


web_search = tool(
    name="web_search",
    description="Search the web for research papers and academic articles on a topic.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Maximum results (default: 10)"},
        },
        "required": ["query"],
    },
)(_web_search_impl)


# =============================================================================
# ArXiv Search Tool
# =============================================================================


async def _arxiv_search_impl(args: dict) -> dict:
    """Search ArXiv for academic papers."""
    query = args["query"]
    max_results = args.get("max_results", 10)
    sort_by = args.get("sort_by", "relevance")
    category = args.get("category", None)

    try:
        # Build search query
        search_query = query
        if category:
            search_query = f"cat:{category} AND {query}"

        # Configure sort order
        sort_criterion = arxiv.SortCriterion.Relevance
        if sort_by == "date":
            sort_criterion = arxiv.SortCriterion.SubmittedDate
        elif sort_by == "citations":
            sort_criterion = arxiv.SortCriterion.Relevance  # ArXiv doesn't have citation sort

        # Create search client
        client = arxiv.Client()
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=sort_criterion,
            sort_order=arxiv.SortOrder.Descending,
        )

        # Fetch results
        results = list(client.results(search))

        if not results:
            return {"content": [{"type": "text", "text": f"No ArXiv papers found for: {query}"}]}

        output_lines = [
            f"Found {len(results)} ArXiv papers for: {query}\n",
            "=" * 60,
        ]

        paper_data = []
        for i, paper in enumerate(results, 1):
            # Get PDF URL (ArXiv always has PDFs)
            pdf_url = paper.pdf_url

            # Format authors (limit to first 3)
            authors = [a.name for a in paper.authors[:3]]
            if len(paper.authors) > 3:
                authors.append(f"et al. (+{len(paper.authors) - 3} more)")
            authors_str = ", ".join(authors)

            # Format categories
            categories = ", ".join(paper.categories[:3])

            # Format date
            pub_date = paper.published.strftime("%Y-%m-%d")

            # Truncate abstract
            abstract = paper.summary.replace("\n", " ")[:300]
            if len(paper.summary) > 300:
                abstract += "..."

            paper_info = {
                "title": paper.title,
                "authors": authors_str,
                "pdf_url": pdf_url,
                "arxiv_id": paper.entry_id.split("/")[-1],
                "categories": categories,
                "published": pub_date,
            }
            paper_data.append(paper_info)

            output_lines.extend(
                [
                    f"\n{i}. {paper.title}",
                    f"   Authors: {authors_str}",
                    f"   ArXiv ID: {paper_info['arxiv_id']}",
                    f"   Categories: {categories}",
                    f"   Published: {pub_date}",
                    f"   📄 PDF: {pdf_url}",
                    f"   Abstract: {abstract}",
                ]
            )

        # Add summary of PDF URLs for easy downloading
        output_lines.extend(
            [
                "\n" + "=" * 60,
                "\n📥 PDF URLs for download:",
            ]
        )
        for paper in paper_data:
            output_lines.append(f"  - {paper['pdf_url']}")

        return {"content": [{"type": "text", "text": "\n".join(output_lines)}]}

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"ArXiv search error: {str(e)}"}],
            "is_error": True,
        }


arxiv_search = tool(
    name="arxiv_search",
    description="Search ArXiv for academic papers. ArXiv is the primary repository for preprints in physics, mathematics, computer science, and related fields. Use this for finding cutting-edge research papers with guaranteed PDF access.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'transformer attention mechanism', 'large language models')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 10, max: 50)",
            },
            "sort_by": {
                "type": "string",
                "enum": ["relevance", "date"],
                "description": "Sort results by relevance or submission date (default: relevance)",
            },
            "category": {
                "type": "string",
                "description": "ArXiv category filter (e.g., 'cs.AI', 'cs.LG', 'cs.CL', 'stat.ML', 'physics')",
            },
        },
        "required": ["query"],
    },
)(_arxiv_search_impl)


# =============================================================================
# PDF Download Tool
# =============================================================================


def _extract_filename_from_url(url: str) -> str:
    """Extract a filename from URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = os.path.basename(path)

    if not filename or not filename.lower().endswith(".pdf"):
        parts = [p for p in path.split("/") if p]
        if parts:
            filename = f"{parts[-1]}.pdf"
        else:
            import hashlib

            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{parsed.netloc}_{url_hash}.pdf"

    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename[:200]


async def _download_single_pdf(url: str, output_dir: str) -> dict:
    """Download a single PDF file."""
    filename = _extract_filename_from_url(url)
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        return {
            "success": True,
            "url": url,
            "filepath": filepath,
            "filename": filename,
            "skipped": True,
        }

    try:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                if response.content[:4] != b"%PDF":
                    return {
                        "success": False,
                        "url": url,
                        "filename": filename,
                        "error": "Not a PDF",
                    }

            with open(filepath, "wb") as f:
                f.write(response.content)

            return {
                "success": True,
                "url": url,
                "filepath": filepath,
                "filename": filename,
                "file_size_bytes": len(response.content),
                "file_size_mb": round(len(response.content) / (1024 * 1024), 2),
            }

    except httpx.TimeoutException:
        return {"success": False, "url": url, "filename": filename, "error": "Timeout"}
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "url": url,
            "filename": filename,
            "error": f"HTTP {e.response.status_code}",
        }
    except Exception as e:
        return {"success": False, "url": url, "filename": filename, "error": str(e)}


async def _download_pdfs_impl(args: dict) -> dict:
    """Download PDFs to the session's pdfs folder."""
    urls = args["urls"]
    output_dir = ResearchConfig.get_pdfs_dir()

    if not urls:
        return {"content": [{"type": "text", "text": "No URLs provided"}]}

    os.makedirs(output_dir, exist_ok=True)

    results = []
    successful, failed, skipped = 0, 0, 0

    for url in urls:
        result = await _download_single_pdf(url, output_dir)
        results.append(result)
        if result["success"]:
            skipped += 1 if result.get("skipped") else 0
            successful += 0 if result.get("skipped") else 1
        else:
            failed += 1

    output_lines = [
        "Download Summary:",
        f"  Total: {len(urls)}, Successful: {successful}, Failed: {failed}, Skipped: {skipped}",
        f"  Output folder: {output_dir}/",
        "",
        "Details:",
    ]

    for result in results:
        if result["success"]:
            status = "⏭️" if result.get("skipped") else "✅"
            suffix = (
                "(already exists)"
                if result.get("skipped")
                else f"({result.get('file_size_mb', 0)} MB)"
            )
            output_lines.append(f"  {status} {result['filename']} {suffix}")
        else:
            output_lines.append(f"  ❌ {result.get('filename', 'unknown')}: {result.get('error')}")

    return {"content": [{"type": "text", "text": "\n".join(output_lines)}]}


download_pdfs = tool(
    name="download_pdfs",
    description="Download PDF files from URLs to the session's pdfs folder.",
    input_schema={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "PDF URLs to download",
            },
        },
        "required": ["urls"],
    },
)(_download_pdfs_impl)


# =============================================================================
# PDF Reading Tool
# =============================================================================


async def _read_pdf_impl(args: dict) -> dict:
    """Extract text from a PDF in the session's pdfs folder."""
    filename = args["filename"]
    max_pages = args.get("max_pages")

    if not filename.endswith(".pdf"):
        filename = f"{filename}.pdf"

    filepath = os.path.join(ResearchConfig.get_pdfs_dir(), filename)

    if not os.path.exists(filepath):
        return {
            "content": [{"type": "text", "text": f"Error: '{filename}' not found"}],
            "is_error": True,
        }

    try:
        extracted_text = []
        with pdfplumber.open(filepath) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages) if max_pages else total_pages

            for i, page in enumerate(pdf.pages[:pages_to_read]):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- Page {i + 1} ---\n{text}")

        if not extracted_text:
            return {
                "content": [
                    {"type": "text", "text": f"Warning: No text extracted from '{filename}'"}
                ]
            }

        full_text = "\n\n".join(extracted_text)
        if len(full_text) > 50000:
            full_text = full_text[:50000] + "\n\n[... Truncated ...]"

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"PDF: {filename}\nPages: {len(extracted_text)}/{total_pages}\n\n{full_text}",
                }
            ]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error reading '{filename}': {str(e)}"}],
            "is_error": True,
        }


read_pdf = tool(
    name="read_pdf",
    description="Extract text from a downloaded PDF file.",
    input_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "PDF filename"},
            "max_pages": {"type": "integer", "description": "Max pages to read"},
        },
        "required": ["filename"],
    },
)(_read_pdf_impl)


# =============================================================================
# Research Notes Tools
# =============================================================================


async def _save_note_impl(args: dict) -> dict:
    """Save a research note to the session's notes folder."""
    note_type = args["note_type"]
    title = args["title"]
    content = args["content"]
    source = args.get("source", "")
    tags = args.get("tags", [])

    notes_dir = ResearchConfig.get_notes_dir()
    os.makedirs(notes_dir, exist_ok=True)

    note = {
        "type": note_type,
        "title": title,
        "content": content,
        "source": source,
        "tags": tags,
        "timestamp": datetime.now().isoformat(),
    }

    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:50]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{note_type}_{safe_title}.json"
    filepath = os.path.join(notes_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(note, f, indent=2, ensure_ascii=False)
        return {"content": [{"type": "text", "text": f"Note saved: {filename}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "is_error": True}


save_note = tool(
    name="save_note",
    description="Save a research note or finding.",
    input_schema={
        "type": "object",
        "properties": {
            "note_type": {
                "type": "string",
                "enum": ["finding", "paper_summary", "insight", "synthesis"],
            },
            "title": {"type": "string"},
            "content": {"type": "string"},
            "source": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["note_type", "title", "content"],
    },
)(_save_note_impl)


async def _read_notes_impl(args: dict) -> dict:
    """Read all saved research notes."""
    note_type_filter = args.get("note_type", "all")
    notes_dir = ResearchConfig.get_notes_dir()

    if not os.path.exists(notes_dir):
        return {"content": [{"type": "text", "text": "No notes found."}]}

    notes = []
    for filename in sorted(os.listdir(notes_dir)):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(notes_dir, filename), "r", encoding="utf-8") as f:
            note = json.load(f)
        if note_type_filter == "all" or note.get("type") == note_type_filter:
            notes.append(note)

    if not notes:
        return {"content": [{"type": "text", "text": "No matching notes found."}]}

    output_lines = [f"Found {len(notes)} notes:\n"]
    for i, note in enumerate(notes, 1):
        output_lines.extend(
            [
                f"\n{'='*60}",
                f"Note {i}: [{note['type'].upper()}] {note['title']}",
                f"Source: {note.get('source', 'N/A')}",
                f"\n{note['content']}",
            ]
        )

    return {"content": [{"type": "text", "text": "\n".join(output_lines)}]}


read_notes = tool(
    name="read_notes",
    description="Read all saved research notes for synthesis.",
    input_schema={
        "type": "object",
        "properties": {
            "note_type": {
                "type": "string",
                "enum": ["all", "finding", "paper_summary", "insight", "synthesis"],
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

    timestamp = datetime.now()
    report_lines = [
        f"# Research Report: {title}",
        f"\n*Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
        "\n---\n",
        "## Executive Summary\n",
        executive_summary,
        "\n---\n",
    ]

    if findings:
        report_lines.append("## Key Findings\n")
        report_lines.extend(f"{i}. {f}\n" for i, f in enumerate(findings, 1))
        report_lines.append("\n---\n")

    if paper_summaries:
        report_lines.append("## Paper Summaries\n")
        for s in paper_summaries:
            if isinstance(s, dict):
                report_lines.extend(
                    [
                        f"### {s.get('title', 'Untitled')}\n",
                        f"**Source:** {s.get('source', 'N/A')}\n",
                        f"{s.get('content', '')}\n",
                    ]
                )
            else:
                report_lines.append(f"{s}\n")
        report_lines.append("\n---\n")

    if methodology:
        report_lines.extend(["## Research Methodology\n", f"{methodology}\n", "\n---\n"])

    if references:
        report_lines.append("## References\n")
        report_lines.extend(f"{i}. {r}" for i, r in enumerate(references, 1))
        report_lines.append("\n")

    report_lines.extend(["\n---\n", "*Generated by Autonomous Research Agent*"])
    report_content = "\n".join(report_lines)

    # Save to session folder root
    output_dir = ResearchConfig.get_output_dir()
    filename = "report.md"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        return {
            "content": [{"type": "text", "text": f"Report saved: {filepath}\n\n{report_content}"}]
        }
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "is_error": True}


write_report = tool(
    name="write_report",
    description="Generate and save the final research report.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "executive_summary": {"type": "string"},
            "findings": {"type": "array", "items": {"type": "string"}},
            "paper_summaries": {"type": "array", "items": {"type": "object"}},
            "methodology": {"type": "string"},
            "references": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "executive_summary"],
    },
)(_write_report_impl)


# =============================================================================
# Create MCP Server
# =============================================================================

web_research_tools_server = create_sdk_mcp_server(
    name="web_research",
    version="1.1.0",
    tools=[
        web_search,
        arxiv_search,
        download_pdfs,
        read_pdf,
        save_note,
        read_notes,
        write_report,
    ],
)
