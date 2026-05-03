# HomePilot Personas

**Official External Additive Personas for [HomePilot](https://github.com/ruslanmv/HomePilot).**

This repository ships the 10 production personas that extend HomePilot, the
external MCP servers that back them, and the safety, governance and tooling
required to run them in production. Personas are packaged as `.hpersona` v2
bundles and published to the [HomePilot Community Gallery](https://ruslanmv.com/HomePilot/gallery.html).

| | |
|---|---|
| **Status** | Production. 10 personas, 10 real MCP servers, 24 canonical tools, 207 platform tests. |
| **License** | Apache-2.0 |
| **MCP transports** | `stdio` and Streamable HTTP `/mcp` |
| **Languages** | Node.js (8 servers) + Python FastMCP (2 servers) |
| **Compatible with** | [MCP Inspector](https://ibm.github.io/mcp-context-forge/using/clients/mcp-inspector/), [MCP Context Forge](https://github.com/IBM/mcp-context-forge), HomePilot Community Gallery |

---

## Table of Contents

1. [What ships in this repo](#what-ships-in-this-repo)
2. [Architecture](#architecture)
3. [Quick start](#quick-start)
4. [The 10 personas](#the-10-personas)
5. [MCP server matrix](#mcp-server-matrix)
6. [Safety and compliance](#safety-and-compliance)
7. [Project structure](#project-structure)
8. [Development workflow](#development-workflow)
9. [Testing](#testing)
10. [Deployment](#deployment)
11. [HomePilot Gallery publishing](#homepilot-gallery-publishing)
12. [Adding a new persona](#adding-a-new-persona)
13. [Adding a new MCP tool](#adding-a-new-mcp-tool)
14. [Documentation index](#documentation-index)
15. [Contributing](#contributing)
16. [License](#license)

---

## What ships in this repo

This is a single, batteries-included pack designed for HomePilot operators
and contributors:

- **10 persona bundles** (`personas/`) — `.hpersona` v2 packages with
  manifest, blueprint (system prompt, agent config, appearance), declared
  tool dependencies, MCP server dependency, gallery preview, and avatar
  assets. Each bundle is independently installable into HomePilot.
- **10 real MCP servers** (`mcp-servers/`) — JSON-RPC over MCP, **not**
  REST. Eight Node servers built on `@modelcontextprotocol/sdk` via the
  shared `node_common` framework, two Python servers built on `FastMCP`
  (Researcher and General Doctor). Every server speaks both `stdio` (for
  MCP Inspector and local development) and Streamable HTTP `/mcp` (for
  Context Forge federation and Docker deployment).
- **A shared Node MCP framework** (`mcp-servers/node_common/`) — server
  factory, both transports, response/error helpers, reusable Zod schema
  fragments, and a protocol test harness so adding a server is a small,
  uniform change.
- **A medical safety adapter** (`mcp-servers/10-mcp-general-doctor/`) —
  Python FastMCP adapter on top of the upstream
  [`medical-mcp-toolkit`](https://github.com/ruslanmv/medical-mcp-toolkit),
  with red-flag detection, output filtering, no-PHI audit logging, and a
  rollback kill-switch. Backed by a six-document medical AI governance
  policy aligned to WHO, EU AI Act, FDA PCCP, CHAI and AMA guidance.
- **CI-built distributables** (`dist/`) — zipped persona packages and
  gallery preview/card artefacts produced by
  `.github/workflows/build-personas.yml`.
- **Drift-detecting validators** (`scripts/validate_personas.py`,
  `scripts/validate_mcp_servers.py`) — fail CI when persona JSON, server
  contracts, or implemented MCP tools fall out of sync.
- **Inspector configurations** (`configs/inspector/`) — drop-in configs
  for stdio and Streamable HTTP modes, per-server and bundled.
- **Migration history** (`docs/migration/`) — the architectural decisions
  behind the platform, server-by-server, with batch-by-batch acceptance
  criteria.

---

## Architecture

```
                      ┌──────────────────────────────┐
                      │  HomePilot Community Gallery │
                      │ ruslanmv.com/HomePilot/...   │
                      └──────────────┬───────────────┘
                                     │ registry.json + .hpersona bundles
                                     ▼
       ┌───────────────────────────────────────────────────────┐
       │                 personas/   ←  this repo              │
       │  10 .hpersona v2 bundles (manifest, blueprint, deps)  │
       └───────────────────────────────────────────────────────┘
                                     │ each persona declares an MCP server
                                     ▼
       ┌───────────────────────────────────────────────────────┐
       │              mcp-servers/   ←  this repo              │
       │  Real MCP (JSON-RPC) over stdio + Streamable HTTP     │
       │                                                       │
       │   01 creator-muse        06 room-stylist              │
       │   02 style-muse          07 storyteller               │
       │   03 secretary-pro       08 exam-coach                │
       │   05 personal-trainer    09 mindfulness-coach         │
       │   ──── Node + node_common framework ────              │
       │                                                       │
       │   04 researcher          10 general-doctor            │
       │   ──── Python FastMCP ────                            │
       └──────┬─────────────────────────────────────┬──────────┘
              │                                     │
              ▼                                     ▼
   arXiv API (search_arxiv,           medical-mcp-toolkit (upstream)
   read_paper, summarize_paper)        triageSymptoms, searchMedicalKB
                                       — exposed via safety adapter only
```

**Two principles run through the platform:**

1. **Safety lives in the adapter.** Every wellness, medical, exam-coach,
   and storyteller tool has a guardrail layer in its `src/safety.js`
   (or `src/doctor/safety.py`). User input is screened *before* upstream
   calls; upstream output is filtered *after*. Refusals are non-shaming
   and offer a redirect.
2. **The MCP contract is enforced in CI.** `validate_mcp_servers.py`
   fails when `server.json`, `tools.js`, and the implemented MCP tools
   drift apart. No silent contract breakage between commits.

---

## Quick start

### Prerequisites

- Node.js 22+
- Python 3.11+
- `npm`, `pip`

### Install

```bash
git clone https://github.com/HomePilotAI/personas.git
cd personas

# Install Node workspace deps (MCP SDK, zod, express)
npm install

# Install Python persona dependencies (researcher + doctor adapters)
pip install -e mcp-servers/04-mcp-researcher
pip install -e mcp-servers/10-mcp-general-doctor

# Install asset/metadata pipeline deps
pip install -r requirements.txt
```

### Validate

```bash
npm test
# Runs:
#   python3 scripts/validate_personas.py     → 10 personas valid
#   python3 scripts/validate_mcp_servers.py  → 10/10 strict-PASS
```

### Run a single persona MCP server (stdio)

```bash
# Node persona, e.g. creator-muse
node mcp-servers/01-mcp-creator-muse/src/index.js

# Python persona, e.g. researcher
python -m researcher.server --transport stdio
```

### Connect MCP Inspector

```bash
npx @modelcontextprotocol/inspector --config configs/inspector/all-stdio.json
```

Inspector now lists every tool from every server and lets you call them
with the declared input schemas.

### Run everything in containers

```bash
docker compose -f docker-compose.mcp.yml up
```

Each server listens on its assigned port (`9101`–`9110`). The Researcher
and General Doctor servers run as their own Python images; the rest run
as the Node service from the repo root.

---

## The 10 personas

| # | ID | Name | Role | Class | NSFW | Canonical tools |
|---|---|---|---|---|---|---|
| 01 | `creator-muse` | Creator Muse | Content Creator's Sidekick | muse | – | `creator_muse_inspire` |
| 02 | `style-muse` | Style Muse | Personal Style Curator | stylist | – | `style_muse_outfit`, `style_muse_variant` |
| 03 | `secretary-pro` | Secretary Pro | Executive Secretary | secretary | – | `secretary_schedule`, `secretary_remind`, `secretary_triage` |
| 04 | `researcher` | Researcher | Scholarly Research Assistant | scholar | – | `search_arxiv`, `read_paper`, `summarize_paper`, `compare_papers`, `build_literature_brief` |
| 05 | `personal-trainer` | Personal Trainer | Strength & Conditioning Coach | coach | – | `trainer_workout_plan`, `trainer_recovery_check`, `trainer_streak` |
| 06 | `room-stylist` | Room Stylist | Interior Design Consultant | designer | – | `room_layout`, `room_palette`, `room_shopping_list` |
| 07 | `storyteller` | Storyteller | Branching Live-Play Director | director | – | `story_scene`, `story_choice`, `story_ending` |
| 08 | `exam-coach` | Exam Coach | Study & Exam Preparation Coach | tutor | – | `exam_question`, `exam_plan`, `exam_explain` |
| 09 | `mindfulness-coach` | Mindfulness Coach | Mindfulness Guide | coach | – | `mindfulness_meditation`, `mindfulness_grounding`, `mindfulness_focus` |
| 10 | `general-doctor` | General Doctor | General Health Information Companion | advisor | – | `doctor_red_flags`, `doctor_general_info`, `doctor_self_care` |

All personas are SFW. Total: 24 canonical tools across 10 servers.

---

## MCP server matrix

| Server | Port | Lang | Stack | Safety guardrail | Tests |
|---|---|---|---|---|---|
| `mcp-creator-muse` | 9101 | Node | `node_common` | – | 9 |
| `mcp-style-muse` | 9102 | Node | `node_common` | – | 12 |
| `mcp-secretary-pro` | 9103 | Node | `node_common` | Draft-only (never sends, never books) | 15 |
| `mcp-researcher` | 9104 | Python | FastMCP | – | 19 |
| `mcp-personal-trainer` | 9105 | Node | `node_common` | Red-flag medical escalation | 19 |
| `mcp-room-stylist` | 9106 | Node | `node_common` | – | 13 |
| `mcp-storyteller` | 9107 | Node | `node_common` | Content red lines (no minors / no atrocity / no hate) | 25 |
| `mcp-exam-coach` | 9108 | Node | `node_common` | Academic integrity (no live-exam help, no answer-only mode) | 22 |
| `mcp-mindfulness-coach` | 9109 | Node | `node_common` | Mental-health crisis escalation (US 988 / UK Samaritans / AU Lifeline) | 20 |
| `mcp-general-doctor` | 9110 | Python | FastMCP + safety adapter | Full medical safety policy (red-flag screen, output filter, no PHI, audit log) | 46 |

Total: **207 platform tests**, all passing.

Every server speaks the same MCP protocol. Inputs are validated by Zod
(Node) or Pydantic (Python) before reaching the handler. Outputs are MCP
content blocks (`text` blocks containing JSON for structured payloads).

---

## Safety and compliance

This pack is intended to be embedded in user-facing products. Five distinct
guardrail patterns are in production today, each in its server's
`src/safety.{js,py}`:

| Pattern | Where | What it does |
|---|---|---|
| **Draft-only** | secretary-pro | Never sends a message or commits a calendar entry; every output is a draft envelope the caller commits. |
| **Red-flag medical escalation** | personal-trainer, mindfulness-coach | Sweeps free text for symptom red flags; replaces the response with an escalation envelope and crisis-line resources. |
| **Content red lines** | storyteller | Refuses sexual/violent content involving minors, hateful content targeting protected groups, and atrocity-as-instruction. Refusal copy is non-shaming and offers a redirect. |
| **Academic integrity** | exam-coach | Refuses help on actively-administered exams; refuses "answer-only" requests — every answer ships with an explanation. |
| **Full medical safety adapter** | general-doctor | 33-pattern red-flag detector + 5-category output filter + bearer-authed upstream + no-PHI audit log + adapter kill-switch. |

### Medical AI governance

The General Doctor adapter follows industry-aligned health-AI guidance and
ships with a six-document policy set in `docs/medical/`:

| Document | Purpose |
|---|---|
| [`medical-ai-safety-policy.md`](docs/medical/medical-ai-safety-policy.md) | The constitution. What the persona is and is not, the mandatory red-flag list, output-filter rules, tool exposure matrix, auth, audit, rollback. |
| [`medical-ai-tool-policy.md`](docs/medical/medical-ai-tool-policy.md) | Per-toolkit-tool exposure matrix and "adding a new public tool" recipe. |
| [`medical-ai-evaluation-suite.md`](docs/medical/medical-ai-evaluation-suite.md) | Metrics, Inspector smoke cases, production dashboards keyed on audit-log fields. |
| [`medical-ai-change-control.md`](docs/medical/medical-ai-change-control.md) | PCCP-style risk classes, required PR artefacts, SemVer rules, changelog. |
| [`medical-ai-privacy.md`](docs/medical/medical-ai-privacy.md) | Data minimisation, what we do and do not collect/log/retain. |
| [`medical-ai-incident-response.md`](docs/medical/medical-ai-incident-response.md) | P1/P2/P3 ladder, runbook, comms templates, postmortem checklist. |
| [`medical-ai-release-checklist.md`](docs/medical/medical-ai-release-checklist.md) | 8-section gate that must be green before tagging a doctor release. |

Industry references the policy aligns with: WHO LMM 2024 ethics guidance,
EU AI Act 2024, FDA Predetermined Change Control Plan for AI-enabled
medical software, CHAI Responsible AI Guide, AMA 2025 position on the
federal AI action plan.

---

## Project structure

```
personas/
├── README.md                       ← this file
├── package.json                    ← Node workspace root (MCP SDK + zod)
├── pnpm-workspace.yaml
├── requirements.txt                ← Python pipeline (Pillow + pyyaml)
├── Makefile                        ← assets / metadata / package / validate
├── docker-compose.mcp.yml          ← brings all 10 servers up
│
├── personas/                       ← the 10 persona bundles
│   ├── 01-creator-muse/
│   │   ├── README.md
│   │   ├── hpersona/               ← .hpersona v2 package contents
│   │   │   ├── manifest.json
│   │   │   ├── blueprint/          ← persona_agent / appearance / agentic
│   │   │   ├── dependencies/       ← tools / mcp_servers / a2a / models / suite
│   │   │   ├── assets/             ← avatar PNGs + thumbnail WebPs
│   │   │   └── preview/card.json   ← gallery character sheet
│   │   └── gallery/                ← public preview + registry entry
│   ├── 02-style-muse/
│   ├── … (10 total)
│   └── 10-general-doctor/
│
├── mcp-servers/                    ← the 10 MCP servers
│   ├── node_common/                ← shared Node MCP framework
│   │   ├── createMcpServer.js
│   │   ├── responses.js, errors.js, schemas.js, transports.js, run.js
│   │   └── test-helpers/protocol-harness.js
│   ├── python_common/              ← legacy Python helpers (FastAPI shim)
│   ├── 01-mcp-creator-muse/        ← Node MCP via node_common
│   ├── 02-mcp-style-muse/
│   ├── 03-mcp-secretary-pro/
│   ├── 04-mcp-researcher/          ← Python FastMCP
│   ├── 05-mcp-personal-trainer/
│   ├── 06-mcp-room-stylist/
│   ├── 07-mcp-storyteller/
│   ├── 08-mcp-exam-coach/
│   ├── 09-mcp-mindfulness-coach/
│   └── 10-mcp-general-doctor/      ← Python FastMCP + safety adapter
│
├── packages/                       ← shared utilities (gallery-tools etc.)
├── schemas/                        ← JSON schemas for hpersona artefacts
├── scripts/                        ← persona pipeline + validators
│   ├── persona_data.py             ← single source of truth for persona metadata
│   ├── generate_assets.py
│   ├── generate_metadata.py
│   ├── build_hpersona.py
│   ├── validate_personas.py
│   ├── validate_mcp_servers.py
│   └── verify_mcp_portfolio.py
│
├── registry/                       ← gallery registry (registry.json + per-persona)
├── dist/                           ← CI build output (gitignored)
│
├── configs/inspector/              ← MCP Inspector configs (stdio + http)
│   ├── all-stdio.json
│   ├── all-http.json
│   └── <per-server>.json
│
├── docs/
│   ├── architecture.md
│   ├── hpersona-v2-format.md
│   ├── mcp-server-contract.md
│   ├── gallery-publishing.md
│   ├── safety-guardrails.md
│   ├── persona-roadmap.md
│   ├── viral-persona-strategy.md
│   ├── baseline/                   ← pre-migration snapshots
│   ├── medical/                    ← General Doctor governance policy (7 docs)
│   └── migration/
│       └── mcp-migration-tracker.md
│
└── tests/                          ← repo-level integration tests
```

---

## Development workflow

This pack is developed in **small, atomic batches**. Every commit is
independently reviewable and reverts cleanly. The migration history in
`docs/migration/mcp-migration-tracker.md` shows the pattern:

1. **Define / update the contract** in `scripts/persona_data.py` (the
   single source of truth — manifests and cards are regenerated from it).
2. **Implement** in the matching `mcp-servers/<id>/`.
3. **Validate** with `npm test` (runs both validators).
4. **Test** with `node --test mcp-servers/<id>/test/` for Node servers
   and `pytest -q mcp-servers/<id>/tests/` for Python servers.
5. **Commit** with a message that describes the batch (sprint/batch
   prefix, scope, what changed, what didn't, what's next).

### Validators

```bash
python3 scripts/validate_personas.py
# Asserts:
#   - every .hpersona has manifest, blueprint, dependencies, preview, assets
#   - card.json has all rich fields (stats, tools, backstory, images)
#   - tools[] is consistent across card.json / dependencies / mcp_servers
#   - safety personas declare required disclaimer keywords in system_prompt
#   - avatar PNG > 5KB, gallery preview > 2KB (no stub images)
#   - description ≤ 120 chars (gallery card limit)

python3 scripts/validate_mcp_servers.py
# Asserts (for every server):
#   - src/index.{js,ts,py} exists
#   - server.json declares tools[]
#   - tools.js (if present) matches server.json names exactly
#   - index.js POST routes cover every server.json tool (legacy REST)
#     OR the server is MCP-native (imports node_common / SDK / FastMCP)
# Pending-migration servers are reported as WARN; migrated servers FAIL on drift.
```

### Single source of truth

`scripts/persona_data.py` is the **only** file you edit when adding or
renaming a persona's metadata, tools, system prompt, or safety keywords.
`make metadata` regenerates every dependent JSON file. Editing
`manifest.json` / `card.json` / `tools.json` directly will be overwritten.

---

## Testing

```bash
# All Python persona tests (researcher + doctor)
pytest -q mcp-servers/04-mcp-researcher/tests/
pytest -q mcp-servers/10-mcp-general-doctor/tests/

# All Node persona tests
node --test mcp-servers/node_common/test/framework.test.js
node --test mcp-servers/01-mcp-creator-muse/test/inspire.test.js \
            mcp-servers/01-mcp-creator-muse/test/mcp-protocol.test.js
# (repeat for 02, 03, 05, 06, 07, 08, 09)

# Persona / MCP contract validators
npm test
```

Every Node server has at minimum:

- a unit-test file for the pure business-logic module, and
- an MCP-protocol smoke test using the shared
  [`runProtocolHarness`](mcp-servers/node_common/test-helpers/protocol-harness.js)
  that boots an in-memory MCP client + server and exercises
  `initialize`, `tools/list`, `tools/call` (sample inputs), invalid-input
  rejection, and unknown-tool rejection.

Safety-sensitive servers add a third test file (`test/safety.test.js`)
covering every refusal pattern in their guardrail.

The General Doctor adapter additionally ships an
[adversarial test suite](mcp-servers/10-mcp-general-doctor/tests/test_adversarial.py)
with 12 cases across five attack classes (jailbreak, dose-leak,
pediatric+pregnancy, PHI exfiltration, rollback envelope).

---

## Deployment

### Docker Compose

```bash
docker compose -f docker-compose.mcp.yml up -d
```

Brings up all 10 MCP servers. Ports `9101`–`9110` are exposed on the host;
each server's MCP endpoint is `http://<host>:<port>/mcp` for Streamable
HTTP, plus `GET /health` for liveness.

### Per-language images

- Node servers run from the repo-root image, one container per service.
- Python servers (`mcp-researcher`, `mcp-general-doctor`) build their
  own images from `mcp-servers/<id>/Dockerfile` (Python 3.12-slim,
  non-root user, `/mcp` healthcheck, named volumes for cache and audit
  log).

### Environment variables

Each persona ships an `.env.example` documenting every knob. The
operationally significant ones:

| Server | Variable | Default | Purpose |
|---|---|---|---|
| All Node | `MCP_TRANSPORT` | `stdio` | `stdio` / `streamable-http` |
| All Node | `MCP_PORT` | per-server | HTTP transport port |
| Researcher | `MCP_RESEARCHER_TRANSPORT` | `stdio` | as above |
| Researcher | `WATSONX_*` | – | optional WatsonX RAG (sprint 3) |
| Researcher | `ARXIV_MAX_RESULTS` | `8` | hard cap on `search_arxiv` |
| Doctor | `MEDICAL_MCP_URL` | `http://localhost:9090` | Upstream `medical-mcp-toolkit` URL |
| Doctor | `MEDICAL_MCP_BEARER_TOKEN` | – | Bearer for upstream `/invoke` |
| Doctor | `MEDICAL_MCP_OFFLINE_FALLBACK` | `true` | Degrade gracefully if upstream is down |
| Doctor | `GENERAL_DOCTOR_ADAPTER_ENABLED` | `true` | **Rollback kill-switch** |
| Doctor | `DOCTOR_AUDIT_LOG_PATH` | (stderr) | JSON-lines audit log |
| Doctor | `DOCTOR_AUDIT_HASH_USER_INPUT` | `true` | SHA-256 user text in audit logs (no raw PHI) |

### MCP Inspector

```bash
# stdio mode — Inspector spawns each server itself; no containers required
npx @modelcontextprotocol/inspector --config configs/inspector/all-stdio.json

# Streamable HTTP — bring docker compose up first
npx @modelcontextprotocol/inspector --config configs/inspector/all-http.json

# Single server iteration
npx @modelcontextprotocol/inspector --config configs/inspector/researcher.json
npx @modelcontextprotocol/inspector --config configs/inspector/general-doctor.json
```

### Context Forge federation

Each server's `server.json` declares its MCP endpoint
(`/mcp`), transport (`streamable-http`), and auth posture (`bearer` for
the doctor, `open` elsewhere). Register each as a Streamable HTTP MCP
server in your Context Forge instance and it federates them under a
single gateway.

---

## HomePilot Gallery publishing

Personas in this repo are published to the
[HomePilot Community Gallery](https://ruslanmv.com/HomePilot/gallery.html)
as `.hpersona` v2 bundles. The CI pipeline produces:

- `dist/packages/<id>/<version>/persona.hpersona` — zipped persona bundle
- `dist/previews/<id>/<version>/preview.webp` — gallery card image
- `dist/previews/<id>/<version>/card.json` — gallery character sheet

The top-level `registry/registry.json` follows the gallery item contract
consumed by `ruslanmv/HomePilot/docs/gallery.js`:

```json
{
  "id": "creator-muse",
  "name": "Creator Muse",
  "short": "Brainstorming muse for reels, carousels and viral hooks…",
  "author": "homepilot-team",
  "nsfw": false,
  "tags": ["creative", "productivity", "entertainment"],
  "class_id": "muse",
  "downloads": 0,
  "submitted_at": "2026-05-02T06:54:22Z",
  "latest": {
    "version": "1.0.0",
    "preview_url": "previews/creator-muse/1.0.0/preview.webp",
    "card_url":    "previews/creator-muse/1.0.0/card.json",
    "package_url": "packages/creator-muse/1.0.0/persona.hpersona",
    "size_bytes":  421311
  }
}
```

The CI workflow (`.github/workflows/build-personas.yml`) runs the full
asset → metadata → package → validate pipeline on every push and uploads
the `dist/` artifact for gallery publishing.

---

## Adding a new persona

1. **Append a row** to `scripts/persona_data.py` with `id`, `dir`,
   `mcp_server`, `name`, `role`, `class_id`, `emoji`, `short`, `tags`,
   `palette`, `stats`, `style_tags`, `tone_tags`, `tools`,
   `backstory`, `system_prompt`, `capabilities`, `tool_specs`.
2. **Create** `personas/<NN>-<id>/` and `mcp-servers/<NN>-mcp-<id>/`
   folders.
3. **Run** `make assets metadata` to generate avatars, cards, manifests,
   and registry entries.
4. **Implement** the MCP server using `node_common` (Node) or `FastMCP`
   (Python). Mirror the structure of an existing server of the same
   language.
5. **Add tests**: pure-logic unit tests + an `mcp-protocol.test.js` that
   calls `runProtocolHarness` (Node) or a `test_server_contract.py`
   that asserts the FastMCP tool registration (Python).
6. **Add Inspector configs**: a single-server config plus entries in
   `all-stdio.json` and `all-http.json`.
7. **Add a Docker compose entry** to `docker-compose.mcp.yml`.
8. **Run `npm test`** — both validators must pass strictly (no WARN).

For wellness/medical/educational personas, add a `src/safety.{js,py}`
module following the patterns in `mindfulness-coach`, `personal-trainer`,
`exam-coach`, or `general-doctor` — and write the safety tests *first*.

---

## Adding a new MCP tool

1. Add the tool to the persona's `tool_specs` in `persona_data.py`.
2. `make metadata` regenerates `tools.json`, `card.json`, `manifest.json`.
3. Update `mcp-servers/<id>/server.json` with `name` + `description`.
4. Implement the handler in `mcp-servers/<id>/src/tools.{js,py}`:
   - Node: `{ name, description, schema: {...zod}, handler }`
   - Python: `@mcp.tool()` decorator with `Annotated[..., Field(...)]`
     parameters
5. Add a `sampleArgs` row (and an `invalidArgs` row when meaningful) to
   the `runProtocolHarness` call in `test/mcp-protocol.test.js`.
6. For safety-sensitive tools, add a unit-test for the guardrail and
   wire user-text fields through the server's `withCrisisGuard` /
   `withRedFlagGuard` / `withContentGuard` / `withIntegrityGuard`
   wrapper.
7. `npm test` — validator must remain strict-PASS.

The General Doctor has its own onboarding rules in
[`docs/medical/medical-ai-tool-policy.md`](docs/medical/medical-ai-tool-policy.md).

---

## Documentation index

### Operator-facing

- [`docs/architecture.md`](docs/architecture.md) — high-level repo
  architecture
- [`docs/mcp-server-contract.md`](docs/mcp-server-contract.md) — the MCP
  server contract personas depend on
- [`docs/hpersona-v2-format.md`](docs/hpersona-v2-format.md) — the
  `.hpersona` v2 package layout
- [`docs/gallery-publishing.md`](docs/gallery-publishing.md) — how to
  publish to the HomePilot Community Gallery
- [`docs/safety-guardrails.md`](docs/safety-guardrails.md) — guardrail
  patterns across the platform
- [`configs/inspector/README.md`](configs/inspector/README.md) — MCP
  Inspector usage

### Engineering

- [`docs/migration/mcp-migration-tracker.md`](docs/migration/mcp-migration-tracker.md)
  — the platform-wide migration plan and per-server status
- [`docs/baseline/general-doctor-current-state.md`](docs/baseline/general-doctor-current-state.md)
  — pre-Sprint-C snapshot of the doctor (for rollback reference)
- [`docs/baseline/medical-mcp-toolkit-current-state.md`](docs/baseline/medical-mcp-toolkit-current-state.md)
  — upstream toolkit envelope the doctor adapter depends on

### Medical AI policy (General Doctor)

- [`docs/medical/medical-ai-safety-policy.md`](docs/medical/medical-ai-safety-policy.md)
- [`docs/medical/medical-ai-tool-policy.md`](docs/medical/medical-ai-tool-policy.md)
- [`docs/medical/medical-ai-evaluation-suite.md`](docs/medical/medical-ai-evaluation-suite.md)
- [`docs/medical/medical-ai-change-control.md`](docs/medical/medical-ai-change-control.md)
- [`docs/medical/medical-ai-privacy.md`](docs/medical/medical-ai-privacy.md)
- [`docs/medical/medical-ai-incident-response.md`](docs/medical/medical-ai-incident-response.md)
- [`docs/medical/medical-ai-release-checklist.md`](docs/medical/medical-ai-release-checklist.md)

### Strategy

- [`docs/persona-roadmap.md`](docs/persona-roadmap.md)
- [`docs/viral-persona-strategy.md`](docs/viral-persona-strategy.md)
- [`docs/mcp_portfolio_verification.md`](docs/mcp_portfolio_verification.md)

---

## Contributing

1. Open an issue describing the persona, MCP tool, or guardrail you
   intend to add.
2. Branch from `main`. Use a short, descriptive name
   (e.g. `feature/medication-safety-checker`).
3. Follow the [development workflow](#development-workflow): small
   atomic batches, tests first for safety-sensitive code.
4. Ensure `npm test` is green and `pytest -q` is green for any Python
   server you touched.
5. Open a PR. The `build-personas.yml` workflow runs the full pipeline
   and uploads the `dist/` artifact.

For changes to the General Doctor adapter, follow the change-control
risk classes in
[`docs/medical/medical-ai-change-control.md`](docs/medical/medical-ai-change-control.md).
R3+ changes require an entry in the changelog table and an updated
adversarial test.

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

---

## Acknowledgements

- [HomePilot](https://github.com/ruslanmv/HomePilot) — the host platform
  and gallery this pack publishes to.
- [Model Context Protocol](https://modelcontextprotocol.io/) — the
  protocol every server in this pack speaks.
- [`medical-mcp-toolkit`](https://github.com/ruslanmv/medical-mcp-toolkit)
  — the upstream capability layer behind the General Doctor adapter.
- [`Medical-AI-Assistant-System`](https://github.com/ruslanmv/Medical-AI-Assistant-System)
  — internal-orchestration reference for future specialist routing.
- [`ArXiv-Chatter-WatsonX`](https://github.com/ruslanmv/ArXiv-Chatter-WatsonX)
  and [`Chat-Researcher`](https://github.com/ruslanmv/Chat-Researcher)
  — references for the Researcher persona's arXiv + RAG pipeline.
