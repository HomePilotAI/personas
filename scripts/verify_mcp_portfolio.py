#!/usr/bin/env python3
"""Assess MCP server readiness for the High-Virality Persona Portfolio.

This check is intentionally conservative: it verifies contract compatibility and
looks for evidence of persona-specific capabilities in Python implementations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVERS_DIR = ROOT / "mcp-servers"


@dataclass
class CapabilityCheck:
    name: str
    keywords: tuple[str, ...]


EXPECTATIONS: dict[str, tuple[CapabilityCheck, ...]] = {
    "mcp-creator-muse": (
        CapabilityCheck("social-ready outputs", ("reel", "carousel", "cta", "scene")),
    ),
    "mcp-style-muse": (
        CapabilityCheck("before/after style variants", ("outfit", "style", "look", "variant")),
    ),
    "mcp-secretary-pro": (
        CapabilityCheck("schedule orchestration", ("schedule", "reminder", "slot")),
    ),
    "mcp-researcher": (
        CapabilityCheck("citation research workflow", ("arxiv", "paper", "brief", "summary")),
    ),
    "mcp-personal-trainer": (
        CapabilityCheck("workout planning", ("workout", "plan", "recovery", "streak")),
    ),
    "mcp-room-stylist": (
        CapabilityCheck("room redesign output", ("layout", "shopping", "style", "room")),
    ),
    "mcp-storyteller": (
        CapabilityCheck("branching story media", ("branching", "scene", "ending", "video")),
    ),
    "mcp-exam-coach": (
        CapabilityCheck("exam preparation", ("question", "quiz", "difficulty", "topic")),
    ),
    "mcp-mindfulness-coach": (
        CapabilityCheck("guided mindfulness", ("meditation", "focus", "script", "grounding")),
    ),
    "mcp-general-doctor": (
        CapabilityCheck("health safety framing", ("disclaimer", "urgent", "diagnosis", "concern")),
    ),
}


def evaluate_server(server_path: Path) -> tuple[str, list[str], list[str]]:
    server_json = json.loads((server_path / "server.json").read_text())
    name = server_json["name"]
    tools = [tool["name"] for tool in server_json.get("tools", [])]
    index_py = (server_path / "src" / "index.py").read_text().lower()

    passes: list[str] = []
    fails: list[str] = []

    if "attach_context_forge_routes" in index_py:
        passes.append("context-forge route attached")
    else:
        fails.append("missing context-forge route attachment")

    for tool in tools:
        if f"/{tool}" in index_py and f"'{tool}'" in index_py:
            passes.append(f"tool endpoint+runner found for {tool}")
        else:
            fails.append(f"missing endpoint or runner branch for {tool}")

    for cap in EXPECTATIONS.get(name, ()):  # qualitative heuristics
        if any(keyword in index_py for keyword in cap.keywords):
            passes.append(f"capability signal: {cap.name}")
        else:
            fails.append(f"capability gap: {cap.name}")

    if "not implemented yet" in index_py:
        fails.append("contains explicit non-implemented message")

    return name, passes, fails


def main() -> int:
    targets = sorted(p for p in SERVERS_DIR.iterdir() if p.is_dir() and p.name[:2].isdigit())
    any_fail = False
    print("MCP portfolio verification report")
    print("=" * 80)

    for server_path in targets:
        name, passes, fails = evaluate_server(server_path)
        status = "PASS" if not fails else "WARN"
        print(f"\n{name}: {status}")
        for item in passes:
            print(f"  [+] {item}")
        for item in fails:
            any_fail = True
            print(f"  [-] {item}")

    print("\n" + "=" * 80)
    if any_fail:
        print("Verification completed with warnings. Some personas need deeper production features.")
        return 1
    print("Verification passed: all servers meet baseline portfolio expectations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
