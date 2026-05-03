# Production Readiness Plan — HomePilot Personas

**Audience**: maintainers, ops, security review.
**State at writing**: `claude/review-homepilot-personas-N5gBZ` HEAD, post Sprint D + Sprint E batches 1-2.
**Goal**: name every gap blocking a clean production cutover, sequence the work, and define what "production ready" means for the whole pack.

This doc is the canonical "what's left" — concrete, scoped, and ordered. It supersedes the older `docs/migration/platform-roadmap.md` for the production cutover; that file becomes the long-tail roadmap (Phases B / C / specialist personas).

---

## 1. What is production-ready already

| Area | State | Evidence |
|---|---|---|
| 10 persona MCP servers speak real MCP | ✅ | `validate_mcp_servers.py`: 10/10 strict-PASS, 0 WARN |
| Node `node_common` framework + protocol harness | ✅ | sprint-A batches 1-5 |
| Drift-detecting validators in CI | ✅ | `validate_personas.py`, `validate_mcp_servers.py` |
| Doctor safety adapter + governance set | ✅ | sprint-C batches 1-4 (7 medical AI docs) |
| Researcher source policy + PDF guards + audit + rate-limit + dual-use | ✅ | sprint-E batches 1-2 (40 / 40 tests) |
| Inspector configs (stdio + http) | ✅ | `configs/inspector/*.json` |
| Per-language Dockerfiles for the two Python servers | ✅ | sprint-D batch 1 |
| Top-level `docker-compose.yml` not broken | ✅ | sprint-D batch 1 (`include:` of `.mcp.yml`) |
| Gallery `size_bytes` correct for all 10 personas | ✅ | sprint-D batch 1 backfill |
| Adversarial test suites (doctor + structured pediatric / pregnancy) | ✅ | 81 / 81 doctor tests |
| Phase B / C design docs landed | ✅ | `docs/medical/phase-{b,c}-*.md` |

---

## 2. Production blockers, by severity

### P0 — must close before any production deploy

1. **Gallery publishing is not wired.** The live `https://ruslanmv.com/HomePilot/gallery.html` still serves placeholder Scarlett / Atlas entries. `.github/workflows/publish-gallery.yml` is a stub.
2. **No package integrity hashes.** `build_hpersona.py` does not write `latest.sha256` into the registry. Gallery downloads cannot be verified.
3. **Avatars are not in the published artefact tree.** Gallery modal can't render avatar images because `dist/previews/<id>/<ver>/` ships only the preview + card, not the avatar PNG.
4. **Node Dockerfile missing.** The 8 Node services in `docker-compose.mcp.yml` declare `build: .` but no root Dockerfile exists. Only researcher + doctor (Python) build clean today.
5. **Researcher persona dependency still says `auth_type: open`.** The doctor flipped to bearer in sprint-C; the other 9 are still open. For an enterprise deployment the bearer-auth posture must be platform-wide.
6. **`verify_mcp_portfolio.py` runs as a soft check (`|| true`)** in `build-personas.yml`. Any contract regression silently passes CI.

### P1 — must close before user-facing rollout

7. **No SHA-256 / supply-chain provenance** beyond size_bytes. Gallery should publish hash + signature.
8. **Researcher governance docs incomplete.** `domain-safety-policy.md` was started and removed; `evaluation-suite.md`, `incident-response.md`, `production-readiness.md` for the researcher specifically not yet written.
9. **Researcher persona prompt + opening message** still pre-Sprint-E (no dual-use language, no source-allow-list note).
10. **Multi-source connectors absent.** Today the researcher only talks to arXiv. OpenAlex / Crossref / PubMed / NASA ADS / OSTI are documented in the source policy but no client code exists.
11. **`compare_papers` and `build_literature_brief`** still return `ToolNotImplemented`. They are advertised but not real.
12. **No Context Forge registration files** at `configs/context-forge/`. Federation is documented in the roadmap but not implemented.
13. **Healthchecks missing on Node services.** Only Python services declare `HEALTHCHECK` in their Dockerfiles.
14. **Compose network not declared.** The doctor adapter's `MEDICAL_MCP_URL` defaults to `http://medical-mcp-toolkit:9090` but no compose network groups them, so DNS resolution fails inside the stack.

### P2 — must close before broad rollout

