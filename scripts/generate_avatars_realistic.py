#!/usr/bin/env python3
"""Regenerate persona avatars with high-quality, photorealistic synthetic
faces — mirroring the HomePilot avatar-service quickface pipeline.

Fallback chain (matches avatar-service/app/quickface_router.py):

  1. Local StyleGAN2 model — used when STYLEGAN_ENABLED=true and the
     weights pickle is reachable. Produces deterministic faces from a
     persona-keyed seed so re-runs are reproducible.

  2. thispersondoesnotexist.com web fallback — fetches one synthetic
     1024×1024 face per call. Disabled in CI (no outbound). Set
     ENABLE_WEB_FACES=true to opt in locally. Each persona gets a
     different face on each rerun by design — cache the output to
     keep the same face across re-runs.

  3. Pillow placeholder via scripts/generate_assets.py — the existing
     gradient + emoji + info-card composition. Used in CI and any
     environment without StyleGAN weights or outbound HTTPS.

Per persona we always produce:

  personas/<dir>/hpersona/assets/avatar_<id>.png       (1024 × 1280)
  personas/<dir>/hpersona/assets/thumb_avatar_<id>.webp (256 × 320)
  personas/<dir>/gallery/preview.webp                   (680 × 850)

The realistic face is composited onto the same gradient background,
glassmorphism info card, and stat pip strip the placeholder pipeline
already produces — so the gallery card stays branded even when the
face source flips between local model / web / placeholder.

Use:

    # default: web fetch when ENABLE_WEB_FACES=true, otherwise placeholder
    python3 scripts/generate_avatars_realistic.py

    # only the new 10 personas, never touching the existing community
    # entries (Scarlett / Atlas / David Mercer / etc.)
    PERSONA_IDS=creator-muse,style-muse,researcher \\
      python3 scripts/generate_avatars_realistic.py

    # use the StyleGAN2 model
    STYLEGAN_ENABLED=true STYLEGAN_WEIGHTS_PATH=/path/to/model.pkl \\
      python3 scripts/generate_avatars_realistic.py

    # opt into the web fallback (writes cached jpgs in .cache/faces/)
    ENABLE_WEB_FACES=true python3 scripts/generate_avatars_realistic.py
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

# Reuse the existing pipeline for the gradient background, info card, etc.
import generate_assets as _ga  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache" / "faces"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WEB_URL = "https://thispersondoesnotexist.com"
WEB_UA = "HomePilot-Personas/1.0"
WEB_TIMEOUT_S = 20

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("avatars")


def _persona_seed(persona: dict) -> int:
    """Stable per-persona seed for the StyleGAN2 path."""
    h = hashlib.sha256(persona["id"].encode()).hexdigest()
    return int(h[:16], 16)


# ── Strategy 1: local StyleGAN2 ────────────────────────────────────────────


def _stylegan_face(persona: dict) -> Image.Image | None:
    """Return a PIL face from the local StyleGAN2 model, or None if unavailable.

    Mirrors avatar-service/app/stylegan/generator.py. The actual model
    loading is intentionally lazy — we don't want the import path to fail
    when the operator hasn't set up StyleGAN.
    """
    if os.getenv("STYLEGAN_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from stylegan.generator import generate_face  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        log.warning("stylegan path requested but unavailable: %s", exc)
        return None
    try:
        return generate_face(seed=_persona_seed(persona))
    except Exception as exc:  # pragma: no cover
        log.warning("stylegan generation failed for %s: %s", persona["id"], exc)
        return None


# ── Strategy 2: thispersondoesnotexist.com (cached) ────────────────────────


def _web_face(persona: dict) -> Image.Image | None:
    """Fetch a synthetic face from thispersondoesnotexist.com.

    Cached on disk under .cache/faces/<id>.jpg so re-runs reuse the same
    face per persona. Delete the cache file to force a fresh fetch.
    Returns None when the network is unreachable, the response is not a
    JPEG, or ENABLE_WEB_FACES is unset.
    """
    if os.getenv("ENABLE_WEB_FACES", "").lower() not in {"1", "true", "yes"}:
        return None

    cache_path = CACHE_DIR / f"{persona['id']}.jpg"
    if cache_path.exists() and cache_path.stat().st_size > 0:
        log.info("web face cache hit %s (%d bytes)", cache_path.name, cache_path.stat().st_size)
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception as exc:  # pragma: no cover
            log.warning("could not read cached face %s: %s", cache_path, exc)

    log.info("fetching %s for %s", WEB_URL, persona["id"])
    req = urllib.request.Request(WEB_URL, headers={"User-Agent": WEB_UA})
    try:
        with urllib.request.urlopen(req, timeout=WEB_TIMEOUT_S) as resp:
            data = resp.read()
    except Exception as exc:  # pragma: no cover
        log.warning("web fetch failed for %s: %s", persona["id"], exc)
        return None

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        log.warning("web response was not a valid image for %s: %s", persona["id"], exc)
        return None
    if img.format not in {"JPEG", "PNG", "WEBP"}:
        log.warning("unexpected image format %s for %s", img.format, persona["id"])
        return None

    cache_path.write_bytes(data)
    log.info("cached %d bytes -> %s", len(data), cache_path)
    # Throttle a tiny bit so we don't hammer the upstream when running
    # the full 10-persona sweep.
    time.sleep(0.2)
    return img.convert("RGB")


# ── Composition: face on top of the existing branded background ────────────


def _crop_to_portrait(face: Image.Image, portrait_size: tuple[int, int]) -> Image.Image:
    """Resize+crop the square face to fill the full portrait aspect.

    The face fills the whole frame — no info card, no stat strip, no
    name/role text. The frontend gallery renders the persona name + role
    + class badge in its own UI; we don't want a second copy of that
    text inside the image, fighting with it visually.
    """
    pw, ph = portrait_size
    fw, fh = face.size
    # Cover-fit: scale so the face fills the portrait short axis, then
    # crop the long axis center-out (slightly top-biased so chins land
    # below the vertical midline).
    scale = max(pw / fw, ph / fh)
    new_w = max(pw, int(fw * scale))
    new_h = max(ph, int(fh * scale))
    face = face.resize((new_w, new_h), Image.Resampling.LANCZOS)
    fx = max(0, (new_w - pw) // 2)
    fy = max(0, (new_h - ph) // 3)
    return face.crop((fx, fy, fx + pw, fy + ph))


def _round_face_mask(size: tuple[int, int]) -> Image.Image:
    """Soft-edged elliptical mask used by the legacy branded composite."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    pad = int(min(size) * 0.06)
    draw.ellipse((pad, pad, size[0] - pad, size[1] - pad), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=int(min(size) * 0.04)))


