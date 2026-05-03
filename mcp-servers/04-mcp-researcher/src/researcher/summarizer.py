"""Lightweight, deterministic abstract-based summarizer.

Sprint 2 ships a no-LLM summarizer so ``summarize_paper`` works offline and in
CI. Sprint 3 will add a WatsonX-grounded version that consumes chunks from the
vector store; the public tool name and shape stay the same.
"""

from __future__ import annotations

import re
from typing import Literal

from .models import PaperRef, SummaryStyle

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")

_STYLE_LIMITS: dict[SummaryStyle, tuple[int, int]] = {
    "short": (1, 3),
    "executive": (2, 4),
    "technical": (3, 6),
}


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _pick_key_points(sentences: list[str], style: SummaryStyle) -> list[str]:
    lo, hi = _STYLE_LIMITS[style]
    if not sentences:
        return []
    return sentences[: max(lo, min(hi, len(sentences)))]


def _detect_limitations(text: str) -> list[str]:
    text = text or ""
    matches = re.findall(
        r"([^.!?]*\b(?:limitation|caveat|future work|do not|cannot|may fail|trade-?off|risk)[^.!?]*[.!?])",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = [m.strip() for m in matches if len(m.strip()) > 20]
    return cleaned[:3]


def summarize_from_abstract(
    *,
    paper: PaperRef | None,
    title: str | None,
    abstract: str | None,
    full_text: str | None,
    style: SummaryStyle,
) -> dict:
    """Return a summary dict. Prefers full_text, then abstract, then title."""
    text_source: Literal["full_text", "abstract", "title", "empty"]
    if full_text and len(full_text) > 200:
        body = full_text
        text_source = "full_text"
    elif abstract:
        body = abstract
        text_source = "abstract"
    elif title:
        body = title
        text_source = "title"
    else:
        body = ""
        text_source = "empty"

    sentences = _split_sentences(body)
    key_points = _pick_key_points(sentences, style)
    limitations = _detect_limitations(body)

    summary = " ".join(key_points) if key_points else (
        "No abstract or full text available; only metadata was provided."
    )

    citation = None
    if paper:
        citation = _format_citation(paper)

    return {
        "title": (paper.title if paper else title) or "Untitled",
        "style": style,
        "source": text_source,
        "summary": summary,
        "key_points": key_points,
        "limitations": limitations,
        "citation": citation,
        "rag_grounded": False,
        "notes": (
            "Sprint-2 abstract-based summary. WatsonX-grounded RAG summary "
            "lands in sprint 3 (same tool name, same response shape)."
        ),
    }


def _format_citation(paper: PaperRef) -> str:
    authors = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors += " et al."
    year = paper.published.year if paper.published else "n.d."
    parts = [authors, f"({year})", f"“{paper.title}”"]
    if paper.abs_url:
        parts.append(paper.abs_url)
    elif paper.paper_id:
        parts.append(f"arXiv:{paper.paper_id}")
    return ". ".join(p for p in parts if p)


__all__ = ["summarize_from_abstract"]
