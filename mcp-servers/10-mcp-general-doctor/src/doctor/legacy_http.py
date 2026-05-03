"""Legacy HTTP / Context Forge compatibility surface for the General Doctor.

The canonical transport is FastMCP `--transport streamable-http` (`/mcp`).
Some HomePilot deployments and the older Context Forge integration patterns
still expect a per-tool REST surface:

    GET  /health
    GET  /tools
    POST /doctor_red_flags
    POST /doctor_general_info
    POST /doctor_self_care
    GET  /context-forge/tools
    POST /context-forge/call

This module builds a FastAPI app (via ``python_common.app_base``) that
exposes that surface and routes every call through the **same** safety
gateway used by the FastMCP tools. The legacy app does not duplicate any
business logic — it imports the handlers from ``doctor.server`` and calls
them with the inbound JSON.

Two run modes use this module:

* ``--transport legacy-http`` — run only the FastAPI app on
  ``DOCTOR_MCP_PORT`` (no MCP /mcp endpoint). Use when the deployment is
  legacy Context Forge / REST only.
* ``--transport hybrid`` — mount FastMCP's streamable-http ASGI app at
  ``/mcp`` inside the same FastAPI process so both surfaces are reachable
  on one port. Recommended during the migration window.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

# python_common lives alongside us under mcp-servers/python_common; it is
# not a published package, so we add the parent dir to sys.path on import.
_ROOT = Path(__file__).resolve().parents[3]
_COMMON = _ROOT / "python_common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

try:
    from app_base import (  # type: ignore[import-not-found]
        attach_context_forge_routes,
        create_base_app,
    )
except ImportError:  # pragma: no cover - tested via parent server
    create_base_app = None  # type: ignore[assignment]
    attach_context_forge_routes = None  # type: ignore[assignment]

log = logging.getLogger("mcp-general-doctor.legacy")


def _legacy_tools_metadata() -> list[dict[str, str]]:
    return [
        {
            "name": "doctor_red_flags",
            "description": (
                "Screen reported symptoms for emergency red flags. Adapter regex "
                "runs first; if it fires, returns an escalation envelope and "
                "never asks upstream."
            ),
        },
        {
            "name": "doctor_general_info",
            "description": (
                "Plain-language educational explanation of a health topic via "
                "searchMedicalKB. Strips diagnostic / dosing / clinical-order "
                "language before returning."
            ),
        },
        {
            "name": "doctor_self_care",
            "description": (
                "General self-care guidance, gated on red-flag triage. Refuses to "
                "give self-care if any red flag is present (adapter regex OR "
                "upstream emergency acuity)."
            ),
        },
    ]


def _unwrap(handler):
    """Return the plain Python function behind a FastMCP-decorated tool."""
    return handler.fn if hasattr(handler, "fn") else handler


def _filter_kwargs(handler, payload: dict[str, Any]) -> dict[str, Any]:
    """Pass only the fields the tool actually accepts.

    The legacy clients sometimes send extra fields ('id', 'session', etc.).
    We silently drop unknown keys rather than 400-ing on them; the tool's
    own pydantic validation still rejects malformed values.
    """
    import inspect

    sig = inspect.signature(_unwrap(handler))
    accepted = {p.name for p in sig.parameters.values()}
    return {k: v for k, v in payload.items() if k in accepted}


def build_legacy_app() -> FastAPI:
    """Build the FastAPI app that exposes the legacy REST + Context Forge surface."""
    if create_base_app is None or attach_context_forge_routes is None:
        raise RuntimeError(
            "python_common.app_base is not importable. Run with the repo as the "
            "current working directory or set PYTHONPATH=mcp-servers/python_common."
        )

    # Late import: doctor.server's module-level setup builds CONFIG and
    # connects the upstream client; we want all of that to run before we
    # take references to the handlers.
    from . import server as srv  # type: ignore[no-redef]

    tools_meta = _legacy_tools_metadata()
    app = create_base_app("mcp-general-doctor", tools_meta)

    handlers: dict[str, Any] = {
        "doctor_red_flags": srv.doctor_red_flags,
        "doctor_general_info": srv.doctor_general_info,
        "doctor_self_care": srv.doctor_self_care,
    }

    def _runner(name: str, args: dict[str, Any]) -> Any:
        if name not in handlers:
            raise ValueError(f"Unknown tool: {name}")
        fn = _unwrap(handlers[name])
        return fn(**_filter_kwargs(handlers[name], args))

    # Per-tool POST routes — preserve the wire shape the legacy clients
    # already use ({"result": <payload>}) so existing callers don't break.
    @app.post("/doctor_red_flags")
    async def red_flags(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"result": _runner("doctor_red_flags", payload or {})}

    @app.post("/doctor_general_info")
    async def general_info(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"result": _runner("doctor_general_info", payload or {})}

    @app.post("/doctor_self_care")
    async def self_care(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"result": _runner("doctor_self_care", payload or {})}

    attach_context_forge_routes(app, tools_meta, _runner)
    return app


def build_hybrid_app() -> FastAPI:
    """Build the FastAPI app and mount FastMCP's streamable-http ASGI app at /mcp.

    Operators get one process, one port, two surfaces:

      - /mcp                  → FastMCP (canonical)
      - /health, /tools, ...  → legacy REST + Context Forge

    Useful during the migration window before a deployment commits to one
    surface or the other.
    """
    from . import server as srv  # noqa: WPS433

    app = build_legacy_app()
    try:
        mcp_app = srv.mcp.streamable_http_app()
    except AttributeError as exc:  # pragma: no cover - SDK too old
        raise RuntimeError(
            "Installed mcp[cli] does not expose streamable_http_app(); "
            "upgrade to a newer SDK or run --transport legacy-http only."
        ) from exc
    # Starlette mount — FastMCP's app handles its own /mcp route.
    app.mount("/mcp", mcp_app)
    return app


def run_legacy_http(host: str, port: int) -> None:
    """Run the legacy-only FastAPI app via uvicorn."""
    import uvicorn

    log.info("starting legacy-http surface host=%s port=%d", host, port)
    uvicorn.run(build_legacy_app(), host=host, port=port, log_level="info")


def run_hybrid(host: str, port: int) -> None:
    """Run the hybrid FastAPI + FastMCP app via uvicorn."""
    import uvicorn

    log.info("starting hybrid (FastMCP /mcp + legacy REST) host=%s port=%d", host, port)
    uvicorn.run(build_hybrid_app(), host=host, port=port, log_level="info")