def _compose_photo_only(
    persona: dict, face: Image.Image, size: tuple[int, int] = (1024, 1280)
) -> Image.Image:
    """Default: raw face, no overlaid text and no vignette.

    The HomePilot gallery's frontend (gallery.js + card template) already
    renders persona name, role, class badge and stats next to the image,
    so duplicating them inside the picture would double up visually. We
    also leave the photo untouched (no vignette / film grain / glow) so
    it ships as the original synthetic face — the upstream source is
    already lit and toned, and the gallery card has its own background
    that any darkening would fight with. Used when ``AVATAR_STYLE`` is
    unset or set to ``photo``.
    """
    return _crop_to_portrait(face, size).convert("RGB")


def _compose_branded(
    persona: dict, face: Image.Image, size: tuple[int, int] = (1024, 1280)
) -> Image.Image:
    """Optional: legacy composite with mesh gradient + info card + stat pips.

    Available behind ``AVATAR_STYLE=branded`` for callers that want the
    fully-rendered marketing card (e.g. for screenshots, social previews,
    or environments where the gallery frontend isn't doing its own
    typography). The 1024×1280 PNG carries the persona name / role /
    class badge / stat strip baked in.
    """
    palette = [_ga._hex(c) for c in persona["palette"]]
    while len(palette) < 4:
        palette.append(_ga._darken(palette[-1], 0.65))

    # _mesh_gradient returns RGB; convert to RGBA so subsequent
    # alpha_composite calls work (matches render_avatar in generate_assets).
    base = _ga._mesh_gradient(size, palette).convert("RGBA")
    base.alpha_composite(_ga._bokeh(size, palette, count=60, seed=hash(persona["id"]) & 0xFFFF))

    # The face occupies the upper 62% of the portrait, leaving room
    # for the info card the existing pipeline draws below.
    face_h = int(size[1] * 0.62)
    face_w = size[0]
    cropped = _crop_to_portrait(face, (face_w, face_h))
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.paste(cropped.convert("RGB"), (0, 0), _round_face_mask((face_w, face_h)))

    # Soft glow halo behind the face for depth.
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = size[0] // 2, int(face_h * 0.55)
    radius = int(min(size) * 0.45)
    accent = _ga._brighten(palette[0], 1.2)
    gd.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(*accent, 90),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=int(min(size) * 0.06)))
    base.alpha_composite(glow)
    base.alpha_composite(layer)

    # Reuse the existing info card + stat strip.
    _ga._draw_info_card(persona, base, size)
    _ga._draw_stat_pips(persona, base, size)

    # _vignette returns RGB; apply after the convert.
    rgb = base.convert("RGB")
    return _ga._vignette(rgb, strength=0.18)