15. **Per-persona version override.** `scripts/build_hpersona.py` hard-codes `VERSION = "1.0.0"` for all 10 personas. After the first publish, individual personas iterating need their own version (e.g. researcher 1.1.0, doctor 1.0.5).
16. **Secret management is env-only.** No vault / KMS integration. Fine for early production; documented gap once we onboard a real customer.
17. **Tracing beyond JSON-line audit log.** OTEL spans + correlation IDs across servers are not in place.
18. **Dependency pinning + renovation cadence.** `pyproject.toml` files use `>=` ranges; no monthly bump cadence or supply-chain audit on record.
19. **Penetration test / security review** has not been recorded. The SSRF guard, dual-use gate, and PDF magic-bytes check are unit-tested but not red-teamed.
20. **Multi-tenant isolation.** Single-tenant by default; per-tenant audit log + per-tenant rate limit not designed yet.

---

## 3. Sequenced sprint plan to "production-ready"

Each sprint is independent enough to ship as one PR. DoD is the explicit gate; nothing merges without all boxes ticked.

### Sprint E3 — Researcher governance docs + prompt upgrade (~2 days)

Closes P1 #8 and #9.

**Scope**:
- `docs/research/domain-safety-policy.md` (the file we removed; rewrite carefully).
- `docs/research/evaluation-suite.md` — metrics, dashboards, gating signals.
- `docs/research/incident-response.md` — P1/P2/P3 ladder mirroring the doctor's.
- `docs/research/researcher-production-readiness.md` — release checklist.
- Researcher persona system prompt rewrite + opening message
  (`scripts/persona_data.py`, `persona_agent.json`).
- Add `tests/test_safety.py` covering benign-allow + 7-category-deny
  matrix.

**DoD**:
```
[ ] All 4 governance docs in docs/research/ committed.
[ ] Researcher persona prompt names: dual-use refusal categories,
    source-allow / Sci-Hub-deny, citation discipline, evidence levels.
[ ] tests/test_safety.py: ≥ 25 cases (benign + each of 7 deny categories +
    domain classifier).
[ ] validate_personas.py PASS; validate_mcp_servers.py 10/10 strict-PASS.
[ ] make -C mcp-servers/04-mcp-researcher pytest green.
```

### Sprint F — Gallery publishing pipeline (~3 days)

Closes P0 #1, #2, #3, plus P1 #7.

**Scope**:
- `scripts/build_hpersona.py`: compute `sha256` per package, write into
  registry + per-persona JSON + gallery template.
- `scripts/build_hpersona.py`: copy `hpersona/assets/avatar_<id>.png`
  and `thumb_avatar_<id>.webp` into `dist/previews/<id>/<ver>/` and
  rewrite `card.json.images.{avatar,thumb}` to sibling paths.
- `.github/workflows/publish-gallery.yml`: replace stub with a real
  job that opens a PR against `ruslanmv/HomePilot` syncing
  `docs/registry.json` and `docs/{packages,previews}/`.
- Optional alternative: push to R2, wire `window.GALLERY_API`.

**DoD**:
```
[ ] dist artefact for every persona has sha256 in registry/registry.json
    and personas/<id>/gallery/registry-entry.json.
[ ] dist/previews/<id>/<ver>/avatar.png exists; card.json points at it
    relatively; gallery modal renders the avatar.
[ ] Manual run of publish-gallery.yml opens a PR on ruslanmv/HomePilot
    that diff-replaces the placeholder Scarlett/Atlas entries with our 10.
[ ] After merge, the live gallery page shows our 10 personas with
    working downloads and integrity hashes.
```

### Sprint G — Node Dockerfile + compose hardening (~2 days)

Closes P0 #4, P1 #13, P1 #14.

**Scope**:
- `docker/Dockerfile.node-mcp` shared multi-stage Dockerfile (node:22-slim,
  copy `node_common/` + per-server folder, npm install, non-root user,
  `HEALTHCHECK` polling `POST /mcp` with empty body).
- Rewrite each Node service in `docker-compose.mcp.yml` to use the
  shared Dockerfile via build args (`SERVER_DIR=mcp-servers/01-mcp-creator-muse`).
- Top-level `homepilot-personas` network so the doctor can resolve
  `medical-mcp-toolkit` by service name.
- Document the canonical local runtime (`docker compose -f docker-compose.mcp.yml up`)
  in the README.

