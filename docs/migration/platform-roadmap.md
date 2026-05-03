# Platform Roadmap

State after Sprint D. The 10 personas + 10 real MCP servers + safety
adapter pattern + governance docs are in production-candidate shape. This
file is the canonical "what's next" — concrete, scoped, and ordered.

## Recently shipped (this branch)

- **Sprint A** — `node_common` framework, drift-detecting validators,
  Inspector configs, simple persona conversions
  (creator-muse, style-muse, room-stylist, mindfulness-coach).
- **Sprint B** — medium-tier persona conversions
  (secretary-pro draft-only, personal-trainer red-flag,
  storyteller content rails, exam-coach academic integrity).
- **Sprint C** — General Doctor full safety adapter:
  Python FastMCP server + safety gateway + upstream HTTP client
  + audit log + 6-doc medical AI governance set + adversarial suite.
- **Sprint D** — production hardening per external review:
  - D1 — Dockerfile / Makefile / docker-compose / size_bytes / version policy.
  - D2 — legacy HTTP / Context Forge compat bridge (
    `--transport legacy-http | hybrid`).
  - D3 — structured pediatric / pregnancy / postpartum signals;
    emergency wording with concrete numbers (112/911/999/000/119);
    persona opening message rewrite.
  - D4 — Phase B + Phase C design docs + this roadmap.

## Sprint E — gallery publishing (single-PR sprint)

Block: the live `https://ruslanmv.com/HomePilot/gallery.html` still
serves placeholder Scarlett / Atlas entries. Goal: switch it to this
repo's `registry/registry.json` + `dist/`.

Tasks:

- Wire `.github/workflows/publish-gallery.yml` (currently a stub) to
  copy `registry/registry.json` → `ruslanmv/HomePilot/docs/registry.json`
  and `dist/{packages,previews}/**` → `ruslanmv/HomePilot/docs/{packages,previews}/**`,
  open a PR via a deploy key.
  *Alternative*: push to an R2 bucket and flip `window.GALLERY_API` /
  `GALLERY_MODE = "r2"` on the gallery page.
- Add `sha256` to each package in `build_hpersona.py` and write it
  into `latest.sha256` so the gallery can show integrity hashes.
- Mirror avatar PNGs into `dist/previews/<id>/<ver>/` and rewrite
  `card.json.images.avatar` to a sibling path so the modal renders
  the avatar after publish.
- Backfill `issue_number` on each persona registry entry so the
  gallery's provenance chip renders.

DoD: the gallery shows the 10 personas with working downloads, real
character sheets, and integrity hashes; placeholder Scarlett / Atlas
removed.

## Sprint F — Phase B persona: Medication Safety Checker

See [`docs/medical/phase-b-medication-safety-checker.md`](../medical/phase-b-medication-safety-checker.md)
for the full design. Concrete deliverables:

- `personas/11-medication-safety-checker/` (.hpersona v2 bundle).
- `mcp-servers/11-mcp-medication-safety-checker/` (Python FastMCP +
  safety adapter, port 9111).
- Extract `mcp-servers/python_common/medical/` shared package
  (safety + audit + upstream client) so the doctor and the new
  persona call the same primitives.
- 50+ tests; 2 weeks of doctor production audit logs reviewed
  before this persona is enabled in any user-facing environment.

DoD per the Phase B doc.

## Sprint G — Platform-wide Docker compose overhaul

Today the Node services in `docker-compose.mcp.yml` `build: .` against a
non-existent root Dockerfile. The Python services have their own
Dockerfiles. Goal: every service has a working build context and runs
clean from a fresh checkout.

Tasks:

- Add `docker/Dockerfile.node-mcp` shared by the 8 Node services.
  Multi-stage: `node:22-slim` base, copy `node_common/` + the per-server
  folder, `npm install --prefix mcp-servers/<id>`, run with the
  service's `start:http` script under a non-root user.
- Replace each Node service's `build: .` with a per-service block:

      build:
        context: .
        dockerfile: docker/Dockerfile.node-mcp
        args: { SERVER_DIR: mcp-servers/01-mcp-creator-muse }
      command: ["node", "mcp-servers/01-mcp-creator-muse/src/index.js"]
      environment:
        MCP_TRANSPORT: streamable-http
        MCP_PORT: "9101"

