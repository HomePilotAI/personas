# `generate_avatars_realistic.py` — quick reference

Photorealistic persona avatars on demand. Mirrors HomePilot's
[`avatar-service/app/quickface_router.py`](https://github.com/ruslanmv/HomePilot/blob/master/avatar-service/app/quickface_router.py)
fallback chain.

## Fallback order

1. **Local StyleGAN2** — used when `STYLEGAN_ENABLED=true` and weights
   are reachable. Deterministic per persona (seed = SHA-256(id)).
2. **`thispersondoesnotexist.com`** — opt-in via `ENABLE_WEB_FACES=true`.
   1024 × 1024 random face per call. Cached per persona at
   `.cache/faces/<id>.jpg`. Each persona gets a different face on
   first fetch; later runs reuse the cached file.
3. **Pillow placeholder** — the default `scripts/generate_assets.py`
   gradient + emoji + info-card composition. Used in CI and any
   environment without StyleGAN weights or outbound HTTPS.

The chosen face is composited onto the same branded background
(palette mesh gradient, bokeh, glassmorphism info card, stat pip strip,
soft vignette) so the gallery card stays consistent regardless of
source.

## Outputs (per persona)

```
personas/<dir>/hpersona/assets/avatar_<id>.png       1024 × 1280
personas/<dir>/hpersona/assets/thumb_avatar_<id>.webp 256 × 320
personas/<dir>/gallery/preview.webp                   680 × 850
```

## Common recipes

### Sweep every persona (default)

```bash
python3 scripts/generate_avatars_realistic.py
```

Without `ENABLE_WEB_FACES`, the placeholder strategy runs — same as
`scripts/generate_assets.py`.

### Sweep only specific personas

```bash
PERSONA_IDS=creator-muse,style-muse,researcher \
  python3 scripts/generate_avatars_realistic.py
```

`PERSONA_IDS` is a comma-separated allow-list. Used during the
audit pass to re-roll just the faces that needed it without
touching the others.

### Use thispersondoesnotexist faces

```bash
ENABLE_WEB_FACES=true PERSONA_IDS=creator-muse \
  python3 scripts/generate_avatars_realistic.py
```

First fetch caches at `.cache/faces/<id>.jpg`. Re-runs reuse the cache
and don't hit the network.

### Re-roll a face you don't like

```bash
rm .cache/faces/<id>.jpg
ENABLE_WEB_FACES=true PERSONA_IDS=<id> \
  python3 scripts/generate_avatars_realistic.py
```

Repeat until the new face passes your audit (gender / age / fit).

### Use the local StyleGAN2 model

```bash
STYLEGAN_ENABLED=true \
STYLEGAN_WEIGHTS_PATH=/path/to/stylegan2-ffhq-1024.pkl \
  python3 scripts/generate_avatars_realistic.py
```

Requires `pip install stylegan2-pytorch` (or the equivalent module
exposed as `stylegan.generator`). Output is deterministic across runs
because the seed is derived from the persona id.

## Audit checklist before committing avatars

For every persona you touched:

```
[ ] Avatar is clearly an adult (no children / minors).
[ ] Gender matches the persona's backstory pronouns:
      creator-muse / style-muse / secretary-pro → 'she'  → adult ♀
      everyone else                              → neutral, any
[ ] Face fits the persona vibe (e.g. exam-coach feels like a teacher,
    general-doctor feels approachable, etc.).
[ ] No sensitive content visible (text, branding, identifying marks).
```

Failed any box → delete `.cache/faces/<id>.jpg` and re-roll.

## Adding a new persona

1. Add the persona row to `scripts/persona_data.py` (id, name, palette,
   stats, etc.).
2. Run `python3 scripts/generate_assets.py` once to build the
   placeholder gradient version (used when web/StyleGAN unavailable).
3. Run `ENABLE_WEB_FACES=true PERSONA_IDS=<new-id>
   python3 scripts/generate_avatars_realistic.py` to generate a
   realistic face for the new persona only.
4. Audit the result (see checklist above). Re-roll if needed.
5. Commit the resulting `avatar_<id>.png`, `thumb_avatar_<id>.webp`,
   `preview.webp` files plus the new `.cache/faces/<id>.jpg` (so
   future runs don't have to re-fetch).

## Env-var summary

| Variable | Default | Purpose |
|---|---|---|
| `PERSONA_IDS` | (all) | Comma-separated allow-list of persona ids. |
| `ENABLE_WEB_FACES` | `false` | Opt into thispersondoesnotexist.com fetches. |
| `STYLEGAN_ENABLED` | `false` | Opt into the local StyleGAN2 path. |
| `STYLEGAN_WEIGHTS_PATH` | – | Path to the StyleGAN2 weights pickle. |
| `LOG_LEVEL` | `INFO` | Standard Python log level. |

## Notes & caveats

- **Production posture**: web fetch is fine for development / one-off
  asset regeneration. For production rebuilds, use the local StyleGAN2
  path so the build is reproducible and not dependent on the
  thispersondoesnotexist.com endpoint.
- **Throttling**: a 0.2 s sleep is applied between web fetches so
  sweeping all 10 personas doesn't hammer the upstream.
- **Cache invalidation**: deleting `.cache/faces/<id>.jpg` is the
  only way to force a fresh fetch. The script never deletes its own
  cache.
- **Existing community personas** (Scarlett, Atlas, David Mercer, etc.)
  are NOT in this repo and are NOT touched by this script.
- **Strategy choice in audit logs**: the script logs `source=stylegan2 |
  thispersondoesnotexist | placeholder` per persona so you can see
  which strategy fired without inspecting the file.
