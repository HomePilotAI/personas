"""Offline tests for paper_reader.

We fake both ``arxiv`` (for metadata) and ``httpx`` (for downloads) so the
tests run with no network and no real PDFs.
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
    def __init__(self) -> None:
        self.entry_id = "http://arxiv.org/abs/1706.03762v5"
        self.title = "Attention Is All You Need"
        self.authors = [_FakeAuthor("Ashish Vaswani"), _FakeAuthor("Noam Shazeer")]
        self.summary = "We propose the Transformer."
        self.published = datetime(2017, 6, 12, tzinfo=timezone.utc)
        self.updated = datetime(2017, 8, 2, tzinfo=timezone.utc)
        self.primary_category = "cs.CL"
        self.categories = ["cs.CL", "cs.LG"]
        self.pdf_url = "http://arxiv.org/pdf/1706.03762v5.pdf"
        self.doi = None
        self.journal_ref = None


class _FakeSearch:
    def __init__(self, *, id_list: list[str] | None = None, query: str | None = None,
                 max_results: int = 10, sort_by: str = "relevance") -> None:
        self.id_list = id_list or []
        self.query = query
        self.max_results = max_results
        self.sort_by = sort_by


class _FakeSortCriterion:
    Relevance = "relevance"
    SubmittedDate = "submittedDate"
    LastUpdatedDate = "lastUpdatedDate"


class _FakeArxivClient:
    def __init__(self, *_: object, **__: object) -> None: ...

    def results(self, search: _FakeSearch):
        if "1706.03762" in (search.id_list[0] if search.id_list else ""):
            return iter([_FakeResult()])
        return iter([])


@pytest.fixture()
def fake_arxiv(monkeypatch: pytest.MonkeyPatch):
    fake = types.ModuleType("arxiv")
    fake.Search = _FakeSearch  # type: ignore[attr-defined]
    fake.Client = _FakeArxivClient  # type: ignore[attr-defined]
    fake.SortCriterion = _FakeSortCriterion  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "arxiv", fake)
    sys.modules.pop("researcher.arxiv_client", None)
    sys.modules.pop("researcher.paper_reader", None)
    return fake


def test_fetch_metadata_returns_normalized_paper_ref(fake_arxiv) -> None:  # noqa: ARG001
    from researcher.paper_reader import fetch_metadata

    paper = fetch_metadata("arXiv:1706.03762")
    assert paper.paper_id.startswith("1706.03762")
    assert paper.title == "Attention Is All You Need"
    assert paper.pdf_url and paper.pdf_url.endswith(".pdf")


def test_fetch_metadata_raises_lookup_error_for_unknown(fake_arxiv) -> None:  # noqa: ARG001
    from researcher.paper_reader import fetch_metadata

    with pytest.raises(LookupError):
        fetch_metadata("9999.99999")


def test_read_returns_abstract_only_when_include_full_text_false(
    tmp_path: Path, fake_arxiv  # noqa: ARG001
) -> None:
    from researcher.paper_reader import read

    content = read(
        "1706.03762",
        include_full_text=False,
        cache_dir=tmp_path,
        max_pdf_mb=10,
        enable_pdf_download=True,
    )
    assert content.full_text is None
    assert content.source == "arxiv-abstract"


def test_read_skips_download_when_disabled(
    tmp_path: Path, fake_arxiv  # noqa: ARG001
) -> None:
    from researcher.paper_reader import read

    content = read(
        "1706.03762",
        include_full_text=True,
        cache_dir=tmp_path,
        max_pdf_mb=10,
        enable_pdf_download=False,
    )
    assert content.source == "arxiv-abstract"
    assert content.full_text is None


def test_safe_filename_strips_unusual_chars() -> None:
    from researcher.paper_reader import _safe_filename

    assert _safe_filename("cs/0701039v2") == "cs_0701039v2.pdf"
    assert _safe_filename("1706.03762v5") == "1706.03762v5.pdf"


def test_extract_text_handles_minimal_pdf(tmp_path: Path) -> None:
    """Smoke-test the extractor on a tiny synthetic PDF."""
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    pdf_path = tmp_path / "tiny.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    from researcher.paper_reader import extract_text

    text = extract_text(pdf_path)
    # Blank page → empty string is the expected outcome; we just want no crash.
    assert isinstance(text, str)
