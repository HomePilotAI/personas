# MCP Platform Migration Tracker

**Goal**: convert every MCP server in this repo from the existing
REST-style pseudo-MCP shim into a real MCP server compatible with
[MCP Inspector](https://ibm.github.io/mcp-context-forge/using/clients/mcp-inspector/)
and federatable by [MCP Context Forge](https://github.com/IBM/mcp-context-forge).

The migration runs in small, atomic batches. Each batch lands as one commit
that is independently reviewable and reverts cleanly.

## Status table

| Server | Current language | Current transport | Target language | Target transport | Status |
|---|---|---|---|---|---|
| `01-mcp-creator-muse` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-A batch 3** |
| `02-mcp-style-muse` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-A batch 5a** |
| `03-mcp-secretary-pro` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-B batch 1** |
| `04-mcp-researcher` | Python (FastMCP) | streamable-http | Python (FastMCP) | stdio + Streamable HTTP | **done — sprint-1 batches 1-5** |
| `05-mcp-personal-trainer` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-B batch 2** |
| `06-mcp-room-stylist` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-A batch 5b** |
| `07-mcp-storyteller` | Node (real logic over REST) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-B batch 3 (legacy logic preserved)** |
| `08-mcp-exam-coach` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-B batch 4** |
| `09-mcp-mindfulness-coach` | Node (Express stub) | REST | Node (MCP SDK) | stdio + Streamable HTTP | **done — sprint-A batch 5c** |
| `10-mcp-general-doctor` | Node (Express stub) | REST | **Python (FastMCP) — safety adapter on top of `medical-mcp-toolkit`** | stdio + Streamable HTTP | **done — sprint-C batch 3 (adversarial suite + remaining governance docs in C4)** |

## Canonical tool names (frozen)

These are the contract for the rest of the migration. They must already
match what `personas/<id>/hpersona/dependencies/tools.json` and
`preview/card.json` declare; **any rename here also requires editing
`scripts/persona_data.py` and re-running `make metadata`**.

| Server | Tool name | Description |
|---|---|---|
| `01-mcp-creator-muse` | `creator_muse_inspire` | Generate scroll-stopping content ideas (hook + scene + CTA). |
| `02-mcp-style-muse` | `style_muse_outfit` | Suggest a head-to-toe outfit for a target vibe / occasion. |
| `02-mcp-style-muse` | `style_muse_variant` | Generate styling variants of a base look. |
| `03-mcp-secretary-pro` | `secretary_schedule` | Propose calendar slots across time zones. |
| `03-mcp-secretary-pro` | `secretary_remind` | Create time-aware reminders. |
| `03-mcp-secretary-pro` | `secretary_triage` | Sort inbox items by urgency bucket. |
| `04-mcp-researcher` | `search_arxiv` | Search arXiv and return normalized paper metadata. |
| `04-mcp-researcher` | `read_paper` | Fetch metadata; optionally extract full PDF text. |
| `04-mcp-researcher` | `summarize_paper` | Summarize a paper (abstract or RAG-grounded). |
| `04-mcp-researcher` | `compare_papers` | Side-by-side compare papers (sprint-3). |
| `04-mcp-researcher` | `build_literature_brief` | Citation-backed literature brief (sprint-4). |
| `05-mcp-personal-trainer` | `trainer_workout_plan` | Build a structured workout plan. |
| `05-mcp-personal-trainer` | `trainer_recovery_check` | Surface recovery / soreness flags. |
| `05-mcp-personal-trainer` | `trainer_streak` | Track and reinforce streak / habit progress. |
| `06-mcp-room-stylist` | `room_layout` | Propose a room layout for a given footprint and goal. |
| `06-mcp-room-stylist` | `room_palette` | Build a color palette and material story. |
| `06-mcp-room-stylist` | `room_shopping_list` | Curate a shoppable list grouped by zone. |
| `07-mcp-storyteller` | `story_scene` | Generate / describe a single live-play scene. |
| `07-mcp-storyteller` | `story_choice` | Generate a branching choice with outcome notes. |
| `07-mcp-storyteller` | `story_ending` | Generate one of N possible endings. |
| `08-mcp-exam-coach` | `exam_question` | Generate practice questions on a topic. |
| `08-mcp-exam-coach` | `exam_plan` | Build a study plan from a target date and topic list. |
| `08-mcp-exam-coach` | `exam_explain` | Explain a concept at a given depth. |
| `09-mcp-mindfulness-coach` | `mindfulness_meditation` | Guided meditation script for a target duration. |
| `09-mcp-mindfulness-coach` | `mindfulness_grounding` | Grounding / 5-4-3-2-1 style exercise. |
| `09-mcp-mindfulness-coach` | `mindfulness_focus` | Focus / intention-setting micro-exercise. |
| `10-mcp-general-doctor` | `doctor_general_info` | Non-diagnostic general health information. |
| `10-mcp-general-doctor` | `doctor_red_flags` | Triage symptoms for emergency red flags + escalation copy. |
| `10-mcp-general-doctor` | `doctor_self_care` | Suggest self-care steps with "consult a professional" disclaimer. |

## Batch plan

### Sprint A — foundation + simple servers

- **A1** *(this commit)* — migration tracker + extend
  `scripts/validate_mcp_servers.py` to fail when tool names drift across
  `server.json`, `src/tools.js`, and the implemented POST routes.
- **A2** — add `@modelcontextprotocol/sdk` + `zod` at the workspace root
  and build `mcp-servers/node_common/` (createMcpServer, responses,
  transports, errors, schemas) supporting stdio + Streamable HTTP.
- **A3** — convert `01-mcp-creator-muse` to real MCP using `node_common`,
  with input schema, content-block result, both transports, Inspector +
  Context Forge configs.
- **A4** — Node MCP protocol test harness (initialize, tools/list,
  tools/call for every tool, bad-input rejection); wire into `npm test`.
- **A5** — convert `02-mcp-style-muse`, `06-mcp-room-stylist`, and
  `09-mcp-mindfulness-coach` (one sub-commit each).

### Sprint B — medium servers

- `03-mcp-secretary-pro` — schedule / remind / triage with safety: never
  send messages, only draft.
- `05-mcp-personal-trainer` — workout / recovery / streak with injury
  caveats and "consult a physician" copy where needed.
- `07-mcp-storyteller` — preserve the existing scene/choice/ending logic
  in `index.js` (real business code) but expose it as MCP tools matching
  the canonical names; legacy POST routes stay alive for one release as
  410-Gone deprecation shims.
- `08-mcp-exam-coach` — question / plan / explain with academic-integrity
  guardrails (no live cheating, no answer-only mode for active exams).

### Sprint D — production hardening (post-Sprint-C external review) — **done**

- D1 — Dockerfile / Makefile / docker-compose.yml / size_bytes /
  version policy.
- D2 — legacy HTTP / Context Forge compat bridge
  (`--transport legacy-http | hybrid`, FastAPI app exposing per-tool
  POST routes + `/context-forge/call`, 9 new tests).
- D3 — structured pediatric / pregnancy / postpartum red-flag layer;
  emergency wording with concrete numbers (112/911/999/000/119);
  persona opening message rewrite (25 new tests).
- D4 — Phase B + Phase C design docs + platform roadmap
  (`docs/migration/platform-roadmap.md`).

### Sprint E onwards — see `docs/migration/platform-roadmap.md`

The roadmap covers gallery publishing (E), Phase B persona (F),
platform-wide Docker overhaul (G), Context Forge federation (H),
Phase C persona (I), and the remaining architecture docs (J).

### Sprint C — doctor (medical adapter) + platform

The Doctor server is its own multi-batch sprint because it is a true safety
adapter, not a like-for-like rewrite. It does **not** ship the Node MCP
SDK pattern of sprints A/B; it ships a Python FastMCP adapter that calls
the upstream [`medical-mcp-toolkit`](https://github.com/ruslanmv/medical-mcp-toolkit)
through a safety gateway.

- **C1** *(this commit)* — baseline state docs (current persona + current
  toolkit shape) and `docs/medical/medical-ai-safety-policy.md` (the
  industry-aligned constitution we'll enforce in code: red-flag list,
  output-filter rules, exposure policy, auth, audit, rollback).
- **C2** — Python FastMCP adapter at `mcp-servers/10-mcp-general-doctor/`:
  3 canonical tools (`doctor_red_flags`, `doctor_general_info`,
  `doctor_self_care`), `safety.py` (red-flag detector + output filter),
  `upstream.py` (HTTP client to `medical-mcp-toolkit/POST /invoke` +
  offline-fake fallback), `audit.py` (no-PHI event logging), pydantic
  schemas, contract + safety tests.
- **C3** — persona upgrade: `persona_data.py` row, system prompt,
  `tools.json` / `mcp_servers.json` (bearer auth + upstream config),
  `card.json`, validators, Inspector configs, tracker flip to "done".
- **C4** — adversarial test suite + remaining governance docs
  (`medical-ai-tool-policy.md`, `medical-ai-evaluation-suite.md`,
  `medical-ai-change-control.md`, `medical-ai-privacy.md`,
  `medical-ai-incident-response.md`, `medical-ai-release-checklist.md`).

Platform tasks (post-doctor): `docker/Dockerfile.node-mcp`, full
`docker-compose.mcp.yml` rewrite, Context Forge registration, the architecture
+ contract docs from your phase-15 list.

## Definition of done

- All 10 servers speak real MCP (JSON-RPC `initialize`, `tools/list`,
  `tools/call`).
- All 10 servers expose **stdio** for local development and
  **Streamable HTTP `/mcp`** for Context Forge.
- Every tool has an input schema (Zod or pydantic).
- `validate_mcp_servers.py` fails on drift between persona deps,
  `server.json`, and implemented MCP tools.
- Wellness/exam/doctor tools include the safety guardrails listed in
  this tracker.
- `docker compose -f docker-compose.mcp.yml up` brings the full stack up.
- MCP Inspector connects to every server (stdio and HTTP).
- Context Forge can federate every server.
