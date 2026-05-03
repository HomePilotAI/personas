"""FastMCP entry point for the Researcher persona.

Exposes the canonical 5 research tools over the MCP protocol. In Sprint 1 only
``search_arxiv`` is wired to a real implementation; the rest return typed
``ToolNotImplemented`` envelopes so MCP Inspector and Context Forge can still
list and validate them.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import audit as audit_mod
from . import rate_limit as rate_limit_mod
from . import safety as safety_mod
from .config import ResearcherConfig
from .models import (
    BriefStyle,
    PaperContent,
    Provenance,
    SearchResult,
    SortBy,
    SummaryStyle,
    ToolBlocked,
    ToolNotImplemented,
)

CONFIG = ResearcherConfig.from_env()

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("mcp-researcher")

# ── Process-global rate-limit registration ────────────────────────────
# arXiv ToU: 1 request per 3 seconds. Operators can raise the interval
# (e.g. to 5s) but the floor stays at 3s to keep us in policy.
rate_limit_mod.configure(
    "arxiv",
    max(3.0, float(CONFIG.arxiv_min_seconds_between_requests)),
)

_audit = audit_mod.AuditLogger(
    log_path=CONFIG.audit_log_path,
    hash_user_input=CONFIG.audit_hash_user_input,
)


def _emit_audit(
    *,
    request_id: str,
    tool: str,
    timer: audit_mod.CallTimer,
    domain: str = "general",
    sources: list[str] | None = None,
    papers: int = 0,
    blocked_categories: list[str] | None = None,
    blocked_sources: int = 0,
    error_type: str | None = None,
    user_input: str | None = None,
) -> None:
    rate_stats = rate_limit_mod.stats()
    _audit.emit(
        audit_mod.AuditEvent(
            request_id=request_id,
            timestamp=_audit.now_iso(),
            tool=tool,
            domain=domain,
            sources_consulted=sources or [],
            papers_examined=papers,
            blocked_categories=blocked_categories or [],
            blocked_sources=blocked_sources,
            rate_limit_wait_ms=float(rate_stats.get("total_waits_seconds", 0.0)) * 1000.0,
            latency_ms=timer.elapsed_ms(),
            error_type=error_type,
            user_input_sha256=audit_mod.maybe_hash(
                user_input, enabled=CONFIG.audit_hash_user_input
            ),
        )
    )


def _safety_refusal(tool: str, request_id: str, decision) -> dict[str, Any]:
    """Build a ToolBlocked envelope when the dual-use gate fires."""
    category = decision.primary_category or "unknown"
    message, alternatives = safety_mod.refusal_for(category)
    env = ToolBlocked(
        tool=tool,
        reason=f"dual_use_refused:{category}",
        matched=decision.matched,
        message=message,
        safe_alternatives=alternatives,
        provenance=Provenance(
            request_id=request_id,
            tool=tool,
            notes=["dual_use_safety_refusal"],
            extra={"categories": ",".join(decision.categories)},
        ),
    )
    return env.model_dump(mode="json")


mcp = FastMCP("mcp-researcher")


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def search_arxiv(
    query: Annotated[str, Field(description="Free-text search query.")],
    max_results: Annotated[
        int, Field(ge=1, le=50, description="Number of papers to return.")
    ] = 5,
    sort_by: Annotated[
        SortBy,
        Field(description="Sort order: relevance, submittedDate, lastUpdatedDate."),
    ] = "relevance",
    categories: Annotated[
        list[str] | None,
        Field(description="Optional arXiv category filters (e.g. ['cs.CL'])."),
    ] = None,
) -> dict[str, Any]:
    """Search arXiv and return normalized paper metadata.

    Runs the dual-use safety gate on the query first. Refusals come back
    as a typed ``ToolBlocked`` envelope with safe alternatives the caller
    can pivot to. Approved queries hit the arXiv API behind the
    process-global 1-req/3s rate limiter.
    """
    from . import arxiv_client  # local import — loaded only when tool fires

    request_id = _audit.new_request_id()
    timer = audit_mod.CallTimer()

    if CONFIG.enable_dual_use_safety:
        decision = safety_mod.evaluate(query)
        if not decision.allowed:
            _emit_audit(
                request_id=request_id,
                tool="search_arxiv",
                timer=timer,
                domain=decision.domain,
                blocked_categories=decision.categories,
                user_input=query,
            )
            return _safety_refusal("search_arxiv", request_id, decision)
        domain = decision.domain
    else:
        domain = "general"

    capped = min(max_results, CONFIG.arxiv_max_results, CONFIG.max_papers_per_request)
    log.info(
        "search_arxiv request_id=%s query=%r max_results=%d sort_by=%s categories=%s domain=%s",
        request_id,
        query,
        capped,
        sort_by,
        categories,
        domain,
    )
    try:
        result: SearchResult = arxiv_client.search(
            query=query,
            max_results=capped,
            sort_by=sort_by,
            categories=categories,
            timeout_s=CONFIG.arxiv_request_timeout_s,
        )
    except Exception as exc:
        _emit_audit(
            request_id=request_id,
            tool="search_arxiv",
            timer=timer,
            domain=domain,
            error_type=type(exc).__name__,
            user_input=query,
        )
        raise

    # Stamp request_id into the response provenance so audit ↔ response
    # is traceable.
    result.provenance.request_id = request_id
    result.provenance.tool = "search_arxiv"
    result.provenance.sources_consulted = ["arxiv"]
    payload = result.model_dump(mode="json")

    _emit_audit(
        request_id=request_id,
        tool="search_arxiv",
        timer=timer,
        domain=domain,
        sources=["arxiv"],
        papers=len(result.results),
        user_input=query,
    )
    return payload


@mcp.tool()
def read_paper(
    paper_id: Annotated[
        str, Field(description="arXiv paper ID, e.g. '1706.03762' or '1706.03762v5'.")
    ],
    include_full_text: Annotated[
        bool,
        Field(description="Download and extract the PDF text in addition to metadata."),
    ] = False,
) -> dict[str, Any]:
    """Return arXiv paper metadata, optionally with extracted full text."""
    from . import paper_reader

    log.info("read_paper paper_id=%s include_full_text=%s", paper_id, include_full_text)
    content: PaperContent = paper_reader.read(
        paper_id=paper_id,
        include_full_text=include_full_text,
        cache_dir=CONFIG.paper_cache_dir,
        max_pdf_mb=CONFIG.max_pdf_mb,
        enable_pdf_download=CONFIG.enable_pdf_download,
        allow_arbitrary_pdf_urls=CONFIG.allow_arbitrary_pdf_urls,
        max_pdf_pages=CONFIG.max_pdf_pages,
        max_pdf_text_chars=CONFIG.max_pdf_text_chars,
        pdf_download_timeout_s=CONFIG.pdf_download_timeout_s,
    )
    return content.model_dump(mode="json")


@mcp.tool()
def summarize_paper(
    paper_id: Annotated[
        str | None, Field(description="arXiv paper ID; preferred over inline fields.")
    ] = None,
    title: Annotated[str | None, Field(description="Paper title (fallback).")] = None,
    abstract: Annotated[str | None, Field(description="Paper abstract (fallback).")] = None,
    full_text: Annotated[
        str | None, Field(description="Full paper text if already extracted.")
    ] = None,
    style: Annotated[
        SummaryStyle, Field(description="Summary depth: short, technical, executive.")
    ] = "technical",
) -> dict[str, Any]:
    """Summarize a paper.

    Sprint-2 produces an abstract-based deterministic summary (no LLM). Sprint-3
    upgrades this to a WatsonX-grounded RAG summary using the same tool shape.
    """
    from . import paper_reader, summarizer

    paper = None
    resolved_abstract = abstract
    resolved_title = title
    resolved_full_text = full_text

    if paper_id and not (resolved_abstract and resolved_title):
        try:
            paper = paper_reader.fetch_metadata(paper_id)
            resolved_title = resolved_title or paper.title
            resolved_abstract = resolved_abstract or paper.abstract
        except Exception as exc:
            log.warning("summarize_paper metadata lookup failed: %s", exc)

    return summarizer.summarize_from_abstract(
        paper=paper,
        title=resolved_title,
        abstract=resolved_abstract,
        full_text=resolved_full_text,
        style=style,
    )


@mcp.tool()
def compare_papers(
    paper_ids: Annotated[
        list[str], Field(min_length=2, max_length=5, description="2–5 arXiv paper IDs.")
    ],
    comparison_dimensions: Annotated[
        list[str] | None,
        Field(
            description=(
                "Optional list of dimensions to compare on, e.g. "
                "['method', 'dataset', 'result', 'limitation']."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """Side-by-side compare papers across method, dataset, results, limitations."""
    return ToolNotImplemented(
        tool="compare_papers",
        sprint="sprint-3",
        message="compare_papers requires the RAG layer; lands in sprint 3.",
    ).model_dump()


@mcp.tool()
def build_literature_brief(
    topic: Annotated[str, Field(description="Topic for the literature brief.")],
    max_papers: Annotated[
        int, Field(ge=2, le=20, description="Max papers to include.")
    ] = 8,
    include_citations: Annotated[
        bool, Field(description="Attach arXiv citation strings to each finding.")
    ] = True,
    brief_style: Annotated[
        BriefStyle, Field(description="academic | executive | technical.")
    ] = "academic",
) -> dict[str, Any]:
    """Build a citation-backed literature brief for a topic."""
    return ToolNotImplemented(
        tool="build_literature_brief",
        sprint="sprint-4",
        message="build_literature_brief lands in sprint 4 once RAG + citations are in place.",
    ).model_dump()


# ── Entry point ──────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mcp-researcher")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=CONFIG.transport,
        help="MCP transport (default from MCP_RESEARCHER_TRANSPORT, fallback stdio).",
    )
    parser.add_argument("--host", default=CONFIG.host)
    parser.add_argument("--port", type=int, default=CONFIG.port)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log.info(
        "starting mcp-researcher transport=%s host=%s port=%s",
        args.transport,
        args.host,
        args.port,
    )

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    sys.exit(main())
