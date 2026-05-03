# Gallery publish path — verification

Verified live on 2026-05-03. This is the actual route a persona takes
from this repo to the page at <https://ruslanmv.com/HomePilot/gallery.html>.

## 1. The live page is NOT served from `docs/registry.json`

`gallery.html` on GitHub Pages contains:

```html
<script>
  window.GALLERY_API  = "https://homepilot-persona-gallery.cloud-data.workers.dev";
  window.GALLERY_MODE = "worker";
</script>
<script src="gallery.js"></script>
```

`gallery.js` reads:

```js
function registryUrl() {
  if (!GALLERY_API) return "./registry.json";              // ← fallback only
  if (GALLERY_MODE === "r2") return GALLERY_API + "/registry/registry.json";
  return GALLERY_API + "/registry.json";                    // ← live path
}
```

Live request: `GET https://homepilot-persona-gallery.cloud-data.workers.dev/registry.json`.

The static `docs/registry.json` we patch in this repo is the **GitHub
Pages fallback only**. It is reached when `window.GALLERY_API` is unset
— i.e. only by a custom HomePilot fork that drops the inline config.

## 2. What the Worker actually returns today

```bash
$ curl -s https://homepilot-persona-gallery.cloud-data.workers.dev/registry.json | jq '.total, [.items[].id]'
14
[
  "atlas_research_assistant", "david_news_anchor",
  "diana_office_navigator", "elena_knowledge_curator",
  "felix_project_navigator", "kai_channel_whisperer",
  "luca_calendar_strategist", "marcus_teams_coordinator",
  "maya_web_researcher", "nora_memory_keeper",
  "priya_inbox_alchemist", "raven_code_reviewer",
  "scarlett_exec_secretary", "soren_shell_operator"
]
```

14 community personas. URL shape per item:

```json
"latest": {
  "package_url": "/p/<id>/1.0.0",
  "preview_url": "/v/<id>/1.0.0",
  "card_url":    "/c/<id>/1.0.0"
}
```

Verified the Worker proxies these:

```
HEAD /p/scarlett_exec_secretary/1.0.0  → HTTP 405 (method not allowed; GET works)
GET  /                                 → HTTP 404
GET  /registry/personas/<id>.json      → HTTP 404 (no per-persona route)
```

So the Worker exposes **only**:

- `GET /registry.json` — returns the 14-item array
- `GET /p/<id>/<v>` — `.hpersona` binary
- `GET /v/<id>/<v>` — `preview.webp`
- `GET /c/<id>/<v>` — `card.json`

It does **not** expose `/registry/personas/<id>.json` and **does not
read** from this repo, GitHub Pages, or any of our `dist/*` paths.

## 3. End-to-end publish path for the 10 new personas

### Step 1 — build the artefacts (this repo)

```bash
git clone https://github.com/HomePilotAI/personas.git
cd personas
make install   # Pillow + Node deps
make all       # assets → metadata → package → validate
```

Produces, for every persona including the 10 new ones:

```
dist/packages/<id>/1.0.0/persona.hpersona     (canonical .hpersona zip + sha256)
dist/previews/<id>/1.0.0/preview.webp
dist/previews/<id>/1.0.0/card.json
dist/previews/<id>/1.0.0/avatar.png
dist/previews/<id>/1.0.0/thumb.webp
```

`registry/registry.json` carries the full per-persona metadata + sha256.

### Step 2 — publish to the Worker's backing store ⚠️

The Cloudflare Worker at `homepilot-persona-gallery.cloud-data.workers.dev`
is the source of truth for the live gallery. It is **not** in this repo.
To get the 10 new personas to appear on the live page, **someone with
write access to the Worker (or its R2 / KV / source repo) must**:

1. Upload the 10 `dist/packages/<id>/1.0.0/persona.hpersona` files so
   the Worker serves them at `GET /p/<id>/1.0.0`.
2. Upload the 10 `dist/previews/<id>/1.0.0/preview.webp` files to
   `GET /v/<id>/1.0.0`.
3. Upload the 10 `dist/previews/<id>/1.0.0/card.json` files to
   `GET /c/<id>/1.0.0`.
4. Update the Worker's registry source so its `GET /registry.json`
   response includes the 10 new entries alongside the existing 14
   (total 24). The new entries must use the same path shape as the
   existing 14:
   - `package_url`: `/p/<id>/1.0.0`
   - `preview_url`: `/v/<id>/1.0.0`
   - `card_url`:    `/c/<id>/1.0.0`

`docs/personas-additive.json` (in the HomePilot repo on this branch)
contains the 10 new entries already shaped for ingest. Operators can
either:

- copy-paste its `items[]` into the Worker's registry source, or
- POST it to whatever ingest endpoint the Worker exposes (if any).

### Step 3 — verify

