"""Shared pytest fixtures: in-memory upstream + adapter under test."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeUpstream:
    """Stands in for the real ``medical-mcp-toolkit``.

    Tests configure ``responses`` keyed on tool name and the adapter calls
    through this object instead of HTTP — no network, no toolkit running.
    """

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def invoke(self, tool: str, args: dict[str, Any]):  # noqa: D401
        from doctor.upstream import UpstreamResponse

        self.calls.append((tool, args))
        if tool not in self.responses:
            return UpstreamResponse(ok=True, data={}, status="live")
        spec = self.responses[tool]
        if callable(spec):
            return UpstreamResponse(ok=True, data=spec(args), status="live")
        return UpstreamResponse(ok=True, data=spec, status="live")


@pytest.fixture()
def fake_upstream(monkeypatch):
    upstream = FakeUpstream()
    # Late import so the module-level CONFIG is built before we monkey-patch
    # the global client.
    import doctor.server as srv  # noqa: WPS433

    monkeypatch.setattr(srv, "_upstream", upstream)
    return upstream


@pytest.fixture()
def call_tool(monkeypatch):
    """Invoke a registered FastMCP tool by name without going through MCP IO."""

    import doctor.server as srv  # noqa: WPS433

    def _invoke(name: str, **kwargs):
        fn = getattr(srv, name)
        target = fn.fn if hasattr(fn, "fn") else fn
        return target(**kwargs)

    return _invoke
