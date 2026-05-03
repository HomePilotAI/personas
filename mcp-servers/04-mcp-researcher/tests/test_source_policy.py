"""Tests for the source allow / deny policy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from researcher.source_policy import (  # noqa: E402
    classify,
    is_allowed_metadata_source,
    is_allowed_pdf_source,
    is_blocked_source,
)


# ── Hard deny ──────────────────────────────────────────────────────────


def test_blocks_pirated_mirrors() -> None:
    for url in [
        "https://sci-hub.se/paper.pdf",
        "https://sci-hub.ru/10.1234/foo",
        "https://libgen.is/scimag/",
        "https://library-genesis.example.org/x.pdf",
        "https://z-library.org/a.pdf",
        "https://en.zlib-something.example/file.pdf",
    ]:
        assert is_blocked_source(url), f"failed to block: {url}"


def test_blocks_non_http_schemes() -> None:
    for url in [
        "file:///etc/passwd",
        "ftp://example.com/file.pdf",
        "javascript:alert(1)",
        "data:text/html,<h1>x</h1>",
    ]:
        assert is_blocked_source(url), f"failed to block scheme in: {url}"


def test_blocks_loopback_and_private_networks() -> None:
    for url in [
        "http://localhost/file.pdf",
        "http://127.0.0.1/file.pdf",
        "http://0.0.0.0/file.pdf",
        "http://10.0.0.5/x.pdf",
        "http://192.168.1.1/x.pdf",
        "http://172.16.0.1/x.pdf",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
    ]:
        assert is_blocked_source(url), f"failed to block private/loopback: {url}"


def test_blocks_empty_or_none() -> None:
    assert is_blocked_source("")
    assert is_blocked_source(None)  # type: ignore[arg-type]


# ── Allow lists ─────────────────────────────────────────────────────────


def test_allows_arxiv_pdf_by_default() -> None:
    assert is_allowed_pdf_source("https://arxiv.org/pdf/1706.03762.pdf")
    assert is_allowed_pdf_source("https://export.arxiv.org/pdf/1706.03762v5.pdf")


def test_allows_pmc_and_osti_pdfs() -> None:
    assert is_allowed_pdf_source("https://www.osti.gov/biblio/12345.pdf")
    assert is_allowed_pdf_source("https://europepmc.org/articles/PMC123456/pdf/")


def test_allows_metadata_apis() -> None:
    for url in [
        "https://api.openalex.org/works",
        "https://api.crossref.org/works",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "https://api.adsabs.harvard.edu/v1/search/query",
        "https://www.osti.gov/api/v1/records",
        "https://clinicaltrials.gov/api/query/study_fields",
    ]:
        assert is_allowed_metadata_source(url), f"failed to allow metadata host: {url}"


def test_disallows_unknown_pdf_hosts_without_override() -> None:
    assert not is_allowed_pdf_source("https://example.com/test.pdf")
    # Developer escape hatch — still rejects pirated mirrors though.
    assert is_allowed_pdf_source(
        "https://example.com/test.pdf", allow_arbitrary=True
    )
    assert not is_allowed_pdf_source(
        "https://sci-hub.example/test.pdf", allow_arbitrary=True
    )


def test_classify_returns_reason_codes() -> None:
    assert classify("https://arxiv.org/abs/x").reason == "allowed"
    assert classify("https://sci-hub.ru/x").reason == "blocked_pirated_mirror"
    assert classify("file:///etc/passwd").reason == "blocked_scheme"
    assert classify("http://127.0.0.1/x").reason == "blocked_private_network"
    assert classify("").reason == "blocked_empty_url"
