#!/usr/bin/env python3
"""Build distributable .hpersona packages and gallery preview artifacts.

Produces:
* dist/packages/<id>/<version>/persona.hpersona     (zip of hpersona/)
* dist/previews/<id>/<version>/preview.webp         (mirror of gallery preview)
* dist/previews/<id>/<version>/card.json            (mirror of preview/card.json)

Then rewrites registry/registry.json with the real size_bytes of each package.
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGES = DIST / "packages"
PREVIEWS = DIST / "previews"
VERSION = "1.0.0"
NOW_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_package(persona: dict) -> Path:
    src = ROOT / "personas" / persona["dir"] / "hpersona"
    out_dir = PACKAGES / persona["id"] / VERSION
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "persona.hpersona"

    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(src)))
    return out_path


def copy_preview(persona: dict) -> tuple[Path, Path]:
    out_dir = PREVIEWS / persona["id"] / VERSION
    out_dir.mkdir(parents=True, exist_ok=True)

    src_preview = ROOT / "personas" / persona["dir"] / "gallery" / "preview.webp"
    dst_preview = out_dir / "preview.webp"
    shutil.copyfile(src_preview, dst_preview)

    src_card = ROOT / "personas" / persona["dir"] / "hpersona" / "preview" / "card.json"
    dst_card = out_dir / "card.json"
    shutil.copyfile(src_card, dst_card)
    return dst_preview, dst_card


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)

    sizes: dict[str, int] = {}
    for p in PERSONAS:
        pkg = build_package(p)
        copy_preview(p)
        sizes[p["id"]] = pkg.stat().st_size
        print(f"[{p['id']}] built {pkg.relative_to(ROOT)}  ({sizes[p['id']]} bytes)")

    # Update size_bytes in registry
    reg_path = ROOT / "registry" / "registry.json"
    reg = json.loads(reg_path.read_text())
    for item in reg.get("items", []):
        size = sizes.get(item["id"])
        if size is not None:
            item["latest"]["size_bytes"] = size
    reg["generated_at"] = NOW_ISO
    reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")

    # Per-persona registry too
    for p in PERSONAS:
        per = ROOT / "registry" / "personas" / f"{p['id']}.json"
        data = json.loads(per.read_text())
        data["latest"]["size_bytes"] = sizes[p["id"]]
        per.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print(f"\nBuilt {len(PERSONAS)} hpersona packages into {DIST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
