#!/usr/bin/env python3
"""Generate enriched persona metadata.

Writes:
* personas/<n>-<slug>/hpersona/preview/card.json    (rich gallery card)
* personas/<n>-<slug>/hpersona/blueprint/*.json     (agent + appearance + agentic)
* personas/<n>-<slug>/hpersona/manifest.json        (cross-checked flags)
* personas/<n>-<slug>/hpersona/dependencies/*.json  (mcp + tools + models + a2a + suite)
* personas/<n>-<slug>/gallery/registry-entry.json   (rich gallery item)
* personas/<n>-<slug>/README.md                     (rendered persona doc)
* mcp-servers/<n>-<server>/server.json              (full server contract)
* registry/personas/<id>.json                       (rich registry entry)
* registry/registry.json                            (gallery items[] format)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOW_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
PACKAGE_VERSION = "1.0.0"
HOMEPILOT_VERSION = "2.1.0"
AUTHOR = "homepilot-team"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def card_json(p: dict) -> dict:
    return {
        "name": p["name"],
        "role": p["role"],
        "class_id": p["class_id"],
        "description": p["short"],
        "stats": p["stats"],
        "style_tags": p["style_tags"],
        "tone_tags": p["tone_tags"],
        "tools": p["tools"],
        "backstory": p["backstory"],
        "tags": p["tags"],
        "content_rating": "nsfw" if p["nsfw"] else "sfw",
        "images": {
            "preview": "preview.webp",
            "avatar": f"../assets/avatar_{p['id']}.png",
            "thumb": f"../assets/thumb_avatar_{p['id']}.webp",
        },
    }


def persona_agent_json(p: dict) -> dict:
    return {
        "schema_version": 1,
        "id": p["id"],
        "name": p["name"],
        "role": p["role"],
        "class_id": p["class_id"],
        "description": p["short"],
        "system_prompt": p["system_prompt"],
        "opening_message": p.get(
            "opening_message",
            f"Hi — I'm {p['name']}, your {p['role'].lower()}. How can I help today?",
        ),
        "tone_tags": p["tone_tags"],
        "style_tags": p["style_tags"],
        "memory_mode": "adaptive",
    }


def persona_appearance_json(p: dict) -> dict:
    return {
        "schema_version": 1,
        "avatar_id": f"avatar_{p['id']}.png",
        "thumb_id": f"thumb_avatar_{p['id']}.webp",
        "palette": p["palette"],
        "emoji": p["emoji"],
    }


def agentic_json(p: dict) -> dict:
    return {
        "schema_version": 1,
        "capabilities": p["capabilities"],
    }


def manifest_json(p: dict) -> dict:
    has_mcp = bool(p["tool_specs"])
    has_tools = bool(p["tools"])
    return {
        "package_version": 2,
        "schema_version": 2,
        "kind": "homepilot.persona",
        "project_type": "persona",
        "id": p["id"],
        "version": PACKAGE_VERSION,
        "source_homepilot_version": HOMEPILOT_VERSION,
        "created_at": NOW_ISO,
        "content_rating": "nsfw" if p["nsfw"] else "sfw",
        "memory_mode": "adaptive",
        "contents": {
            "has_avatar": True,
            "has_outfits": False,
            "outfit_count": 0,
            "has_voice": False,
            "has_tool_dependencies": has_tools,
            "has_mcp_servers": has_mcp,
            "has_a2a_agents": False,
            "has_model_requirements": False,
        },
        "capability_summary": {
            "personality_tools": p["tools"],
            "capabilities": p["capabilities"],
            "mcp_servers_count": 1 if has_mcp else 0,
            "a2a_agents_count": 0,
        },
    }


def mcp_servers_json(p: dict) -> dict:
    base_port = 9100 + int(p["dir"].split("-")[0])
    return {
        "schema_version": 1,
        "servers": [
            {
                "name": p["mcp_server"],
                "description": f"MCP server for the {p['name']} persona.",
                "default_port": base_port,
                "url": f"http://localhost:{base_port}",
                "auth_type": "open",
                "registry_id": p["mcp_server"],
                "source": {"type": "registry", "registry_id": p["mcp_server"]},
                "transport": "HTTP",
                "protocol": "MCP",
                "health_endpoint": "/health",
                "tools_endpoint": "/tools",
                "tools_provided": p["tools"],
            }
        ],
    }


def tools_json(p: dict) -> dict:
    return {"schema_version": 1, "tools": p["tools"]}


def models_json(_: dict) -> dict:
    return {"schema_version": 1, "models": []}


def a2a_json(_: dict) -> dict:
    return {"schema_version": 1, "agents": []}


def suite_json(_: dict) -> dict:
    return {"schema_version": 1, "members": []}


def gallery_registry_entry(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "short": p["short"],
        "author": AUTHOR,
        "nsfw": p["nsfw"],
        "tags": p["tags"],
        "class_id": p["class_id"],
        "downloads": 0,
        "submitted_at": NOW_ISO,
        "issue_number": None,
        "latest": {
            "version": PACKAGE_VERSION,
            "preview_url": f"previews/{p['id']}/{PACKAGE_VERSION}/preview.webp",
            "card_url": f"previews/{p['id']}/{PACKAGE_VERSION}/card.json",
            "package_url": f"packages/{p['id']}/{PACKAGE_VERSION}/persona.hpersona",
            "size_bytes": 0,
            "submitted_at": NOW_ISO,
        },
    }


def server_contract_json(p: dict) -> dict:
    base_port = 9100 + int(p["dir"].split("-")[0])
    return {
        "name": p["mcp_server"],
        "description": f"MCP server for the {p['name']} persona.",
        "default_port": base_port,
        "protocol": "HTTP",
        "transport": "HTTP",
        "version": PACKAGE_VERSION,
        "health_endpoint": "/health",
        "tools_endpoint": "/tools",
        "auth_type": "open",
        "tools": p["tool_specs"],
    }


def readme_md(p: dict) -> str:
    tools_md = "\n".join(f"* **{t['name']}** — {t['description']}" for t in p["tool_specs"])
    return f"""# {p['name']}

