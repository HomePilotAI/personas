"""Paper reader: fetch arXiv metadata, optionally download + extract PDF text.

Every PDF download passes through:

  1. ``source_policy.is_allowed_pdf_source`` — refuses pirated mirrors,
     SSRF targets, non-http(s) schemes, and unknown hosts.
  2. ``pdf_guard.ensure_pdf_size`` — refuses files larger than the
     configured ``MAX_PDF_MB`` cap.
  3. ``pdf_guard.ensure_pdf_magic`` — refuses files that don't start with
     ``%PDF-`` (catches HTML login pages, redirect bodies, etc.).
  4. ``pdf_guard.ensure_pdf_page_limit`` — refuses files over
     ``MAX_PDF_PAGES``.
  5. ``pdf_guard.ensure_pdf_text_cap`` — truncates extracted text to
     ``MAX_PDF_TEXT_CHARS`` and records ``full_text_truncated=True``.

Every successful read carries a :class:`Provenance` block with the
upstream URL hash and source tag so the audit log can trace evidence
back to its origin without storing raw user text.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .arxiv_client import normalize_paper_id
from .models import PaperContent, PaperRef, Provenance
from .pdf_guard import (
    ensure_pdf_magic,
    ensure_pdf_page_limit,
    ensure_pdf_size,
    ensure_pdf_text_cap,
)
from .source_policy import is_allowed_pdf_source

if TYPE_CHECKING:  # pragma: no cover
    pass

log = logging.getLogger("mcp-researcher.paper")

_DOWNLOAD_CHUNK = 64 * 1024


def _safe_filename(paper_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id) + ".pdf"


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch_metadata(paper_id: str, *, timeout_s: int = 30) -> PaperRef:
    """Look up a single arXiv paper by ID."""
    try:
        import arxiv  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'arxiv' Python package is required for read_paper. "
            "Install it with `pip install arxiv`."
        ) from exc

    canonical = normalize_paper_id(paper_id)
    base_id = canonical.split("v")[0] if re.match(r"^\d{4}\.\d{4,5}v\d+$", canonical) else canonical
    log.info("read_paper id=%s (canonical=%s base=%s)", paper_id, canonical, base_id)

    search = arxiv.Search(id_list=[base_id])
    client = arxiv.Client(page_size=1, delay_seconds=3.0, num_retries=3)
    results = list(client.results(search))
    if not results:
        raise LookupError(f"arXiv returned no result for id={paper_id!r}")

    from .arxiv_client import _to_paper_ref  # local import to avoid cycle

    return _to_paper_ref(results[0])


def download_pdf(
    pdf_url: str,
    *,
    cache_dir: Path,
    paper_id: str,
    max_mb: int = 50,
    timeout_s: int = 60,
) -> Path:
    """Download (or reuse cached) PDF for ``pdf_url`` and return the local path."""
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'httpx' package is required for PDF download. "
            "Install it with `pip install httpx`."
        ) from exc

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / _safe_filename(paper_id)
    if target.exists() and target.stat().st_size > 0:
        log.info("pdf cache hit %s (%d bytes)", target, target.stat().st_size)
        return target

    max_bytes = max_mb * 1024 * 1024
    log.info("downloading pdf %s -> %s (cap=%dMB)", pdf_url, target, max_mb)
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        with client.stream("GET", pdf_url) as resp:
            resp.raise_for_status()
            written = 0
            with target.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=_DOWNLOAD_CHUNK):
                    fh.write(chunk)
                    written += len(chunk)
                    if written > max_bytes:
                        fh.close()
                        target.unlink(missing_ok=True)
                        raise ValueError(
                            f"PDF for {paper_id} exceeded MAX_PDF_MB={max_mb}; download aborted."
                        )
    log.info("downloaded %d bytes -> %s", written, target)
    return target


def extract_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pypdf, joining pages with double newlines."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'pypdf' package is required for full-text extraction. "
            "Install it with `pip install pypdf`."
        ) from exc

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover
            log.warning("could not decrypt %s: %s", pdf_path, exc)
            return ""

    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover
            log.warning("page extract error in %s: %s", pdf_path, exc)
            text = ""
        text = text.strip()
        if text:
            parts.append(text)
    joined = "\n\n".join(parts)
    return re.sub(r"\n{3,}", "\n\n", joined)


def _page_count(pdf_path: Path) -> int:
    """Return the page count of a PDF without extracting text."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        return 0
    return len(PdfReader(str(pdf_path)).pages)


