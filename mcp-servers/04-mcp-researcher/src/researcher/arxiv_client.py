"""arXiv search client.

Wraps the `arxiv` Python package and normalizes results to our :class:`PaperRef`
shape so MCP clients see a stable schema regardless of what the arxiv library
returns. The `arxiv` import is lazy so that environments without the package
(unit tests, fast scaffolding) can still import the module.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .models import PaperRef, SearchResult, SortBy

log = logging.getLogger("mcp-researcher.arxiv")

# arXiv IDs come in two flavours:
#   - new style: 1706.03762, 2310.06825v2
#   - old style: cs/0701039, math.GT/0309136
_NEW_STYLE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")
_OLD_STYLE = re.compile(r"\b([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?\b")
_ABS_URL = re.compile(r"https?://arxiv\.org/abs/([^\s?#]+)")


def normalize_paper_id(raw: str) -> str:
    """Extract a canonical arXiv ID from a URL, entry id or bare id."""
    if not raw:
        return raw
    raw = raw.strip()
    m = _ABS_URL.search(raw)
    if m:
        raw = m.group(1)
    for pat in (_NEW_STYLE, _OLD_STYLE):
        m = pat.search(raw)
        if m:
            base = m.group(1)
            ver = m.group(2) or ""
            return f"{base}{ver}"
    return raw


def _to_paper_ref(result: Any) -> PaperRef:
    paper_id = normalize_paper_id(getattr(result, "entry_id", "") or "")
    authors = [str(a.name) if hasattr(a, "name") else str(a) for a in getattr(result, "authors", [])]
    categories = list(getattr(result, "categories", []) or [])
    pdf_url = getattr(result, "pdf_url", None)
    abs_url = None
    entry_id = getattr(result, "entry_id", None)
    if entry_id and "arxiv.org/abs/" in entry_id:
        abs_url = entry_id
    return PaperRef(
        paper_id=paper_id or (entry_id or "unknown"),
        title=(getattr(result, "title", "") or "").strip().replace("\n", " "),
        authors=authors,
        abstract=(getattr(result, "summary", None) or "").strip() or None,
        published=getattr(result, "published", None),
        updated=getattr(result, "updated", None),
        primary_category=getattr(result, "primary_category", None),
        categories=categories,
        pdf_url=pdf_url,
        abs_url=abs_url,
        doi=getattr(result, "doi", None),
        journal_ref=getattr(result, "journal_ref", None),
    )


def _sort_criterion(sort_by: SortBy):
    import arxiv  # type: ignore

    return {
        "relevance": arxiv.SortCriterion.Relevance,
        "submittedDate": arxiv.SortCriterion.SubmittedDate,
        "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
    }[sort_by]


def _build_query(query: str, categories: list[str] | None) -> str:
    """Combine free-text query with optional category filters using arXiv syntax."""
    query = (query or "").strip()
    if not categories:
        return query
    cat_clause = " OR ".join(f"cat:{c.strip()}" for c in categories if c.strip())
    if not cat_clause:
        return query
    if not query:
        return cat_clause
    return f"({query}) AND ({cat_clause})"


def search(
    *,
    query: str,
    max_results: int,
    sort_by: SortBy,
    categories: list[str] | None = None,
    timeout_s: int = 30,
) -> SearchResult:
    """Search arXiv and return a normalized :class:`SearchResult`.

    Every call goes through the process-global rate limiter
    (:mod:`researcher.rate_limit`) so we never exceed arXiv's 1-request-per-
    3-seconds policy regardless of how many MCP workers are running.
    """
    try:
        import arxiv  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without arxiv installed
        log.error("arxiv package not installed: %s", exc)
        raise RuntimeError(
            "The 'arxiv' Python package is required for search_arxiv. "
            "Install it with `pip install arxiv` or `pip install -e .` from "
            "mcp-servers/04-mcp-researcher."
        ) from exc

    from . import rate_limit  # local import: no-op when called from tests

    full_query = _build_query(query, categories)
    log.info(
        "arxiv.search query=%r max_results=%d sort_by=%s",
        full_query,
        max_results,
        sort_by,
    )
    waited = rate_limit.acquire("arxiv")
    if waited > 0:
        log.info("arxiv rate limiter slept %.3fs before search", waited)
    search_obj = arxiv.Search(
        query=full_query,
        max_results=max_results,
        sort_by=_sort_criterion(sort_by),
    )
    client = arxiv.Client(page_size=max(10, max_results), delay_seconds=3.0, num_retries=3)
    results = [_to_paper_ref(r) for r in client.results(search_obj)]
    return SearchResult(
        query=full_query,
        sort_by=sort_by,
        total=len(results),
        results=results,
        source="arxiv",
        rate_limit_policy="arxiv_1_request_per_3_seconds",
    )


__all__ = ["search", "normalize_paper_id"]
