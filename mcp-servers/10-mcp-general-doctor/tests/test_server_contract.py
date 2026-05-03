"""FastMCP-level contract: registers the 3 canonical tools."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doctor.server import mcp  # noqa: E402

CANONICAL = {"doctor_red_flags", "doctor_general_info", "doctor_self_care"}


def test_registers_canonical_three_tools() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == CANONICAL


def test_each_tool_has_input_schema_and_description() -> None:
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        assert t.description, f"tool {t.name} missing description"
        assert t.inputSchema and t.inputSchema.get("type") == "object"