**DoD**:
```
[ ] docker compose up brings all 10 services healthy from a fresh checkout.
[ ] Each service has a HEALTHCHECK and reaches "healthy" within 30s.
[ ] Doctor adapter resolves the toolkit by name on the homepilot-personas
    network; compose-level integration test passes.
[ ] All Inspector HTTP configs resolve.
```

### Sprint H — Bearer auth platform-wide (~2 days)

Closes P0 #5.

**Scope**:
- Update `personas/<id>/hpersona/dependencies/mcp_servers.json`
  for the 8 still-open servers: `auth_type: bearer`.
- For Node servers, extend `node_common/transports.js` to require a
  bearer token on the Streamable HTTP path when
  `MCP_REQUIRE_BEARER=true`.
- For the researcher, wire `CONFIG.require_bearer_auth` /
  `CONFIG.bearer_token` (already exists in `config.py`) into
  `transports.streamable_http_app()`.
- Per-server `.env.example` documents the new env var.

**DoD**:
```
[ ] All 10 mcp_servers.json declare auth_type: bearer.
[ ] Streamable-HTTP request without a bearer returns 401 in production
    config; stdio transport unaffected (Inspector continues to work).
[ ] tests/test_auth.py: 401 on missing / wrong / expired token; 200 on valid.
[ ] validators stay strict-PASS.
```

### Sprint I — Strict CI gate + per-persona version override (~2 days)

Closes P0 #6 and P2 #15.

**Scope**:
- `.github/workflows/build-personas.yml`: drop `|| true` on
  `verify_mcp_portfolio.py` and on the asset / metadata regeneration
  steps. Any contract regression is now a hard fail.
- `scripts/persona_data.py` accepts an optional `version` field per
  persona (default `1.0.0`).
- `scripts/build_hpersona.py` + `scripts/generate_metadata.py` honor
  `p.get("version", "1.0.0")`. Path layout becomes
  `dist/packages/<id>/<version>/persona.hpersona`.

**DoD**:
```
[ ] CI fails (not warns) on any tool-name drift, validator failure,
    or portfolio regression.
[ ] Bumping researcher to 1.1.0 in persona_data.py changes only
    researcher artefacts; the other 9 stay at 1.0.0.
[ ] medical-ai-change-control.md "Version policy" section updated.
```

### Sprint J — Researcher multi-source connectors (~5 days)

Closes P1 #10. Largest single sprint; can be split.

**Scope** (in priority order):
1. `openalex_client.py` (cross-domain metadata).
2. `crossref_client.py` (DOI metadata + citations).
3. `pubmed_client.py` (NCBI E-utilities; covers PMC).
4. `nasa_ads_client.py` (aerospace + astrophysics).
5. `osti_client.py` (DOE / nuclear / energy).

Each connector must:
- live in its own module under `src/researcher/`,
- use a per-source `rate_limit.configure()` call,
- normalize results to `PaperRef` with proper `source` tag,
- handle 4xx / 5xx / network errors gracefully,
- ship at least 3 unit tests with `httpx.MockTransport`.

New tools shipped alongside:
- `search_openalex`, `search_crossref`, `search_pubmed`,
  `search_nasa_ads`, `search_osti`.

**DoD**:
```
[ ] 5 new connector modules + 5 new MCP tools.
[ ] Each tool has a sample / invalid arg pair in test_tools.py.
[ ] Inspector smoke test: each tool returns ≥ 1 result for a benign query.
[ ] Audit log emits source_consulted=[<source>] correctly.
[ ] No Sci-Hub / SSRF target reachable from any connector path
    (regression test).
```

### Sprint K — Reasoning tools + claim binding (~5 days)

Closes P1 #11.

**Scope**:
- Real `compare_papers` (axes: methods, datasets, results, limitations,
  novelty, contradictions). Output: `list[Claim]` per axis.
- Real `build_literature_brief` (sections: landscape, leading methods,
  gaps, open questions, citations). Flagship synthesis tool.
- `evidence_grader.py` — auto-grades claims E0..E6 based on source
  type / replication count.
- `citation_verifier.py` — confirms every emitted citation resolves to
  a paper at one of the allowed sources.

**DoD**:
```
[ ] No claim emitted without an EvidenceLevel.
[ ] No fabricated DOI / paper_id in any test fixture or live response.
[ ] Adversarial test suite covers: invented DOI rejected, abstract-only
    flagged, preprint flagged, contradictory sources reported, "cure"
    claim refused without E5+ evidence.
[ ] tests/test_research_quality.py: 50+ cases.
```

