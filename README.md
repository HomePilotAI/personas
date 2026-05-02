# HomePilot Personas Pack

This repository contains 10 production-ready **essential personas** for the
HomePilot project plus their external MCP servers. Each persona is packaged
according to the `.hpersona` v2 format, ships an enriched gallery card,
generated avatars and a CI-built distributable zip ready to publish to
[https://ruslanmv.com/HomePilot/gallery.html](https://ruslanmv.com/HomePilot/gallery.html).

## The 10 personas

| ID | Name | Role | Class |
|---|---|---|---|
| `creator-muse` | Creator Muse | Content Creator's Sidekick | muse |
| `style-muse` | Style Muse | Personal Style Curator | stylist |
| `secretary-pro` | Secretary Pro | Executive Secretary | secretary |
| `researcher` | Researcher | Scholarly Research Assistant | scholar |
| `personal-trainer` | Personal Trainer | Strength & Conditioning Coach | coach |
| `room-stylist` | Room Stylist | Interior Design Consultant | designer |
| `storyteller` | Storyteller | Branching Live-Play Director | director |
| `exam-coach` | Exam Coach | Study & Exam Preparation Coach | tutor |
| `mindfulness-coach` | Mindfulness Coach | Mindfulness Guide | coach |
| `general-doctor` | General Doctor | Health Information Companion | advisor |

## Repository structure

- **`personas/`** — One folder per persona with `hpersona/` (package
  contents) and `gallery/` (preview asset + registry entry).
- **`mcp-servers/`** — External MCP servers (`/health` + `/tools`) backing
  each persona.
- **`packages/`** — Shared libraries and tooling.
- **`schemas/`** — JSON schemas for manifests, blueprints and cards.
- **`scripts/`** — Generators and validators (asset, metadata, package, CI).
- **`docs/`** — Architecture, hpersona spec, MCP contract, gallery publishing.
- **`dist/`** — CI build output. `dist/packages/<id>/<version>/persona.hpersona`
  and `dist/previews/<id>/<version>/{preview.webp,card.json}`.
- **`registry/`** — Registry metadata; `registry.json` is in the gallery
  `items[]` shape consumed by `docs/gallery.js`.

## Pipeline

```sh
make install        # Pillow + Node deps
make assets         # render avatars, previews, thumbnails
make metadata       # rebuild card.json, manifests, blueprints, registry entries
make package        # zip into dist/packages/<id>/<version>/persona.hpersona
make validate       # production-readiness checks (must pass)
make all            # assets + metadata + package + validate
```

The same pipeline runs in CI via `.github/workflows/build-personas.yml` and
uploads the `dist/` artifact for gallery publishing.

## Authoring a new persona

1. Append a new entry to `scripts/persona_data.py`.
2. Add a numbered persona folder and a sibling MCP server folder.
3. Run `make all`. Generators write everything else.

## Compatibility with HomePilot Gallery

Each persona's `gallery/registry-entry.json` and the top-level
`registry/registry.json` follow the gallery item contract from
`ruslanmv/HomePilot/docs/gallery.js`:

```json
{
  "id": "...", "name": "...", "short": "...", "author": "...",
  "nsfw": false, "tags": ["..."], "class_id": "...",
  "latest": {
    "version": "1.0.0",
    "preview_url": "previews/<id>/1.0.0/preview.webp",
    "card_url":    "previews/<id>/1.0.0/card.json",
    "package_url": "packages/<id>/1.0.0/persona.hpersona",
    "size_bytes":  123456
  }
}
```

The enriched `preview/card.json` populates the gallery's MMORPG-style
character sheet (stats, style/tone tags, tools, backstory).
