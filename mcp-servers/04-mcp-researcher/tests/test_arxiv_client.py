"""Unit tests for arxiv_client. No network calls — uses a fake result class.

The real `arxiv` package is monkey-patched into ``sys.modules`` so the client
code path runs without hitting the live API.
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeAuthor:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeResult:
    def __init__(
        self,
        entry_id: str,
        title: str,
        authors: list[str],
        summary: str,
        primary_category: str = "cs.CL",
    ) -> None:
        self.entry_id = entry_id
        self.title = title
        self.authors = [_FakeAuthor(n) for n in authors]
        self.summary = summary
        self.published = datetime(2017, 6, 12, tzinfo=timezone.utc)
        self.updated = datetime(2017, 8, 2, tzinfo=timezone.utc)
        self.primary_category = primary_category
        self.categories = [primary_category, "cs.LG"]
        self.pdf_url = entry_id.replace("/abs/", "/pdf/") + ".pdf"
        self.doi = None
        self.journal_ref = None


class _FakeSortCriterion:
    Relevance = "relevance"
    SubmittedDate = "submittedDate"
    LastUpdatedDate = "lastUpdatedDate"


class _FakeSearch:
    def __init__(self, query: str, max_results: int, sort_by: str) -> None:
        self.query = query
        self.max_results = max_results
        self.sort_by = sort_by


class _FakeClient:
    def __init__(self, *_: object, **__: object) -> None: ...

    def results(self, search: _FakeSearch):
        # Generate a stable list — caller asked for max_results.
        base = [
            _FakeResult(
                "http://arxiv.org/abs/1706.03762v5",
                "Attention Is All You Need",
                ["Ashish Vaswani", "Noam Shazeer"],
                "We propose a new simple network architecture, the Transformer.",
            ),
            _FakeResult(
                "http://arxiv.org/abs/2005.14165v4",
                "Language Models are Few-Shot Learners",
                ["Tom B. Brown"],
                "We train GPT-3, an autoregressive language model with 175B parameters.",
            ),
            _FakeResult(
                "http://arxiv.org/abs/2310.06825v2",
                "Mistral 7B",
                ["Albert Q. Jiang"],
                "We introduce Mistral 7B, a 7-billion-parameter language model.",
            ),
        ]
        return base[: search.max_results]


@pytest.fixture()
def fake_arxiv(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    fake = types.ModuleType("arxiv")
    fake.Search = _FakeSearch  # type: ignore[attr-defined]
    fake.Client = _FakeClient  # type: ignore[attr-defined]
    fake.SortCriterion = _FakeSortCriterion  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "arxiv", fake)
    # Drop any cached import of arxiv_client so it re-binds against the fake.
    sys.modules.pop("researcher.arxiv_client", None)
    return fake


def test_normalize_paper_id_handles_urls_and_bare_ids() -> None:
    from researcher.arxiv_client import normalize_paper_id

    assert normalize_paper_id("http://arxiv.org/abs/1706.03762v5") == "1706.03762v5"
    assert normalize_paper_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
    assert normalize_paper_id("1706.03762") == "1706.03762"
    assert normalize_paper_id("arXiv:1706.03762v5") == "1706.03762v5"
    assert normalize_paper_id("cs/0701039") == "cs/0701039"


def test_search_returns_normalized_paper_refs(fake_arxiv) -> None:  # noqa: ARG001
    from researcher.arxiv_client import search

    result = search(query="transformers", max_results=2, sort_by="relevance")

    assert result.query == "transformers"
    assert result.sort_by == "relevance"
    assert result.total == 2
    assert len(result.results) == 2

    first = result.results[0]
    assert first.paper_id == "1706.03762v5"
    assert first.title == "Attention Is All You Need"
    assert first.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert first.abs_url == "http://arxiv.org/abs/1706.03762v5"
    assert first.pdf_url and first.pdf_url.endswith(".pdf")
    assert first.primary_category == "cs.CL"
    assert "cs.LG" in first.categories


def test_search_combines_query_and_categories(fake_arxiv) -> None:  # noqa: ARG001
    from researcher.arxiv_client import search

    result = search(
        query="rag",
        max_results=1,
        sort_by="submittedDate",
        categories=["cs.CL", "cs.IR"],
    )

    assert "(rag)" in result.query
    assert "cat:cs.CL" in result.query
    assert "cat:cs.IR" in result.query


def test_search_with_only_categories(fake_arxiv) -> None:  # noqa: ARG001
    from researcher.arxiv_client import search

    result = search(query="", max_results=1, sort_by="relevance", categories=["cs.CL"])
    assert result.query == "cat:cs.CL"


def test_search_raises_clear_error_when_arxiv_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    # Make `import arxiv` fail cleanly.
    monkeypatch.setitem(sys.modules, "arxiv", None)
    sys.modules.pop("researcher.arxiv_client", None)
    arxiv_client = importlib.import_module("researcher.arxiv_client")

    with pytest.raises(RuntimeError, match="arxiv"):
        arxiv_client.search(query="x", max_results=1, sort_by="relevance")