def _compose(
    persona: dict, face: Image.Image, size: tuple[int, int] = (1024, 1280)
) -> Image.Image:
    """Pick the active composite style based on the AVATAR_STYLE env var."""
    style = os.getenv("AVATAR_STYLE", "photo").strip().lower()
    if style in {"branded", "card", "legacy"}:
        return _compose_branded(persona, face, size)
    # Default: photo-only.
    return _compose_photo_only(persona, face, size)


def _compose_branded_avatar(persona: dict, face: Image.Image, size=(1024, 1280)) -> Image.Image:
    """Backwards-compatible alias for any caller that imported the old name."""
    return _compose(persona, face, size)
    rgb = _ga._vignette(rgb, strength=0.18)
    return rgb


# ── Strategy 3: Pillow placeholder fallback ────────────────────────────────


def _placeholder_avatar(persona: dict, size: tuple[int, int] = (1024, 1280)) -> Image.Image:
    """Fallback: the existing gradient + emoji glyph + info card composition."""
    out = ROOT / ".cache" / "_placeholder.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    _ga.render_avatar(persona, out, size)
    return Image.open(out).convert("RGB")


# ── Top-level pipeline ─────────────────────────────────────────────────────


def render_for(persona: dict) -> tuple[Image.Image, str]:
    """Pick the best available source and return (PIL-image, source-tag)."""
    face = _stylegan_face(persona)
    if face is not None:
        return _compose_branded_avatar(persona, face), "stylegan2"
    face = _web_face(persona)
    if face is not None:
        return _compose_branded_avatar(persona, face), "thispersondoesnotexist"
    return _placeholder_avatar(persona), "placeholder"


def _selected_personas() -> list[dict]:
    """Honour PERSONA_IDS=… so operators can target only the new pack."""
    raw = os.getenv("PERSONA_IDS", "").strip()
    if not raw:
        return list(PERSONAS)
    wanted = {x.strip() for x in raw.split(",") if x.strip()}
    return [p for p in PERSONAS if p["id"] in wanted]


def main() -> int:
    selected = _selected_personas()
    if not selected:
        log.error("no personas matched PERSONA_IDS=%r", os.getenv("PERSONA_IDS"))
        return 1
    log.info("rendering %d persona(s)", len(selected))

    for persona in selected:
        pdir = ROOT / "personas" / persona["dir"] / "hpersona" / "assets"
        gdir = ROOT / "personas" / persona["dir"] / "gallery"
        pdir.mkdir(parents=True, exist_ok=True)
        gdir.mkdir(parents=True, exist_ok=True)

        avatar, source = render_for(persona)
        avatar_path = pdir / f"avatar_{persona['id']}.png"
        thumb_path = pdir / f"thumb_avatar_{persona['id']}.webp"
        preview_path = gdir / "preview.webp"

        avatar.save(avatar_path, "PNG", optimize=True)
        avatar.resize((680, 850), Image.Resampling.LANCZOS).save(
            preview_path, "WEBP", quality=90, method=6
        )
        avatar.resize((256, 320), Image.Resampling.LANCZOS).save(
            thumb_path, "WEBP", quality=88, method=6
        )
        log.info("[%s] source=%s avatar=%s", persona["id"], source, avatar_path.name)

    print(f"\nRendered {len(selected)} persona avatar(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
