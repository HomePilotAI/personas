#!/usr/bin/env python3
"""Build distributable .hpersona packages and gallery preview artifacts.

Produces (per persona, per version):

  * dist/packages/<id>/<version>/persona.hpersona       (zip of hpersona/)
  * dist/previews/<id>/<version>/preview.webp           (gallery preview image)
  * dist/previews/<id>/<version>/card.json              (gallery character sheet)
  * dist/previews/<id>/<version>/avatar.png             (the avatar mirrored
                                                          out so the gallery
                                                          modal renders it)
  * dist/previews/<id>/<version>/thumb.webp             (avatar thumbnail)

Then rewrites:

  * registry/registry.json
  * registry/personas/<id>.json
  * personas/<id>/gallery/registry-entry.json

…with the real ``size_bytes`` and ``sha256`` of each package, plus the
relative ``avatar`` and ``thumb`` URLs the gallery card.json needs.
"""

from __future__ import annotations

import hashlib
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
DEFAULT_VERSION = "1.0.0"
NOW_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _persona_version(persona: dict) -> str:
    """Honor a per-persona ``version`` override; fall back to the platform default."""
    return persona.get("version", DEFAULT_VERSION)


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_package(persona: dict) -> Path:
    src = ROOT / "personas" / persona["dir"] / "hpersona"
    version = _persona_version(persona)
    out_dir = PACKAGES / persona["id"] / version
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "persona.hpersona"

    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(src)))
    return out_path


def copy_preview(persona: dict) -> tuple[Path, Path, Path | None, Path | None]:
    """Mirror preview, card, avatar, and thumb into ``dist/previews/``.

    Returns ``(preview_path, card_path, avatar_path_or_None,
    thumb_path_or_None)``. Avatars + thumbs are best-effort: if the source
    image is missing we keep going (the asset pipeline regenerates them on
    every CI run).
    """
    version = _persona_version(persona)
    out_dir = PREVIEWS / persona["id"] / version
    out_dir.mkdir(parents=True, exist_ok=True)

    src_preview = ROOT / "personas" / persona["dir"] / "gallery" / "preview.webp"
    dst_preview = out_dir / "preview.webp"
    shutil.copyfile(src_preview, dst_preview)

    src_card = ROOT / "personas" / persona["dir"] / "hpersona" / "preview" / "card.json"
    dst_card = out_dir / "card.json"
    # Rewrite card.json image paths so they point at sibling files in dist/
    # instead of the now-broken ``../assets/avatar_<id>.png`` relative path.
    card = json.loads(src_card.read_text())
    images = card.get("images", {})
    images["preview"] = "preview.webp"
    images["avatar"] = "avatar.png"
    images["thumb"] = "thumb.webp"
    card["images"] = images
    dst_card.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")

    pid = persona["id"]
    avatar_src = ROOT / "personas" / persona["dir"] / "hpersona" / "assets" / f"avatar_{pid}.png"
    thumb_src = ROOT / "personas" / persona["dir"] / "hpersona" / "assets" / f"thumb_avatar_{pid}.webp"
    avatar_dst: Path | None = None
    thumb_dst: Path | None = None
    if avatar_src.exists():
        avatar_dst = out_dir / "avatar.png"
        shutil.copyfile(avatar_src, avatar_dst)
    if thumb_src.exists():
        thumb_dst = out_dir / "thumb.webp"
        shutil.copyfile(thumb_src, thumb_dst)

    return dst_preview, dst_card, avatar_dst, thumb_dst


def _stamp_latest(latest: dict, *, version: str, size: int, sha: str) -> dict:
    """Apply the post-build size + sha256 + path data into a ``latest`` block."""
    latest["version"] = version
    latest["size_bytes"] = size
    latest["sha256"] = sha
    # Path layout the gallery consumes.
    pid = latest.get("_persona_id")  # set by the callers below
    if pid:
        latest["package_url"] = f"packages/{pid}/{version}/persona.hpersona"
        latest["preview_url"] = f"previews/{pid}/{version}/preview.webp"
        latest["card_url"] = f"previews/{pid}/{version}/card.json"
        latest.pop("_persona_id", None)
    return latest


def _update_registry_file(path: Path, *, persona: dict, version: str, size: int, sha: str) -> None:
    data = json.loads(path.read_text())
    latest = data.get("latest") or {}
    latest["_persona_id"] = persona["id"]
    _stamp_latest(latest, version=version, size=size, sha=sha)
    data["latest"] = latest
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)

    summary: dict[str, dict[str, str | int]] = {}
    for p in PERSONAS:
        pkg = build_package(p)
        copy_preview(p)
        size = pkg.stat().st_size
        sha = _sha256_of(pkg)
        version = _persona_version(p)
        summary[p["id"]] = {"size": size, "sha": sha, "version": version}
        print(f"[{p['id']}] built {pkg.relative_to(ROOT)}  ({size} bytes, sha={sha[:12]}…, v{version})")

    # Top-level registry
    reg_path = ROOT / "registry" / "registry.json"
    reg = json.loads(reg_path.read_text())
    for item in reg.get("items", []):
        info = summary.get(item["id"])
        if not info:
            continue
        latest = item.setdefault("latest", {})
        latest["_persona_id"] = item["id"]
        _stamp_latest(latest, version=str(info["version"]), size=int(info["size"]), sha=str(info["sha"]))
    reg["generated_at"] = NOW_ISO
    reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")

    # Per-persona registry + per-persona gallery template
    for p in PERSONAS:
        info = summary[p["id"]]
        per = ROOT / "registry" / "personas" / f"{p['id']}.json"
        if per.exists():
            _update_registry_file(per, persona=p, version=str(info["version"]), size=int(info["size"]), sha=str(info["sha"]))
        gallery = ROOT / "personas" / p["dir"] / "gallery" / "registry-entry.json"
        if gallery.exists():
            _update_registry_file(gallery, persona=p, version=str(info["version"]), size=int(info["size"]), sha=str(info["sha"]))

    print(f"\nBuilt {len(PERSONAS)} hpersona packages into {DIST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
