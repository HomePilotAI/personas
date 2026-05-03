# Medical AI Change Control (PCCP-style)

Mirrors the spirit of the FDA *Predetermined Change Control Plan for AI-
enabled medical software*: every change to the adapter, persona, or upstream
contract is **versioned, tested, monitored, and reversible**. This file is
the operating procedure.

## 1. Scope

Applies to changes in:

- `mcp-servers/10-mcp-general-doctor/**`
- `personas/10-general-doctor/**`
- `scripts/persona_data.py` (the doctor row)
- Adapter ↔ `medical-mcp-toolkit` contract (`server.json:upstream`)
- `docs/medical/**`

Out of scope: changes to other personas, gallery layout, build tooling.

## 2. Risk classes

| Class | Examples | Required sign-off |
|---|---|---|
| **R0 — docs only** | typo in a markdown file, comment polish | one engineer self-review |
| **R1 — internal-only behaviour** | tweak the audit log fields, tighten a config default, add a developer-only flag | one engineer + tests pass |
| **R2 — public response shape** | new field in `RedFlagsResult`, new `blocked_content` category, new persona tool description | one engineer + tests pass + tracker updated |
| **R3 — safety-relevant** | red-flag regex change, output-filter regex change, new persona tool, new upstream tool exposed | engineer + safety review + adversarial-suite delta + release checklist run |
| **R4 — high-risk** | adapter rollback knob removed, PHI tool surfaced, dose/prescription tool added | safety review + ops sign-off + staged rollout (shadow → beta → default) |

Anything that touches the safety policy (`medical-ai-safety-policy.md` §3,
§4, or §5) is at least **R3**.

## 3. Required artefacts per change

Every PR touching the doctor (above scope) ships with:

```
[ ] Updated tests covering the new behaviour.
[ ] Adversarial test added or updated if the change is R3+.
[ ] Audit log line schema unchanged OR migration note in the PR.
[ ] docs/medical/medical-ai-change-control.md changelog row appended.
[ ] If R3+: docs/medical/medical-ai-tool-policy.md updated.
[ ] If R3+: docs/medical/medical-ai-evaluation-suite.md updated.
[ ] Rollback plan stated in the PR description (one paragraph).
```

## 4. Versioning

- **Adapter version** = `mcp-servers/10-mcp-general-doctor/server.json:version`.
  Bumped per SemVer:
  - patch — R0/R1.
  - minor — R2 (new optional field, new tool description).
  - major — R3/R4 (renamed tool, removed tool, new public tool,
    safety-relevant regex change that adds/removes refusals).
- **Adapter ↔ toolkit contract version** = `server.json:upstream.min_version`.
  Bumped when the toolkit makes a breaking change to `/invoke` payload,
  removes `triageSymptoms` or `searchMedicalKB`, or changes bearer-auth.

## 5. Rollback plan template

Every R3+ change must answer in the PR:

```
- Trigger: <error-rate / false-negative case / performance>
- Detection: <which audit-log field, dashboard, or test>
- Action: <flip GENERAL_DOCTOR_ADAPTER_ENABLED=false / revert SHA / rebuild>
- Comms: <who tells users; if API consumers, what we tell them>
- Validation post-rollback: <which tests + which Inspector smoke cases>
```

The default rollback for everything in scope is:

```
git revert <sha>      # reverts code
GENERAL_DOCTOR_ADAPTER_ENABLED=false  # disables adapter without a deploy
```

The persona dependency keeps pointing at `mcp-general-doctor`; the adapter
returns the typed `AdapterDisabledResult` envelope instead of clinical data.

## 6. Changelog

Append below for every change in scope.

| Date | SHA | Risk | Summary | Rollback verified? |
|---|---|---|---|---|
| 2026-05-03 | sprint-C/batch-2 | R3 | Initial Python FastMCP safety adapter (3 tools, red-flag detector, output filter, upstream HTTP client, audit logger). | yes — validators pass; adapter-disabled envelope works; legacy entrypoint shim restored to MCP-native shape. |
| 2026-05-03 | sprint-C/batch-3 | R3 | Persona dependency swap: auth=bearer, transport=streamable-http, upstream block declared, tools_provided ordered red_flags-first. | yes — manual revert tested against sprint-C/batch-1 baseline; validators stay green. |
| 2026-05-03 | sprint-C/batch-4 | R2 | Adversarial test suite + governance docs (this file, tool-policy, evaluation-suite, privacy, incident-response, release-checklist). | n/a — pure tests + docs. |
| 2026-05-03 | sprint-D/batch-1 | R1 | Production deployment fixes: Dockerfile COPY order (pyproject + README before `pip install .`); Makefile uses `pip install -e ".[dev]"`; top-level docker-compose.yml replaced with `include:` of docker-compose.mcp.yml; build_hpersona.py also updates `personas/<id>/gallery/registry-entry.json` size_bytes; backfilled all 10 gallery entries (0 → real). | yes — `make pytest` green; `compose config` parses; validators strict-PASS. |
| 2026-05-03 | sprint-D/batch-2 | R2 | Legacy HTTP / Context Forge compat: new `--transport legacy-http \| hybrid`; `src/doctor/legacy_http.py` (FastAPI app exposing `/doctor_red_flags`, `/doctor_general_info`, `/doctor_self_care`, `/context-forge/{tools,call}`); fastapi + uvicorn now mandatory deps; `server.json` declares `supported_transports[]` and `legacy_endpoints{}`; 9 new TestClient cases (55/55 pytest). | yes — disable knob unchanged; revert transport flag to fall back to FastMCP-only. |
| 2026-05-03 | sprint-D/batch-3 | R3 | Safety hardening: structured pediatric thresholds (<3 mo any fever; <5 y high fever / breathing / lethargy / cyanosis / severe dehydration) and pregnancy / postpartum signals (bleeding / severe pain / decreased fetal movement / hemorrhage / leg swelling) via new `pregnant` / `postpartum` boolean fields and float `age` (fractional for under-1s); default emergency guidance now lists 112 / 911 / 999 / 000 / 119; persona opening message rewritten to make the limitation visible; `medical-ai-safety-policy.md` §2.5 (production env overrides) and §3.1 (structured signals table) added. 81/81 pytest. | yes — `git revert <sha>`; new fields are optional, no schema break for legacy callers. |

### Version policy (current)

The General Doctor adapter, persona, and pyproject all carry version
`1.0.0`. Per the medical AI policy, **`1.0.0` is the genuine first release
because nothing has been published to the gallery yet**: the live
`docs/registry.json` on `ruslanmv/HomePilot` still serves placeholder
entries. The first publish to the live gallery is the moment we bump to
`1.1.0` (or `2.0.0` if the change is breaking) — at that point we will
extend `scripts/persona_data.py` with a per-persona `version` override
and update `scripts/build_hpersona.py` + `scripts/generate_metadata.py`
to honour it, so individual personas can iterate without dragging the
whole pack along. Until then, the platform-wide `VERSION = "1.0.0"`
constant remains correct.

## 7. Monitoring after merge

For an R3+ change, the on-call rotation watches the adapter audit log for
24 hours after a release-tag deploy. The metrics in
`medical-ai-evaluation-suite.md` §3 are checked at +1h, +6h, +24h. If any
of the rollback triggers in `medical-ai-safety-policy.md` §9 hit, the
on-call flips `GENERAL_DOCTOR_ADAPTER_ENABLED=false` immediately and
opens an incident.
