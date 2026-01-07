"""
Custom Tools for Research Agent

Tools for web search and PDF downloading using Claude Agent SDK's @tool decorator.
"""

import os
import re
import asyncio
import json
from typing import Optional
from urllib.parse import urlparse, unquote

import httpx
from tavily import TavilyClient

from claude_agent_sdk import tool, create_sdk_mcp_server


# =============================================================================
# Tavily Search Tool
# =============================================================================

async def _web_search_impl(args: dict) -> dict:
    """Search for research papers and articles using Tavily API."""
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

        # Enhance query for research/academic focus
        enhanced_query = f"{query} research paper PDF academic"

        # Academic domains
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

        # Identify PDF URLs
        pdf_urls = []
        for result in results:
            url = result.get("url", "")
            if _is_pdf_url(url):
                pdf_urls.append(url)

        # Format output
        output_lines = [f"Found {len(results)} results for: {query}\n"]

        if pdf_urls:
            output_lines.append(f"PDF URLs found: {len(pdf_urls)}\n")

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:200]
            is_pdf = "📄 [PDF]" if url in pdf_urls else ""

            output_lines.append(f"\n{i}. {title} {is_pdf}")
            output_lines.append(f"   URL: {url}")
            output_lines.append(f"   {content}...")

        if pdf_urls:
            output_lines.append(f"\n\nPDF URLs for download:")
            for url in pdf_urls:
                output_lines.append(f"  - {url}")

        return {
            "content": [{"type": "text", "text": "\n".join(output_lines)}],
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Search error: {str(e)}"}],
            "is_error": True,
        }


# Create the decorated tool
web_search = tool(
    name="web_search",
    description=(
        "Search the web for research papers, academic articles, and PDFs on a topic. "
        "Uses Tavily API to find relevant content from credible academic sources like "
        "arXiv, PubMed, Nature, IEEE, and more. Returns search results including "
        "titles, URLs, content snippets, and identifies PDF links."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query for finding research papers and articles",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10)",
            },
        },
        "required": ["query"],
    },
)(_web_search_impl)


def _is_pdf_url(url: str) -> bool:
    """Check if a URL likely points to a PDF document."""
    url_lower = url.lower()

    if url_lower.endswith(".pdf"):
        return True

    pdf_patterns = [
        r"\.pdf\?",
        r"\.pdf#",
        r"/pdf/",
        r"arxiv\.org/pdf/",
        r"download.*pdf",
    ]

    for pattern in pdf_patterns:
        if re.search(pattern, url_lower):
            return True

    return False


# =============================================================================
# PDF Downloader Tool
# =============================================================================

async def _download_pdfs_impl(args: dict) -> dict:
    """Download PDFs from a list of URLs."""
    urls = args["urls"]
    output_dir = "papers"

    if not urls:
        return {
            "content": [{"type": "text", "text": "No URLs provided to download"}],
        }

    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    results = []
    successful = 0
    failed = 0
    skipped = 0

    for url in urls:
        result = await _download_single_pdf(url, output_dir)
        results.append(result)

        if result["success"]:
            if result.get("skipped"):
                skipped += 1
            else:
                successful += 1
        else:
            failed += 1

    # Format output
    output_lines = [
        f"Download Summary:",
        f"  Total: {len(urls)}",
        f"  Successful: {successful}",
        f"  Failed: {failed}",
        f"  Skipped (already exists): {skipped}",
        f"  Output folder: {output_dir}/",
        "",
        "Details:",
    ]

    for result in results:
        if result["success"]:
            if result.get("skipped"):
                output_lines.append(f"  ⏭️  {result['filename']} (already exists)")
            else:
                size_mb = result.get("file_size_mb", 0)
                output_lines.append(f"  ✅ {result['filename']} ({size_mb} MB)")
        else:
            output_lines.append(f"  ❌ {result.get('filename', 'unknown')}: {result.get('error', 'Unknown error')}")

    return {
        "content": [{"type": "text", "text": "\n".join(output_lines)}],
    }


# Create the decorated tool
download_pdfs = tool(
    name="download_pdfs",
    description=(
        "Download PDF files from a list of URLs and save them to the local 'papers' folder. "
        "Use this after web_search to download the PDF files found. "
        "Returns download status for each URL including success/failure and file paths."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of PDF URLs to download",
            },
        },
        "required": ["urls"],
    },
)(_download_pdfs_impl)


async def _download_single_pdf(url: str, output_dir: str) -> dict:
    """Download a single PDF file."""
    filename = _extract_filename_from_url(url)
    filepath = os.path.join(output_dir, filename)

    # Skip if exists
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
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Verify it's a PDF
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                if not response.content[:4] == b"%PDF":
                    return {
                        "success": False,
                        "url": url,
                        "filename": filename,
                        "error": f"Not a PDF (content-type: {content_type})",
                    }

            with open(filepath, "wb") as f:
                f.write(response.content)

            file_size = len(response.content)

            return {
                "success": True,
                "url": url,
                "filepath": filepath,
                "filename": filename,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
            }

    except httpx.TimeoutException:
        return {"success": False, "url": url, "filename": filename, "error": "Timeout"}
    except httpx.HTTPStatusError as e:
        return {"success": False, "url": url, "filename": filename, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "url": url, "filename": filename, "error": str(e)}


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

    # Sanitize
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    return filename[:200] if len(filename) > 200 else filename


# =============================================================================
# Create MCP Server with Tools
# =============================================================================

research_tools_server = create_sdk_mcp_server(
    name="research_tools",
    version="1.0.0",
    tools=[web_search, download_pdfs],
)


def list_downloaded_pdfs(output_dir: str = "papers") -> list[str]:
    """List all PDFs in the output directory."""
    if not os.path.exists(output_dir):
        return []
    return [f for f in os.listdir(output_dir) if f.lower().endswith(".pdf")]