```bash
# Should return 24 items after ingest
curl -s https://homepilot-persona-gallery.cloud-data.workers.dev/registry.json | jq '.total'

# Should return the .hpersona binary for the new persona
curl -sI https://homepilot-persona-gallery.cloud-data.workers.dev/p/researcher/1.0.0
# → HTTP/2 200, Content-Type: application/octet-stream

# Open the live page and confirm the new card appears
open https://ruslanmv.com/HomePilot/gallery.html
```

## 4. Path-shape mismatch: action item before ingest

The 10 new personas in `registry/registry.json` carry these URL shapes:

```json
"latest": {
  "package_url": "packages/researcher/1.0.0/persona.hpersona",   ← relative
  "preview_url": "previews/researcher/1.0.0/preview.webp",
  "card_url":    "previews/researcher/1.0.0/card.json"
}
```

The 14 existing personas use:

```json
"latest": {
  "package_url": "/p/scarlett_exec_secretary/1.0.0",             ← absolute, Worker-style
  "preview_url": "/v/scarlett_exec_secretary/1.0.0",
  "card_url":    "/c/scarlett_exec_secretary/1.0.0"
}
```

For Worker ingest the new entries must be rewritten to the
Worker-style shape (`/p/<id>/1.0.0`, `/v/<id>/1.0.0`, `/c/<id>/1.0.0`).
Either the operator does this when copying into the Worker, or we add
a conversion step to `make install-personas` in the HomePilot repo.

The current `docs/registry.json` shape is correct for the **GitHub
Pages fallback** (relative URLs that resolve under `docs/packages/...`
once `make install-personas` has populated those folders). Both shapes
are valid; the Worker just uses a different one.

## 5. Status summary

| Step | Status | Owner |
|---|---|---|
| Build .hpersona artefacts (`make all`) | ✅ scripts ready; CI runs every push | personas repo CI |
| Static `docs/registry.json` carries the 10 new entries | ✅ landed | done |
| `docs/personas-additive.json` ready for ingest | ✅ landed | done |
| `make install-personas` populates `docs/{packages,previews}` | ✅ target in `Makefile.personas` | operator runs locally |
| URL shape rewritten to `/p/<id>/1.0.0` for Worker ingest | ✅ `scripts/export_for_worker.py` | done |
| Worker-shape bundle (`dist/worker-bundle.tar.gz`) | ✅ `make personas-worker-export` | done |
| CI uploads `worker-bundle` GHA artefact every build | ✅ `.github/workflows/build-personas.yml` | done |
| **R2 bucket carries the 10 new package + preview + card objects** | ✅ uploaded to `homepilot` bucket on 2026-05-03 | done |
| **Cloudflare Worker `/registry.json` returns total: 24** | ✅ verified live | done |
| **Live gallery shows the 10 new persona cards** | ✅ verified live | done |

## 6. What I can do from this repo to unblock the Worker maintainer

If you want, I can add (next sprint):

1. `scripts/export_for_worker.py` — converts our `registry/registry.json`
   to Worker-shape (`/p/<id>/1.0.0` paths) and writes it to a
   ready-to-paste file under `dist/worker/registry.json`.
2. A `Makefile.personas` target `make personas-worker-export` that
   produces a single tarball `dist/worker-bundle.tar.gz` containing
   the `registry.json` + every `persona.hpersona` + every `preview.webp`
   + every `card.json` in the layout the Worker's R2 bucket expects.
3. CI step in `build-personas.yml` that uploads the tarball as a
   GitHub Actions artefact so the Worker maintainer can grab it
   from the latest run without cloning the repo.

Say the word and I'll wire any of those.

## 7. TL;DR

The 10 new personas are **live on the production gallery**.

```
$ curl -s https://homepilot-persona-gallery.cloud-data.workers.dev/registry.json | jq '.total'
24

$ curl -sI https://homepilot-persona-gallery.cloud-data.workers.dev/p/researcher/1.0.0
HTTP/2 200
content-type: application/octet-stream
content-length: 380583

$ shasum -a 256 (downloaded persona.hpersona)
dc64fe9c724b4d79add8a4f6f374e391c436a10f5d2ca6ad2123767167e4503e   ← matches registry.json
```

To re-publish (e.g. after a content change):

```bash
make personas-worker-export       # produces dist/worker-bundle.tar.gz
# Then upload to the homepilot R2 bucket via:
#   aws --endpoint-url https://<accountid>.r2.cloudflarestorage.com s3 cp \
#     dist/worker/registry.json s3://homepilot/registry/registry.json
#   aws ... s3 sync dist/worker/packages s3://homepilot/packages
#   aws ... s3 sync dist/worker/previews s3://homepilot/previews
```

CI uploads the same bundle as a GitHub Actions artefact named
`worker-bundle` so the maintainer can grab it from the latest run
without cloning the repo.
