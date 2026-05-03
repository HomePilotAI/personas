#!/usr/bin/env python3
"""Generate high-quality persona avatars, previews and thumbnails.

This module is the production replacement for the placeholder stubs that
shipped with the initial repo. Each persona gets a 4:5 portrait built from a
deterministic recipe:

* multi-stop mesh-style gradient sampled from the persona's palette
* layered concentric rings + soft bokeh particles for depth
* glow halo + stroked emoji glyph (or monogram fallback)
* glassmorphism info card with name / role / class badge
* film-grain overlay and edge vignette for a polished cinematic finish

Output sizes are tuned to the gallery's `aspect-ratio: 4/5` cards:

* avatar PNG    1024 x 1280  (high-res, shipped inside .hpersona)
* preview WebP   680 x  850  (gallery card render)
* thumb WebP     256 x  320  (table / list views)
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_data import PERSONAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# ─── colour helpers ───────────────────────────────────────────────────────

def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _darken(c, k: float = 0.55):
    return tuple(int(v * k) for v in c)


def _brighten(c, k: float = 1.25):
    return tuple(min(255, int(v * k)) for v in c)


# ─── background composition ────────────────────────────────────────────────

def _mesh_gradient(size, palette):
    """Build a vibrant mesh-style gradient from the persona's palette."""
    w, h = size
    palette = list(palette)
    while len(palette) < 4:
        palette.append(_brighten(palette[-1], 0.95))

    # Vivid corners — full saturation, generous brightness.
    tl = _brighten(palette[0], 1.30)
    tr = _brighten(palette[1], 1.30)
    bl = _brighten(palette[2], 1.20)
    br = _darken(palette[1], 0.75)

    img = Image.new("RGB", size, tl)
    px = img.load()
    for y in range(h):
        ty = y / (h - 1)
        left = _lerp(tl, bl, ty)
        right = _lerp(tr, br, ty)
        for x in range(w):
            tx = x / (w - 1)
            px[x, y] = _lerp(left, right, tx)

    # Bright elliptical highlight near the upper third.
    highlight = Image.new("L", size, 0)
    hd = ImageDraw.Draw(highlight)
    cx, cy = int(w * 0.5), int(h * 0.34)
    for i in range(40):
        r = int(min(w, h) * (0.62 - i * 0.012))
        if r <= 0:
            break
        alpha = int(160 * (1 - i / 40))
        hd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    highlight = highlight.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 12))
    glow = Image.new("RGB", size, _brighten(palette[1], 1.45))
    img = Image.composite(glow, img, highlight)

    return img


def _bokeh(size, palette, count: int = 50, seed: int = 0):
    rng = random.Random(seed)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = size
    bright = [_brighten(c, 1.4) for c in palette]
    for _ in range(count):
        cx = rng.randint(-50, w + 50)
        cy = rng.randint(-50, h + 50)
        r = rng.randint(int(min(w, h) * 0.02), int(min(w, h) * 0.08))
        col = bright[rng.randint(0, len(bright) - 1)]
        a = rng.randint(40, 95)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, a))
    return layer.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 50))