### Sprint L — Context Forge federation (~3 days)

Closes P1 #12.

**Scope**:
- `configs/context-forge/<server>.json` per persona.
- `configs/context-forge/virtual-servers.json` grouping creative /
  productivity / learning / wellness clusters.
- `docs/context-forge-registration.md` — recipe + verified end-to-end
  smoke test through the gateway.

**DoD**: documented in the existing platform-roadmap.md §H.

---

## 4. Cross-cutting tracks (run in parallel where possible)

| Track | Scope | Owner |
|---|---|---|
| **Observability** | OTEL traces with tenant + request_id propagation; Prometheus exporters for the metrics we already audit-log. | platform |
| **Secrets** | Pluggable provider (env / Vault / AWS SM); document rotation cadence. | platform |
| **Supply chain** | Pin all `>=` to `~=`; run `pip-audit` + `npm audit` weekly; record review in change-control. | platform |
| **Penetration test** | External red team on the doctor + researcher safety surfaces. Documented findings + close-out. | security |
| **Multi-tenant** | Per-tenant rate limit, per-tenant audit shard, per-tenant config override. | platform |
| **Backups** | Dry-run + restore procedure for the (Phase F+) Researcher knowledge stores. | ops |

---

## 5. Definition of "production ready"

The pack is production-ready when every box below is ticked. Anything else is "shipped to staging / beta".

```
[ ] Every persona MCP server reachable via Streamable HTTP /mcp under bearer auth.
[ ] docker compose -f docker-compose.mcp.yml up brings all 10 services
    healthy from a fresh checkout; healthchecks pass; compose network groups
    doctor + medical-mcp-toolkit.
[ ] Validators run strict (no `|| true`) in CI; any drift fails the build.
[ ] Gallery (https://ruslanmv.com/HomePilot/gallery.html) lists our 10
    personas; downloads return the real .hpersona artefact; SHA-256 verifies.
[ ] Doctor adapter has 30 days of audit-log review with zero P1 incidents.
[ ] Researcher has the 4 governance docs + dual-use safety + ≥ 3 source
    connectors + real compare_papers + real build_literature_brief.
[ ] No tool returns a claim without an EvidenceLevel.
[ ] No tool fetches from a non-allow-listed source.
[ ] Penetration test report on file with all P1/P2 findings closed.
[ ] OTEL traces flow from MCP client → server → upstream connector.
[ ] Secrets live in a vault, not env (or env policy is signed off).
[ ] Per-persona versioning works; bumping one does not drag the others.
[ ] Phase B (Medication Safety Checker) shipped or explicitly deferred.
```

---

## 6. Recommended execution order

```
Now           E3  (researcher governance docs + prompt + safety tests)
Week 1        F   (gallery publishing) ← unblocks distribution
Week 1-2      G   (Node Dockerfile + compose) ← parallel with F
Week 2        H   (bearer auth platform-wide)
Week 2        I   (strict CI gate + per-persona version)
Week 3-4      J   (multi-source connectors)
Week 4-5      K   (reasoning tools + claim binding)
Week 5        L   (Context Forge federation)
Cross-cut     observability / secrets / supply-chain / pen-test
```

E3 + F + G + H + I together cover every P0 / P1. J + K + L cover P2 and the remaining "enterprise feel". Everything in §4 runs in parallel from week 1.

The **first production milestone** is end of Sprint H — bearer auth + healthy compose stack + published gallery. That's the moment "ship to staging" becomes "ship to a real customer".

---

## 7. What this plan deliberately does NOT include

- **Phase B (Medication Safety Checker)** and **Phase C (Appointment Coordinator)** — those are scoped in `docs/medical/phase-{b,c}-*.md` and live on the long-tail roadmap (`docs/migration/platform-roadmap.md`). They do not block production of the existing 10 personas.
- **Specialist medical personas** (cardiology, oncology, …) — explicitly out of scope per `medical-ai-safety-policy.md` §10 Phase D.
- **Voice / phone interfaces** — out of scope.
- **Long-term per-user memory for the doctor or researcher** — needs its own privacy story before it lands.
- **Public Researcher tools that hit Sci-Hub or paywall-bypass** — refused at the source policy layer; not a roadmap item.
