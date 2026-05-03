#!/usr/bin/env python3
"""Export the personas pack into the shape the HomePilot Cloudflare Worker
serves on https://homepilot-persona-gallery.cloud-data.workers.dev.

Reads:
  - registry/registry.json                  — the canonical source of truth
  - dist/packages/<id>/<v>/persona.hpersona — the binary artefacts
  - dist/previews/<id>/<v>/{preview.webp,card.json}

Writes:
  - dist/worker/registry.json              — additive entries, Worker URL shape
  - dist/worker/packages/<id>/<v>/persona.hpersona
  - dist/worker/previews/<id>/<v>/{preview.webp,card.json}

Two registry-export modes:

  --mode=additive   (default)  — only the entries from this repo, with
                                  Worker URL shape; the maintainer merges
                                  this into the live registry source.
  --mode=merge --live-registry-url=URL
                              — fetch the live registry, ADD the entries
                                  from this repo (preserving the existing
                                  community personas), and write the
                                  merged total to dist/worker/registry.json.

Outputs are sorted by id for deterministic diffs. Idempotent.

URL shape transform per item:
  packages/<id>/<v>/persona.hpersona  → /p/<id>/<v>
  previews/<id>/<v>/preview.webp     → /v/<id>/<v>
  previews/<id>/<v>/card.json        → /c/<id>/<v>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WORKER_OUT = DIST / "worker"


def _worker_shape(item: dict) -> dict:
    """Convert a registry item to the Worker URL shape."""
    out = {k: v for k, v in item.items() if k != "latest"}
    latest = dict(item["latest"])
    pid = item["id"]
    version = latest.get("version", "1.0.0")
    latest["package_url"] = f"/p/{pid}/{version}"
    latest["preview_url"] = f"/v/{pid}/{version}"
    latest["card_url"] = f"/c/{pid}/{version}"
    out["latest"] = latest
    return out


def _copy_artefacts(persona: dict) -> tuple[bool, list[str]]:
    """Mirror dist/packages and dist/previews under dist/worker/."""
    pid = persona["id"]
    version = persona.get("version", "1.0.0")
    src_pkg = DIST / "packages" / pid / version / "persona.hpersona"
    src_prev = DIST / "previews" / pid / version
    if not src_pkg.exists() or not src_prev.exists():
        return False, [f"missing dist artefacts for {pid} (run `make package` first)"]

    dst_pkg = WORKER_OUT / "packages" / pid / version / "persona.hpersona"
    dst_pkg.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_pkg, dst_pkg)

    dst_prev = WORKER_OUT / "previews" / pid / version
    dst_prev.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    for fname in ("preview.webp", "card.json"):
        srcf = src_prev / fname
        if srcf.exists():
            shutil.copyfile(srcf, dst_prev / fname)
        else:
            notes.append(f"missing {fname} for {pid}")
    return True, notes


def export(*, live_registry_url: str | None) -> dict:
    if WORKER_OUT.exists():
        shutil.rmtree(WORKER_OUT)
    WORKER_OUT.mkdir(parents=True, exist_ok=True)

    src_registry = json.loads((ROOT / "registry" / "registry.json").read_text())
    additive_items: list[dict] = []
    notes_all: list[str] = []
    for item in src_registry.get("items", []):
        ok, notes = _copy_artefacts(item)
        notes_all.extend(notes)
        if not ok:
            continue
        additive_items.append(_worker_shape(item))

    if live_registry_url:
        live = _fetch_live(live_registry_url)
        merged_items = _merge(live.get("items", []), additive_items)
        registry = {
            "schema_version": live.get("schema_version", 1),
            "generated_at": _now_iso(),
            "source": "merged: live + homepilotai/personas",
            "total": len(merged_items),
            "items": sorted(merged_items, key=lambda i: i["id"]),
        }
    else:
        registry = {
            "schema_version": 1,
            "generated_at": _now_iso(),
            "source": "homepilotai/personas (additive)",
            "total": len(additive_items),
            "items": sorted(additive_items, key=lambda i: i["id"]),
        }

    (WORKER_OUT / "registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    )
    return {
        "items": len(additive_items),
        "registry_total": registry["total"],
        "notes": notes_all,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_live(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "personas-export/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _merge(live: list[dict], new: list[dict]) -> list[dict]:
    """Merge live + new items by id; new wins on collision (we own the metadata)."""
    new_ids = {it["id"] for it in new}
    out = [it for it in live if it["id"] not in new_ids]
    out.extend(new)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export_for_worker")
    parser.add_argument("--mode", choices=["additive", "merge"], default="additive")
    parser.add_argument(
        "--live-registry-url",
        default="https://homepilot-persona-gallery.cloud-data.workers.dev/registry.json",
        help="Used in --mode=merge to fetch the live registry first.",
    )
    args = parser.parse_args(argv)

    if args.mode == "merge":
        result = export(live_registry_url=args.live_registry_url)
    else:
        result = export(live_registry_url=None)

    print(f"Exported {result['items']} additive item(s).")
    print(f"Final registry total: {result['registry_total']}.")
    print(f"Output: {WORKER_OUT.relative_to(ROOT)}/")
    if result["notes"]:
        print("Notes:")
        for n in result["notes"]:
            print(f"  - {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
