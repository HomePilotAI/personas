"""PDF ingestion safety checks.

Each guard is a small pure function that raises ``ValueError`` on policy
breach so callers can surface a typed envelope instead of crashing the MCP
transport. The guards are exercised both inline (paper_reader) and via the
test suite — there is no "trust the upstream toolkit" path.
"""

from __future__ import annotations

from pathlib import Path

# Defensive defaults; the live values come from ResearcherConfig.
_PDF_MAGIC = b"%PDF-"


def ensure_pdf_size(path: Path, max_mb: int) -> None:
    """Reject PDFs larger than the configured cap."""
    size = path.stat().st_size
    max_bytes = max_mb * 1024 * 1024
    if size > max_bytes:
        raise ValueError(f"PDF exceeds max size: {size} bytes > {max_bytes} bytes ({max_mb} MB)")


def ensure_pdf_page_limit(page_count: int, max_pages: int) -> None:
    """Reject PDFs with more pages than the configured cap."""
    if page_count > max_pages:
        raise ValueError(f"PDF exceeds max pages: {page_count} > {max_pages}")


def ensure_pdf_magic(path: Path) -> None:
    """Reject files that don't begin with the PDF magic bytes.

    A reachable PDF endpoint that returns HTML or a redirect-to-login page
    is the most common wedge for "invisible" download failures. We surface
    it as a clean policy error rather than letting pypdf raise an opaque
    exception 100 lines later.
    """
    with path.open("rb") as fh:
        head = fh.read(8)
    if not head.startswith(_PDF_MAGIC):
        raise ValueError(f"file at {path} is not a valid PDF (bad magic bytes)")


def ensure_pdf_text_cap(text: str, max_chars: int) -> str:
    """Truncate extracted PDF text to the configured cap.

    Returns the (possibly-truncated) text; the caller decides whether to
    record `full_text_truncated=true` in the response envelope.
    """
    if len(text) > max_chars:
        return text[:max_chars]
    return text


__all__ = [
    "ensure_pdf_size",
    "ensure_pdf_page_limit",
    "ensure_pdf_magic",
    "ensure_pdf_text_cap",
]
