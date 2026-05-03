"""Tests for the abstract-based summarizer (sprint 2)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _paper():
    from researcher.models import PaperRef

    return PaperRef(
        paper_id="1706.03762v5",
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        abstract=(
            "We propose a new simple network architecture, the Transformer, "
            "based solely on attention mechanisms, dispensing with recurrence "
            "and convolutions entirely. Experiments on two machine translation "
            "tasks show these models to be superior in quality. A limitation "
            "is the model's quadratic memory cost in sequence length."
        ),
        published=datetime(2017, 6, 12, tzinfo=timezone.utc),
        abs_url="http://arxiv.org/abs/1706.03762v5",
    )


def test_short_style_returns_one_to_three_sentences() -> None:
    from researcher.summarizer import summarize_from_abstract

    paper = _paper()
    out = summarize_from_abstract(
        paper=paper, title=None, abstract=paper.abstract, full_text=None, style="short"
    )
    assert out["style"] == "short"
    assert 1 <= len(out["key_points"]) <= 3
    assert out["source"] == "abstract"
    assert out["rag_grounded"] is False


def test_technical_style_picks_more_sentences() -> None:
    from researcher.summarizer import summarize_from_abstract

    paper = _paper()
    out = summarize_from_abstract(
        paper=paper, title=None, abstract=paper.abstract, full_text=None, style="technical"
    )
    assert len(out["key_points"]) >= 3


def test_limitation_detection_picks_caveat_sentence() -> None:
    from researcher.summarizer import summarize_from_abstract

    paper = _paper()
    out = summarize_from_abstract(
        paper=paper, title=None, abstract=paper.abstract, full_text=None, style="technical"
    )
    assert any("limitation" in s.lower() for s in out["limitations"])


def test_citation_format_uses_authors_year_title_url() -> None:
    from researcher.summarizer import summarize_from_abstract

    paper = _paper()
    out = summarize_from_abstract(
        paper=paper, title=None, abstract=paper.abstract, full_text=None, style="short"
    )
    citation = out["citation"]
    assert "Vaswani" in citation
    assert "2017" in citation
    assert "Attention Is All You Need" in citation
    assert "et al." in citation  # 4 authors → truncated
    assert "1706.03762" in citation


def test_falls_back_to_metadata_only_message_when_no_text() -> None:
    from researcher.summarizer import summarize_from_abstract

    out = summarize_from_abstract(
        paper=None, title=None, abstract=None, full_text=None, style="short"
    )
    assert out["source"] == "empty"
    assert "metadata" in out["summary"].lower()


def test_full_text_preferred_over_abstract_when_long_enough() -> None:
    from researcher.summarizer import summarize_from_abstract

    long_text = ("This is a sentence. " * 20).strip()
    out = summarize_from_abstract(
        paper=None,
        title="X",
        abstract="ignored short abstract",
        full_text=long_text,
        style="executive",
    )
    assert out["source"] == "full_text"
