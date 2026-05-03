"""Contract-level tests — does FastMCP register the canonical 5 tools?

These run without network access and without the real ``arxiv`` package being
imported (``arxiv_client`` is loaded lazily inside ``search_arxiv``).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from researcher.server import mcp  # noqa: E402

CANONICAL_TOOLS = {
    "search_arxiv",
    "read_paper",
    "summarize_paper",
    "compare_papers",
    "build_literature_brief",
}


def _list_tool_names() -> set[str]:
    tools = asyncio.run(mcp.list_tools())
    return {t.name for t in tools}


def test_registers_canonical_tools() -> None:
    assert _list_tool_names() == CANONICAL_TOOLS


def test_remaining_stubs_return_not_implemented_envelope() -> None:
    """compare_papers and build_literature_brief are still sprint-3/4 stubs."""
    from researcher.server import build_literature_brief, compare_papers

    for fn, args in [
        (compare_papers, {"paper_ids": ["1706.03762", "2005.14165"]}),
        (build_literature_brief, {"topic": "transformers"}),
    ]:
        result = fn.fn(**args) if hasattr(fn, "fn") else fn(**args)
        assert result["status"] == "not_implemented"
        assert "sprint" in result
