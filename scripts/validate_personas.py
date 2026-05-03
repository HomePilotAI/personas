#!/usr/bin/env python3
"""Validate every persona for production readiness.

Checks:
* Required hpersona/ subfolders and manifest fields exist.
* preview/card.json is enriched (role, class_id, stats, tools, backstory, tags).
* gallery/registry-entry.json has the gallery item shape (id/name/short/tags/latest).
* Registered tools match dependencies/tools.json and dependencies/mcp_servers.json.
* Avatar PNG and gallery preview are larger than the historical 1KB stubs.
* short description ≤ 120 chars (gallery card limit).
* Safety personas declare a disclaimer in their system prompt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONAS_DIR = ROOT / "personas"

SAFETY_REQUIRES_DISCLAIMER = {
    "general-doctor": ["consult", "professional", "emergency"],
    "mindfulness-coach": ["therapist", "professional", "crisis"],
    "personal-trainer": ["physician", "medical", "injury"],
    "exam-coach": ["academic integrity", "institution"],
}

REQUIRED_CARD_FIELDS = {"name", "role", "class_id", "description", "stats", "tools", "tags", "backstory", "images"}
REQUIRED_REGISTRY_FIELDS = {"id", "name", "short", "tags", "nsfw", "class_id", "latest"}
REQUIRED_LATEST_FIELDS = {"version", "preview_url", "card_url", "package_url"}


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print(f"  [-] {msg}")


def ok(msg: str) -> None:
    print(f"  [+] {msg}")


def validate_persona(persona_dir: Path) -> list[str]:
    errors: list[str] = []
    print(f"\n{persona_dir.name}")
    hp = persona_dir / "hpersona"

    for sub in ("manifest.json", "blueprint", "dependencies", "assets", "preview"):
        if not (hp / sub).exists():
            fail(f"missing hpersona/{sub}", errors)

    manifest = json.loads((hp / "manifest.json").read_text())
    for k in ("package_version", "schema_version", "kind", "id", "version", "content_rating"):
        if k not in manifest:
            fail(f"manifest missing key: {k}", errors)
    if manifest.get("schema_version") != 2:
        fail(f"manifest schema_version is {manifest.get('schema_version')}, expected 2", errors)

    card = json.loads((hp / "preview" / "card.json").read_text())
    missing = REQUIRED_CARD_FIELDS - set(card.keys())
    if missing:
        fail(f"card.json missing fields: {sorted(missing)}", errors)
    else:
        ok("card.json has all rich fields")

    if "stats" in card:
        for stat in ("charisma", "elegance", "confidence", "warmth", "level"):
            if stat not in card["stats"]:
                fail(f"card.stats missing '{stat}'", errors)

    short = card.get("description", "")
    if len(short) > 120:
        fail(f"description is {len(short)} chars (>120 gallery limit)", errors)
    else:
        ok(f"description length {len(short)}/120")

    tools_in_card = card.get("tools", [])
    deps_tools = json.loads((hp / "dependencies" / "tools.json").read_text()).get("tools", [])
    if sorted(tools_in_card) != sorted(deps_tools):
        fail(f"tools mismatch: card={tools_in_card} deps={deps_tools}", errors)
    else:
        ok(f"tools consistent ({len(deps_tools)})")

    mcp = json.loads((hp / "dependencies" / "mcp_servers.json").read_text())
    for s in mcp.get("servers", []):
        if not set(s.get("tools_provided", [])) >= set(deps_tools):
            fail("mcp server tools_provided does not cover dependencies/tools.json", errors)
        # New: every server MUST carry an `install` block so HomePilot's
        # Install-Persona flow knows how to provision it. Backwards-
        # compatible: missing block is a WARN-once, not a hard fail (so
        # community personas built before sprint-F survive).
        install = s.get("install")
        if not install:
            fail(f"mcp server '{s.get('name','?')}' missing install block (required for auto-install)", errors)
            continue
        for required in ("source_type", "source_subdir", "runtime", "install_cmd", "start_cmd", "health_url", "default_port"):
            if required not in install:
                fail(f"mcp server '{s.get('name','?')}' install missing key: {required}", errors)
        if install.get("runtime") not in {"python", "node"}:
            fail(f"mcp server '{s.get('name','?')}' install.runtime must be python|node", errors)
        if "{PORT}" not in install.get("start_cmd", "") + install.get("health_url", ""):
            fail(f"mcp server '{s.get('name','?')}' install must templatize {{PORT}}", errors)

    avatar_pngs = list((hp / "assets").glob("avatar_*.png"))
    if not avatar_pngs:
        fail("no avatar PNG in assets/", errors)
    elif avatar_pngs[0].stat().st_size < 5_000:
        fail(f"avatar PNG too small ({avatar_pngs[0].stat().st_size} bytes) — looks like a stub", errors)
    else:
        ok(f"avatar PNG present ({avatar_pngs[0].stat().st_size} bytes)")

    preview = persona_dir / "gallery" / "preview.webp"
    if not preview.exists():
        fail("missing gallery/preview.webp", errors)
    elif preview.stat().st_size < 2_000:
        fail(f"gallery preview too small ({preview.stat().st_size} bytes) — looks like a stub", errors)
    else:
        ok(f"gallery preview present ({preview.stat().st_size} bytes)")

    reg = json.loads((persona_dir / "gallery" / "registry-entry.json").read_text())
    missing_r = REQUIRED_REGISTRY_FIELDS - set(reg.keys())
    if missing_r:
        fail(f"gallery registry-entry missing fields: {sorted(missing_r)}", errors)
    if "latest" in reg:
        missing_l = REQUIRED_LATEST_FIELDS - set(reg["latest"].keys())
        if missing_l:
            fail(f"gallery registry-entry.latest missing fields: {sorted(missing_l)}", errors)
        else:
            ok("registry entry has gallery shape")

    agent = json.loads((hp / "blueprint" / "persona_agent.json").read_text())
    sp = agent.get("system_prompt", "")
    if not sp:
        fail("blueprint/persona_agent.json missing system_prompt", errors)
    else:
        ok(f"system prompt length {len(sp)}")

    pid = manifest.get("id") or reg.get("id")
    needs = SAFETY_REQUIRES_DISCLAIMER.get(pid)
    if needs:
        lower = sp.lower()
        missing_kw = [kw for kw in needs if kw.lower() not in lower]
        if missing_kw:
            fail(f"safety system prompt missing keywords: {missing_kw}", errors)
        else:
            ok(f"safety disclaimer keywords present: {needs}")

    return errors


def main() -> int:
    if not PERSONAS_DIR.is_dir():
        print(f"Personas directory not found: {PERSONAS_DIR}")
        return 1

    all_errors: list[str] = []
    for d in sorted(PERSONAS_DIR.iterdir()):
        if not d.is_dir():
            continue
        all_errors.extend(validate_persona(d))

    print("\n" + "=" * 72)
    if all_errors:
        print(f"FAIL - {len(all_errors)} issues across personas")
        return 1
    print("PASS - all personas validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