> {p['short']}

**Class:** `{p['class_id']}`  ·  **Role:** {p['role']}  ·  **Content rating:** {'NSFW' if p['nsfw'] else 'SFW'}  ·  **Version:** v{PACKAGE_VERSION}

## Backstory

{p['backstory']}

## Style & tone

* Style: {", ".join(p['style_tags'])}
* Tone: {", ".join(p['tone_tags'])}

## Tools

This persona uses the MCP server **{p['mcp_server']}** and exposes the following tools:

{tools_md}

## System prompt

```
{p['system_prompt']}
```

## Files

* `hpersona/manifest.json` — package manifest (schema v2)
* `hpersona/blueprint/persona_agent.json` — agent definition + system prompt
* `hpersona/blueprint/persona_appearance.json` — avatar / palette
* `hpersona/blueprint/agentic.json` — capability list
* `hpersona/dependencies/mcp_servers.json` — MCP server contract
* `hpersona/dependencies/tools.json` — tool ids
* `hpersona/preview/card.json` — gallery character sheet
* `hpersona/assets/avatar_{p['id']}.png` — full-resolution avatar
* `hpersona/assets/thumb_avatar_{p['id']}.webp` — thumbnail
* `gallery/preview.webp` — gallery preview image
* `gallery/registry-entry.json` — gallery registry entry
"""


def main() -> int:
    rich_items = []

    for p in PERSONAS:
        base = ROOT / "personas" / p["dir"]
        hp = base / "hpersona"

        write_json(hp / "preview" / "card.json", card_json(p))
        write_json(hp / "blueprint" / "persona_agent.json", persona_agent_json(p))
        write_json(hp / "blueprint" / "persona_appearance.json", persona_appearance_json(p))
        write_json(hp / "blueprint" / "agentic.json", agentic_json(p))
        write_json(hp / "manifest.json", manifest_json(p))
        write_json(hp / "dependencies" / "mcp_servers.json", mcp_servers_json(p))
        write_json(hp / "dependencies" / "tools.json", tools_json(p))
        write_json(hp / "dependencies" / "models.json", models_json(p))
        write_json(hp / "dependencies" / "a2a_agents.json", a2a_json(p))
        write_json(hp / "dependencies" / "suite.json", suite_json(p))
        write_json(base / "gallery" / "registry-entry.json", gallery_registry_entry(p))
        write_text(base / "README.md", readme_md(p))

        rich_items.append(gallery_registry_entry(p))

        # MCP server contract
        for server_dir in (ROOT / "mcp-servers").iterdir():
            if server_dir.is_dir() and p["mcp_server"] in server_dir.name:
                write_json(server_dir / "server.json", server_contract_json(p))

        # Per-persona registry entry (rich)
        write_json(ROOT / "registry" / "personas" / f"{p['id']}.json", gallery_registry_entry(p))

        print(f"[{p['id']}] metadata + registry written")

    # Top-level registry in gallery format ({items: [...]})
    registry = {
        "version": "1.0.0",
        "generated_at": NOW_ISO,
        "items": rich_items,
        "personas": [p["id"] for p in PERSONAS],
        "mcp_servers": [p["mcp_server"] for p in PERSONAS],
    }
    write_json(ROOT / "registry" / "registry.json", registry)
    print(f"\nWrote registry/registry.json with {len(rich_items)} items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
