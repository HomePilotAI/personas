# Baseline — upstream `medical-mcp-toolkit`

Reference: <https://github.com/ruslanmv/medical-mcp-toolkit>

This is **not** vendored into this repo. Our adapter
(`mcp-servers/10-mcp-general-doctor/`) calls the toolkit over HTTP at runtime.
This baseline describes the toolkit shape we depend on so any incompatible
upstream change is caught quickly.

## HTTP surface

| Method + path | Purpose |
|---|---|
| `GET /health` | plain-text liveness (`"ok"`). |
| `GET /healthz` | (planned in upstream upgrade) JSON liveness with `version`, `tools_registered`, `database`. |
| `GET /schema` | MCP components JSON schema. |
| `GET /tools` | List registered tool names. |
| `GET /tools/metadata` | (planned upgrade) per-tool risk/exposure policy. |
| `POST /invoke` | `{ "tool": "<name>", "args": {...} }` — bearer-authenticated. |

Bearer token is taken from the toolkit's `BEARER_TOKEN` env var.

## Tools registered upstream (12)

| Name | Adapter exposure | Risk | Notes |
|---|---|---|---|
| `triageSymptoms` | **used by `doctor_red_flags`, `doctor_self_care`** | high | Returns `acuity`, `rulesMatched`, `nextSteps`. We expand red-flag detection in our own `safety.py` because the upstream rule set is intentionally minimal. |
| `searchMedicalKB` | **used by `doctor_general_info`, `doctor_self_care`** | medium | Education only. Source confidence comes back as KB hits; we summarise into safe wording. |
| `getDrugInfo` | adapter-only future (`doctor_medication_safety_check` phase 2) | high | Never exposed directly. |
| `getDrugInteractions` | adapter-only future | high | Phase 2 only. |
| `getDrugContraindications` | adapter-only future | high | Phase 2 only. |
| `getDrugAlternatives` | not exposed | very high | Requires clinician context. |
| `calcClinicalScores` | not exposed | high | Clinical-only output. |
| `scheduleAppointment` | adapter-only future (`doctor_appointment_intake` phase 2) | medium | Requires explicit user confirmation. |
| `getPatient` | not exposed | very high | PHI. |
| `getPatientVitals` | not exposed | very high | PHI. |
| `getPatientMedicalProfile` | not exposed | very high | PHI. |
| `getPatient360` | not exposed | very high | PHI aggregate. |

The exposure column above is enforced by the adapter; the toolkit itself can
serve all 12 tools to authenticated callers.

## Triage shape we depend on

`triageSymptoms(age, sex, symptoms[], duration_text?)` returns:

```json
{
  "acuity": "routine | urgent | emergency",
  "advice": "self-care | …",
  "rulesMatched": ["chest pain", "diaphoresis"],
  "nextSteps": ["ECG", "troponin", "aspirin if not contraindicated"]
}
```

The adapter's safety filter rewrites `nextSteps` before the user ever sees it
— "ECG / troponin / aspirin" is clinical-decision content and must not appear
in a public response.

## KB shape we depend on

`searchMedicalKB(query, limit?)` returns:

```json
{
  "hits": [
    { "title": "...", "url": "...", "score": 0.92, "snippet": "..." }
  ]
}
```

The adapter strips the URL by default and converts the `snippet` into
educational language; raw clinical content is rephrased through the safety
filter.

## Adapter ↔ toolkit contract version

| Field | Value | Bumped when |
|---|---|---|
| `adapter_min_toolkit_version` | `1.0.0` | Toolkit makes a breaking change to `/invoke` payload shape, removes `triageSymptoms`/`searchMedicalKB`, or changes the bearer-auth header. |
| `adapter_min_toolkit_endpoints` | `/health`, `/tools`, `/invoke` | A required endpoint goes away. |

If the toolkit moves outside that envelope the adapter falls back to its
**offline mode** (returns a deterministic stub via the local fake upstream)
and surfaces `upstream_status: "degraded"` so the persona can apologise
gracefully without breaking emergency screening — red flags are detected by
the adapter's own regex layer, not by the toolkit.
