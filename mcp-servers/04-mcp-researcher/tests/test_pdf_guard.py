"""Tests for the PDF safety guards."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from researcher.pdf_guard import (  # noqa: E402
    ensure_pdf_magic,
    ensure_pdf_page_limit,
    ensure_pdf_size,
    ensure_pdf_text_cap,
)


def test_ensure_pdf_size_passes_under_cap(tmp_path: Path) -> None:
    pdf = tmp_path / "small.pdf"
    pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 1024)
    ensure_pdf_size(pdf, max_mb=1)


def test_ensure_pdf_size_raises_over_cap(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    pdf.write_bytes(b"0" * (2 * 1024 * 1024))
    with pytest.raises(ValueError, match="exceeds max size"):
        ensure_pdf_size(pdf, max_mb=1)


def test_ensure_pdf_page_limit_passes_under_cap() -> None:
    ensure_pdf_page_limit(page_count=10, max_pages=250)


def test_ensure_pdf_page_limit_raises_over_cap() -> None:
    with pytest.raises(ValueError, match="exceeds max pages"):
        ensure_pdf_page_limit(page_count=300, max_pages=250)


def test_ensure_pdf_magic_passes_for_real_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.7\nrest is not a real pdf but starts right")
    ensure_pdf_magic(pdf)


def test_ensure_pdf_magic_raises_for_html_login_page(tmp_path: Path) -> None:
    """A redirect-to-login HTML page is the most common silent-failure mode."""
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"<!DOCTYPE html><html>login required</html>")
    with pytest.raises(ValueError, match="not a valid PDF"):
        ensure_pdf_magic(fake)


def test_ensure_pdf_text_cap_truncates() -> None:
    text = "x" * 100
    out = ensure_pdf_text_cap(text, max_chars=40)
    assert len(out) == 40


def test_ensure_pdf_text_cap_passes_short_text() -> None:
    text = "abc"
    out = ensure_pdf_text_cap(text, max_chars=40)
    assert out == "abc"