def read(
    paper_id: str,
    *,
    include_full_text: bool,
    cache_dir: Path,
    max_pdf_mb: int,
    enable_pdf_download: bool,
    allow_arbitrary_pdf_urls: bool = False,
    max_pdf_pages: int = 250,
    max_pdf_text_chars: int = 200_000,
    pdf_download_timeout_s: int = 60,
) -> PaperContent:
    """High-level entry: metadata + optional full text.

    Sweeps every PDF through the source policy + pdf_guard chain. Any
    refusal returns the abstract-only shape with a ``provenance`` note
    explaining why.
    """
    paper = fetch_metadata(paper_id)

    base_provenance = Provenance(
        sources_consulted=["arxiv"],
        notes=["fetch_metadata=ok"],
    )

    if not include_full_text:
        return PaperContent(paper=paper, source="arxiv-abstract", provenance=base_provenance)

    if not enable_pdf_download:
        log.info("PDF download disabled by config; returning abstract only.")
        prov = base_provenance.model_copy()
        prov.notes.append("pdf_download_disabled")
        return PaperContent(paper=paper, source="arxiv-abstract", provenance=prov)

    if not paper.pdf_url:
        log.info("no pdf_url for %s; returning abstract only.", paper.paper_id)
        prov = base_provenance.model_copy()
        prov.notes.append("no_pdf_url")
        return PaperContent(paper=paper, source="arxiv-abstract", provenance=prov)

    if not is_allowed_pdf_source(paper.pdf_url, allow_arbitrary=allow_arbitrary_pdf_urls):
        log.warning(
            "pdf source blocked by policy for %s: %s", paper.paper_id, paper.pdf_url
        )
        prov = base_provenance.model_copy()
        prov.notes.append("blocked_pdf_source")
        prov.extra["pdf_url_sha256_16"] = _hash_url(paper.pdf_url)
        return PaperContent(paper=paper, source="arxiv-abstract", provenance=prov)

    try:
        pdf_path = download_pdf(
            paper.pdf_url,
            cache_dir=cache_dir,
            paper_id=paper.paper_id,
            max_mb=max_pdf_mb,
            timeout_s=pdf_download_timeout_s,
        )
        ensure_pdf_size(pdf_path, max_pdf_mb)
        ensure_pdf_magic(pdf_path)
        ensure_pdf_page_limit(_page_count(pdf_path), max_pdf_pages)
        full_text = extract_text(pdf_path)
    except Exception as exc:
        log.exception("read_paper full-text path failed for %s: %s", paper.paper_id, exc)
        prov = base_provenance.model_copy()
        prov.notes.append("pdf_pipeline_failed")
        prov.extra["error"] = type(exc).__name__
        return PaperContent(paper=paper, source="arxiv-abstract", provenance=prov)

    truncated_before = len(full_text)
    full_text = ensure_pdf_text_cap(full_text, max_pdf_text_chars)
    truncated = truncated_before > len(full_text)

    prov = base_provenance.model_copy()
    prov.notes.extend(
        [
            "pdf_downloaded",
            "pdf_size_ok",
            "pdf_magic_ok",
            "pdf_pages_ok",
        ]
    )
    prov.extra["pdf_url_sha256_16"] = _hash_url(paper.pdf_url)
    prov.extra["pdf_chars"] = str(len(full_text))
    if truncated:
        prov.notes.append("pdf_text_truncated")

    return PaperContent(
        paper=paper,
        full_text=full_text,
        full_text_chars=len(full_text),
        full_text_truncated=truncated,
        source="arxiv-pdf",
        provenance=prov,
    )


__all__ = ["fetch_metadata", "download_pdf", "extract_text", "read"]
