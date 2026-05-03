#!/usr/bin/env python3
"""One-shot backfill: compute sha256 for the existing dist artefacts (or a
synthetic-but-deterministic placeholder when dist/ isn't present) and write
it into every registry file.

Idempotent. Run after ``make package`` or whenever the registry needs to
catch up to the on-disk dist tree. Used once during sprint F1 to seed the
per-persona ``latest.sha256`` field across all 10 personas without
requiring a full asset rebuild.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _placeholder_sha(persona_id: str, size: int) -> str:
    """When the real package isn't on disk, derive a stable placeholder so
    every registry has *some* sha256 to publish. The first ``make package``
    overwrites it with the real digest. The placeholder is clearly tagged
    with the ``"placeholder-"`` prefix so consumers can tell it apart."""
    seed = f"{persona_id}|{size}|placeholder-v1".encode()
    digest = hashlib.sha256(seed).hexdigest()
    return f"placeholder-{digest}"


def _resolve_sha(persona: dict, size: int) -> str:
    pkg = DIST / "packages" / persona["id"] / persona.get("version", "1.0.0") / "persona.hpersona"
    if pkg.exists() and pkg.stat().st_size > 0:
        return _sha256_of(pkg)
    return _placeholder_sha(persona["id"], size)


def _patch_file(path: Path, sha: str) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    latest = data.get("latest", {})
    if latest.get("sha256") == sha:
        return False
    latest["sha256"] = sha
    data["latest"] = latest
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def main() -> int:
    # Seed sha256 in the top-level registry first; that's the one with the
    # already-correct size_bytes per persona.
    reg_path = ROOT / "registry" / "registry.json"
    reg = json.loads(reg_path.read_text())
    changed_top = False
    for item in reg.get("items", []):
        persona = next((p for p in PERSONAS if p["id"] == item["id"]), None)
        if not persona:
            continue
        size = int(item.get("latest", {}).get("size_bytes", 0))
        sha = _resolve_sha(persona, size)
        if item["latest"].get("sha256") != sha:
            item["latest"]["sha256"] = sha
            changed_top = True
    if changed_top:
        reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")

    # Then per-persona registry + gallery template.
    updated = 0
    for p in PERSONAS:
        item = next((i for i in reg["items"] if i["id"] == p["id"]), None)
        sha = item["latest"]["sha256"]  # always set above
        if _patch_file(ROOT / "registry" / "personas" / f"{p['id']}.json", sha):
            updated += 1
        if _patch_file(ROOT / "personas" / p["dir"] / "gallery" / "registry-entry.json", sha):
            updated += 1

    print(f"sha256 backfill: top-level={'updated' if changed_top else 'unchanged'}; per-file updates={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
