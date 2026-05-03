# Medical AI Tool Policy

Companion to `medical-ai-safety-policy.md`. This file is the single source of
truth for **which upstream tools the General Doctor adapter will and will
not call**, and **which public tools the persona will and will not register**.
Code paths that violate this matrix are blocking review feedback.

## 1. Upstream `medical-mcp-toolkit` tools

| Tool | Risk | Adapter exposure | Why |
|---|---|---|---|
| `triageSymptoms` | high | **exposed (filtered)** — used by `doctor_red_flags` and inside `doctor_self_care` for the gate. | Core of the persona's safety story. Output is filtered through `safety.filter_lines` before any user sees it. |
| `searchMedicalKB` | medium | **exposed (filtered)** — used by `doctor_general_info`. | Educational only. Snippets routed through `safety.filter_text`. |
| `getDrugInfo` | high | adapter-only future | Phase B persona `Medication Safety Checker`; never directly. |
| `getDrugInteractions` | high | adapter-only future | Phase B; never directly. |
| `getDrugContraindications` | high | adapter-only future | Phase B; never directly. |
| `getDrugAlternatives` | very high | **never** | Requires clinician context; alternatives implies dose/substitution decisions. |
| `calcClinicalScores` | high | **never** | BMI / BSA / CrCl / eGFR — clinical-only output. |
| `scheduleAppointment` | medium | adapter-only future | Phase C `Appointment Coordinator`; needs explicit confirmation UX + privacy policy. |
| `getPatient` | very high | **never** | PHI. |
| `getPatientVitals` | very high | **never** | PHI. |
| `getPatientMedicalProfile` | very high | **never** | PHI. |
| `getPatient360` | very high | **never** | PHI aggregate. |

The adapter enforces the "never" column in two ways:

1. The `safety.exposed_upstream_tools` field in `server.json` is the
   declared allow-list (`triageSymptoms`, `searchMedicalKB`).
2. `upstream.UpstreamClient._fallback` only fabricates offline responses
   for the two allow-listed tools. PHI / clinical-score / scheduling tools
   return `status="error"` even with offline fallback enabled.

## 2. Public persona tools

The General Doctor persona registers exactly three tools today:

| Persona tool | Upstream call(s) | Refuses if … |
|---|---|---|
| `doctor_red_flags` | adapter regex first; `triageSymptoms` only if regex misses | adapter is disabled (rollback) |
| `doctor_general_info` | `searchMedicalKB` only | adapter is disabled |
| `doctor_self_care` | adapter regex first; `triageSymptoms` only if regex misses; refuses to render self-care if `acuity == "emergency"` upstream | red flag fires; adapter is disabled |

Future personas (none ship yet):

- **`Medication Safety Checker`** (Phase B) — calls `getDrugInteractions`
  + `getDrugContraindications` and a heavily filtered `getDrugInfo`.
  **Will not** call `getDrugAlternatives`. Output never includes a dose,
  a brand recommendation, or a "start/stop/switch" instruction.
- **`Appointment Coordinator`** (Phase C) — calls `scheduleAppointment`
  only after an explicit user confirmation step. Privacy policy must be
  in place before this ships.

## 3. Adapter feature flags (defence in depth)

`.env.example` ships with three flags defaulted to `false`:

```
ENABLE_PATIENT_TOOLS=false
ENABLE_DRUG_ALTERNATIVES=false
ENABLE_APPOINTMENT_SCHEDULING=false
```

These are belt-and-suspenders. The adapter does not check them today (the
allow-list of upstream tools is hard-coded), but they exist so a future
deployment cannot accidentally turn on a forbidden surface via env var.
A code change that *reads* one of these flags must be reviewed against
this policy.

## 4. Output filter categories

Every adapter response carries `blocked_content[]`. Categories and what
they mean (mirrors `safety.py`):

| Category | What we block |
|---|---|
| `diagnosis_language` | "you have X" / "it's X" → "Possible causes can include …, but only a clinician can diagnose." |
| `medication_dosing` | "Take 500 mg every 4 hours" / "5 mg of …" → "Ask a clinician or pharmacist about appropriate medication use." |
| `start_stop_medication` | "start your medication" / "stop the prescription" / "switch / increase / decrease / double / halve" → "Do not start or stop medication without professional guidance." |
| `clinical_orders` | `ECG`, `EKG`, `troponin`, `aspirin if not contraindicated`, `give aspirin`, `IV fluids`, `imaging now`, `stat CT/MRI/X-ray` → "Emergency clinicians may evaluate with tests and treatments as appropriate." |
| `specialist_attribution` | "Cardiology Specialist diagnosed acute MI" → "A clinician can evaluate this further." |
| `self_care_blocked_by_red_flag` | not a text rewrite — synthetic marker added to `blocked_content` when `doctor_self_care` returns the escalation envelope instead of self-care. |

A new category needs a new regex in `safety._DISALLOWED`, a new test in
`tests/test_safety.py`, and an entry in this table.

## 5. Adding a new public tool

1. Open a PR adding the tool to `personas/10-general-doctor/.../tools.json`,
   `mcp_servers.json`, `card.json`, `manifest.json`, and `persona_data.py`.
2. Add the tool to `mcp-servers/10-mcp-general-doctor/server.json` `tools[]`.
3. Implement the handler in `src/doctor/server.py`. The handler MUST:
   - Run `detect_red_flags(TriageInput(...))` on every free-text field
     before any upstream call.
   - Call only the upstream tools listed in the matrix above.
   - Pass every string field of the upstream response through
     `safety.filter_text` or `safety.filter_lines`.
   - Emit an `AuditEvent`.
4. Add a sample/invalid pair to a protocol-style test (see
   `tests/test_tools.py` patterns) and at least two adversarial cases
   to `tests/test_adversarial.py`.
5. Update this file's matrix.