def _vignette(img, strength: float = 0.35):
    """Apply an edge-darkening vignette. Mask is white in the center
    (preserve original) and fades to dark at the edges."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = w // 2, h // 2
    max_r = max(cx, cy)
    steps = 60
    for i in range(steps):
        # Bright center → dim edges. Largest ellipse first (low alpha),
        # smallest last (full alpha).
        r = int(max_r * (1.0 - i / steps))
        if r <= 0:
            break
        alpha = int(255 * (i / steps))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 12))
    # Lighten the mask so even darkest edges keep some image visible.
    mask = Image.eval(mask, lambda v: int(v * (1.0 - strength) + 255 * strength))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, dark, mask)


def _film_grain(img, strength: int = 8, seed: int = 0):
    rng = random.Random(seed)
    w, h = img.size
    # Lightweight grain: small noise tile resampled for speed.
    tile_w, tile_h = max(1, w // 4), max(1, h // 4)
    noise = Image.new("L", (tile_w, tile_h))
    np = noise.load()
    for y in range(tile_h):
        for x in range(tile_w):
            np[x, y] = 128 + rng.randint(-strength, strength)
    noise = noise.resize((w, h), Image.BILINEAR).convert("RGB")
    return Image.blend(img, noise, 0.06)


# ─── glyph rendering ───────────────────────────────────────────────────────

def _find_emoji_font(size: int):
    for path in (
        "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/opentype/noto/NotoColorEmoji.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return None


def _find_text_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_centred(draw, xy, text, font, fill, stroke_width: int = 0, stroke_fill=None):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    pos = (xy[0] - w // 2 - bbox[0], xy[1] - h // 2 - bbox[1])
    draw.text(pos, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _draw_glyph(persona, base, size):
    """Soft halo + crisp monogram with palette-tinted accent fill."""
    w, h = size
    cx, cy = int(w * 0.5), int(h * 0.40)
    accent = _hex(persona["palette"][0])
    accent_b = _brighten(accent, 1.4)

    # Soft circular medallion behind the monogram for a portrait-like frame.
    medallion = Image.new("RGBA", size, (0, 0, 0, 0))
    md = ImageDraw.Draw(medallion)
    r_outer = int(min(w, h) * 0.28)
    md.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(255, 255, 255, 36))
    medallion = medallion.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 80))
    base.alpha_composite(medallion)

    # Concentric glow halo (palette-tinted, not muddy black).
    halo = Image.new("RGBA", size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    for i in range(22):
        rr = int(min(w, h) * (0.34 - i * 0.011))
        if rr <= 0:
            break
        a = int(110 * (1 - i / 22))
        hd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*accent_b, a), width=3)
    halo = halo.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 60))
    base.alpha_composite(halo)

    monogram = _initials(persona["name"])
    glyph_size = int(min(w, h) * 0.34)
    mono_font = _find_text_font(glyph_size, bold=True)

    # Soft drop shadow that doesn't muddy the fill.
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    _draw_centred(sd, (cx + 6, cy + 10), monogram, mono_font, fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
    base.alpha_composite(shadow)

    # Crisp pure-white monogram (no overpowering stroke).
    glyph = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glyph)
    _draw_centred(gd, (cx, cy), monogram, mono_font, fill=(255, 255, 255, 255))
    base.alpha_composite(glyph)

    # A thin tinted accent line under the monogram for personality.
    accent_line = Image.new("RGBA", size, (0, 0, 0, 0))
    ad = ImageDraw.Draw(accent_line)
    line_y = cy + int(glyph_size * 0.65)
    line_w = int(w * 0.18)
    ad.rounded_rectangle([cx - line_w, line_y, cx + line_w, line_y + 6], radius=3, fill=(*accent_b, 220))
    base.alpha_composite(accent_line)

    # Tiny circular badge top-right with the persona emoji (or class initial).
    emoji_font = _find_emoji_font(int(min(w, h) * 0.055))
    badge_r = int(min(w, h) * 0.055)
    bx, by = int(w * 0.84), int(h * 0.10)
    badge = Image.new("RGBA", size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r], fill=(*_darken(accent, 0.35), 220), outline=(255, 255, 255, 200), width=3)
    if emoji_font is not None:
        try:
            _draw_centred(bd, (bx, by), persona["emoji"], emoji_font, fill=(255, 255, 255, 240))
        except Exception:
            pass
    base.alpha_composite(badge)


# ─── glassmorphism info card ───────────────────────────────────────────────

def _draw_info_card(persona, base, size):
    w, h = size
    card_h = int(h * 0.30)
    card = Image.new("RGBA", (w, card_h), (0, 0, 0, 0))

    # Frosted glass: dark gradient + subtle blur of the underlying area.
    region = base.crop((0, h - card_h, w, h)).filter(ImageFilter.GaussianBlur(radius=18))
    base.paste(region, (0, h - card_h))

    overlay = Image.new("RGBA", (w, card_h), (10, 10, 18, 175))
    od = ImageDraw.Draw(overlay)
    for y in range(card_h):
        a = int(140 + (115 * y / card_h))
        od.line([(0, y), (w, y)], fill=(10, 10, 18, min(a, 220)))
    card.alpha_composite(overlay)

    # Top hairline
    od2 = ImageDraw.Draw(card)
    od2.line([(int(w * 0.06), 0), (int(w * 0.94), 0)], fill=(255, 255, 255, 80), width=2)

    # Text
    name_font = _find_text_font(int(h * 0.058), bold=True)
    role_font = _find_text_font(int(h * 0.030), bold=False)
    class_font = _find_text_font(int(h * 0.020), bold=True)

    cx = w // 2
    _draw_centred(od2, (cx, int(card_h * 0.30)), persona["name"], name_font, fill=(255, 255, 255, 250))
    _draw_centred(od2, (cx, int(card_h * 0.55)), persona["role"], role_font, fill=(220, 220, 230, 230))

    # Class badge
    badge_text = persona["class_id"].upper()
    bbox = od2.textbbox((0, 0), badge_text, font=class_font)
    bw = bbox[2] - bbox[0] + int(w * 0.05)
    bh = bbox[3] - bbox[1] + int(h * 0.018)
    bx = (w - bw) // 2
    by = int(card_h * 0.78) - bh // 2
    accent = _hex(persona["palette"][0])
    od2.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=(*accent, 90), outline=(*_brighten(accent, 1.2), 230), width=2)
    _draw_centred(od2, (cx, by + bh // 2), badge_text, class_font, fill=(255, 255, 255, 240))

    base.paste(card, (0, h - card_h), card)


# ─── stat pips (MMORPG accent) ─────────────────────────────────────────────

def _draw_stat_pips(persona, base, size):
    w, h = size
    d = ImageDraw.Draw(base, "RGBA")
    pip_y = int(h * 0.65)
    stats = persona["stats"]
    keys = ["charisma", "elegance", "confidence", "warmth"]
    accent = _hex(persona["palette"][1])
    for i, k in enumerate(keys):
        v = stats.get(k, 50)
        bar_w = int(w * 0.10)
        bar_h = max(4, int(h * 0.005))
        x0 = int(w * 0.08) + i * int(w * 0.21)
        y0 = pip_y
        d.rounded_rectangle([x0, y0, x0 + bar_w, y0 + bar_h], radius=bar_h, fill=(255, 255, 255, 60))
        d.rounded_rectangle([x0, y0, x0 + int(bar_w * v / 100), y0 + bar_h], radius=bar_h, fill=(*_brighten(accent, 1.15), 220))


# ─── high-level render ─────────────────────────────────────────────────────

def render_avatar(persona: dict, out_path: Path, size: tuple[int, int] = (1024, 1280)) -> None:
    palette = [_hex(c) for c in persona["palette"]]
    while len(palette) < 4:
        palette.append(_darken(palette[-1], 0.65))

    bg = _mesh_gradient(size, palette)
    base = bg.convert("RGBA")
    base.alpha_composite(_bokeh(size, palette, count=60, seed=hash(persona["id"]) & 0xFFFF))

    _draw_glyph(persona, base, size)
    _draw_stat_pips(persona, base, size)
    _draw_info_card(persona, base, size)

    rgb = base.convert("RGB")
    rgb = _vignette(rgb, strength=0.18)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(out_path, "PNG", optimize=True)


def render_preview(persona: dict, out_path: Path, size: tuple[int, int] = (680, 850)) -> None:
    tmp = Path("/tmp/_persona_preview.png")
    render_avatar(persona, tmp, (size[0] * 2, size[1] * 2))
    img = Image.open(tmp).convert("RGB").resize(size, Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=90, method=6)


def render_thumb(persona: dict, out_path: Path, size: tuple[int, int] = (256, 320)) -> None:
    tmp = Path("/tmp/_persona_thumb.png")
    render_avatar(persona, tmp, (size[0] * 4, size[1] * 4))
    img = Image.open(tmp).convert("RGB").resize(size, Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=88, method=6)


def main() -> int:
    # Stub-size thresholds: anything larger is treated as a real asset
    # (realistic photo OR a previously-rendered branded placeholder) and
    # left alone. CI re-runs must NEVER overwrite committed photos —
    # delete the file on disk to force a re-render.
    AVATAR_KEEP_BYTES = 5_000   # validate_personas.py minimum
    THUMB_KEEP_BYTES = 2_000
    PREVIEW_KEEP_BYTES = 2_000  # validate_personas.py minimum
    force = os.environ.get("FORCE_REGEN_ASSETS", "").lower() in {"1", "true", "yes"}

    def _keep(path: Path, min_bytes: int) -> bool:
        return (not force) and path.exists() and path.stat().st_size >= min_bytes

    for persona in PERSONAS:
        pdir = ROOT / "personas" / persona["dir"] / "hpersona" / "assets"
        gdir = ROOT / "personas" / persona["dir"] / "gallery"
        avatar_path = pdir / f"avatar_{persona['id']}.png"
        thumb_path = pdir / f"thumb_avatar_{persona['id']}.webp"
        preview_path = gdir / "preview.webp"

        if _keep(avatar_path, AVATAR_KEEP_BYTES):
            print(f"[{persona['id']}] avatar — keep ({avatar_path.stat().st_size}B)")
        else:
            print(f"[{persona['id']}] avatar")
            render_avatar(persona, avatar_path)
        if _keep(thumb_path, THUMB_KEEP_BYTES):
            print(f"[{persona['id']}] thumb — keep ({thumb_path.stat().st_size}B)")
        else:
            print(f"[{persona['id']}] thumb")
            render_thumb(persona, thumb_path)
        if _keep(preview_path, PREVIEW_KEEP_BYTES):
            print(f"[{persona['id']}] preview — keep ({preview_path.stat().st_size}B)")
        else:
            print(f"[{persona['id']}] preview")
            render_preview(persona, preview_path)

    print("\nGenerated production assets for", len(PERSONAS), "personas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
