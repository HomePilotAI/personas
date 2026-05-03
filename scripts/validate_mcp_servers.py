#!/usr/bin/env python3
"""Validate every MCP server in `mcp-servers/` for structural + contract health.

Each server folder (numeric prefix) must:

1. Have an entrypoint: ``src/index.js``, ``src/index.ts`` or ``src/index.py``.
2. Have a ``server.json`` listing its tools.
3. Match its tool names across:

     - ``server.json`` (the canonical contract),
     - ``src/tools.js`` if present (Node legacy export),
     - the POST routes implemented in ``src/index.js`` if present
       (legacy REST surface — every ``server.json`` tool must have a
       matching route, but extra routes are tolerated as deprecation
       shims while migration is in flight).

Step 3 closes the historical gap that let ``server.json`` declare one
contract while the legacy REST handlers used a different set of names.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVERS_DIR = ROOT / "mcp-servers"

# Servers still on the legacy REST shim. Drift is reported as a warning rather
# than a hard CI failure for these. Each server is removed from this set as it
# lands on real MCP via the node_common framework. See
# docs/migration/mcp-migration-tracker.md.
PENDING_MIGRATION: set[str] = set()


def _is_server_dir(path: Path) -> bool:
    return path.is_dir() and path.name[:2].isdigit()


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}")


def _server_json_tool_names(server_json: dict) -> list[str]:
    raw_tools = server_json.get("tools") or []
    names: list[str] = []
    for entry in raw_tools:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict) and entry.get("name"):
            names.append(entry["name"])
    return names


# Match both `"name": "..."` (legacy CommonJS JSON style) and `name: "..."`
# (ES module object literals used by migrated servers).
_TOOLS_JS_NAME = re.compile(r'(?:^|[\{,]\s*)"?name"?\s*:\s*"([^"]+)"', re.MULTILINE)
_INDEX_JS_POST = re.compile(r'app\.post\(\s*["\']/([A-Za-z0-9_/\-]+)["\']', re.MULTILINE)
# Migrated servers boot the SDK rather than hand-registering REST routes.
# Detecting the import lets us skip the legacy app.post check for them.
_MCP_NATIVE_MARKERS = (
    "@homepilot/mcp-node-common",
    "@modelcontextprotocol/sdk",
    "from mcp.server.fastmcp",
)


def _tools_js_names(tools_js: Path) -> list[str]:
    if not tools_js.exists():
        return []
    return _TOOLS_JS_NAME.findall(tools_js.read_text())


def _index_js_post_routes(index_js: Path) -> list[str]:
    if not index_js.exists():
        return []
    return _INDEX_JS_POST.findall(index_js.read_text())


def _is_mcp_native(entrypoint: Path) -> bool:
    if not entrypoint.exists():
        return False
    body = entrypoint.read_text()
    return any(marker in body for marker in _MCP_NATIVE_MARKERS)


def validate_server(server_dir: Path) -> list[str]:
    errors: list[str] = []
    name = server_dir.name

    src = server_dir / "src"
    entrypoints = [src / "index.js", src / "index.ts", src / "index.py"]
    if not any(p.exists() for p in entrypoints):
        errors.append(f"{name}: missing src/index.{{js,ts,py}}")

    server_json_path = server_dir / "server.json"
    server_json = _load_json(server_json_path)
    if server_json is None:
        errors.append(f"{name}: missing server.json")
        return errors

    canonical = _server_json_tool_names(server_json)
    if not canonical:
        errors.append(f"{name}: server.json declares no tools[]")
        return errors
    canon_set = set(canonical)

    tools_js = src / "tools.js"
    if tools_js.exists():
        legacy = set(_tools_js_names(tools_js))
        only_in_legacy = legacy - canon_set
        only_in_canon = canon_set - legacy
        if only_in_legacy:
            errors.append(
                f"{name}: src/tools.js declares tool(s) not in server.json: "
                f"{sorted(only_in_legacy)}"
            )
        if only_in_canon:
            errors.append(
                f"{name}: server.json declares tool(s) missing from src/tools.js: "
                f"{sorted(only_in_canon)}"
            )

    # POST-route check applies only to legacy REST entrypoints. Servers that
    # have migrated to the MCP SDK route via the protocol, not Express.
    index_js = src / "index.js"
    index_py = src / "index.py"
    native_entrypoint = next(
        (p for p in (index_js, index_py) if _is_mcp_native(p)), None
    )
    if not native_entrypoint and index_js.exists():
        routes = {r.split("/")[0] for r in _index_js_post_routes(index_js)}
        missing_routes = canon_set - routes
        if missing_routes:
            errors.append(
                f"{name}: src/index.js does not POST-handle declared tool(s): "
                f"{sorted(missing_routes)}"
            )

    return errors


def main() -> int:
    if not SERVERS_DIR.is_dir():
        print(f"MCP servers directory not found: {SERVERS_DIR}")
        return 1

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for server_dir in sorted(SERVERS_DIR.iterdir()):
        if not _is_server_dir(server_dir):
            continue
        errs = validate_server(server_dir)
        if not errs:
            print(f"  [+] {server_dir.name}: contract consistent")
            continue
        if server_dir.name in PENDING_MIGRATION:
            for e in errs:
                print(f"  [~] WARN {e}  (pending migration)")
            all_warnings.extend(errs)
        else:
            for e in errs:
                print(f"  [-] {e}")
            all_errors.extend(errs)

    print()
    if all_warnings:
        print(
            f"WARN — {len(all_warnings)} drift issue(s) on {len(PENDING_MIGRATION)} "
            "server(s) still pending MCP migration "
            "(see docs/migration/mcp-migration-tracker.md)"
        )
    if all_errors:
        print(f"FAIL — {len(all_errors)} drift issue(s) on already-migrated servers")
        return 1
    print("PASS — every migrated MCP server is structurally valid and contract-consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