- Add `HEALTHCHECK` to each Node service mirroring the Python ones
  (`POST /mcp` with empty body returns 405 or 200 — both prove the
  endpoint is up).
- Add a top-level `homepilot-personas` network so the doctor can
  reach `medical-mcp-toolkit` by service name when both run in the
  same compose stack.
- Document `docker compose up` as the single canonical local runtime
  in the README.

DoD: `docker compose -f docker-compose.mcp.yml up` brings all 10
services up cleanly from a fresh checkout, every service is healthy
within 30s, every Inspector HTTP config resolves.

## Sprint H — Context Forge registration

Goal: every persona MCP server is federated under a single Context
Forge instance, with virtual server groups per persona category.

Tasks:

- Generate per-server Context Forge registration JSON in
  `configs/context-forge/<server>.json` based on each `server.json`
  (transport, URL, bearer hint).
- Generate virtual server groups in
  `configs/context-forge/virtual-servers.json`:

      creative-assistant:    [creator-muse, style-muse, room-stylist, storyteller]
      productivity-assistant: [secretary-pro]
      learning-assistant:    [researcher, exam-coach]
      wellness-assistant:    [personal-trainer, mindfulness-coach, general-doctor]

- Document the registration recipe at
  `docs/context-forge-registration.md`.
- E2E smoke: `npx @modelcontextprotocol/inspector` connects through
  Context Forge gateway URLs (`/servers/<UUID>/mcp/`) and lists the
  expected tools per virtual server.

DoD: the four virtual servers are reachable via Inspector through
Context Forge; every tool answers; the doctor still escalates red
flags through the gateway.

## Sprint I — Phase C persona: Appointment Coordinator

See [`docs/medical/phase-c-appointment-coordinator.md`](../medical/phase-c-appointment-coordinator.md).
Lands only after:

- Sprint F has shipped Phase B and 30 days of Phase B audit logs are
  reviewed.
- A privacy policy extension is committed and reviewed.
- The HomePilot client agrees to the explicit-confirmation UX
  (every client must render "are you sure?" before posting
  `appointment_confirm`).

DoD per the Phase C doc.

## Sprint J — remaining architecture docs

The medical / migration / inspector docs are landed; the platform-wide
contract docs your phase-15 list called out are not. Tasks:

- `docs/architecture.md` — refresh for the post-Sprint-D state (Node
  vs Python adapters, the safety-adapter pattern, Context Forge).
- `docs/mcp-server-contract.md` — formalise what every server MUST
  expose (the validators already enforce most of this; the doc names
  it).
- `docs/safety-guardrails.md` — refresh to enumerate the five
  guardrail patterns shipping today (draft-only, red-flag medical x2,
  content rails, academic integrity, full medical adapter).
- `docs/adding-new-server.md` — onboarding recipe pulled from the
  README; the README links here.
- `docs/inspector-testing.md` — the manual test plan for tagging a
  release.
- `docs/migration-status.md` — derived view of
  `docs/migration/mcp-migration-tracker.md` rendered as a one-page
  status board.

DoD: every doc the README links to exists; the README's documentation
index is no longer aspirational.

## Out of scope (deliberately)

- **Specialist medical personas** (cardiology, oncology, ...). The
  Medical-AI-Assistant-System reference repo has them, but exposing
  them as public personas implies specialist clinical care and is a
  liability surface we don't take on without clinical governance.
  They stay internal-orchestration only — see
  `docs/medical/medical-ai-safety-policy.md` §10 Phase D.
- **Voice / phone interfaces** for any medical persona. Out of scope
  for this pack; the persona is text-only.
- **Long-term user memory / per-user history** for the doctor. The
  privacy posture is "data minimisation, no PHI retained by default";
  long-term memory needs its own privacy story.

## Suggested execution order

```
1. Sprint E (gallery publishing)            — single-PR, unblocks distribution
2. Sprint F (Phase B persona)               — medication safety
3. Sprint G (Docker compose overhaul)       — infra cleanup
4. Sprint H (Context Forge registration)    — production federation
5. Sprint I (Phase C persona)               — appointment coordinator
6. Sprint J (remaining architecture docs)   — closing-the-doc-loop
```

E + G can be parallelised. F → I sequentially because Phase C requires
Phase B's audit-log experience. H benefits from F + G being done first
but is not blocked by them.
