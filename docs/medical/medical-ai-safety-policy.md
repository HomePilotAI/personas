# Medical AI Safety Policy — `General Doctor` persona

Applies to the `General Doctor` persona, the `mcp-general-doctor` adapter,
and any future medical persona (Medication Safety Checker, Appointment
Coordinator) built on top of `medical-mcp-toolkit` and the Medical-AI-
Assistant-System reference architecture.

This is the constitution every commit in `mcp-servers/10-mcp-general-doctor/`
must respect. Violations are blocking review feedback, not nits.

## 1. What General Doctor is and is not

**Is**: a general health information companion. Calm, plain-language
education; emergency triage that escalates fast; self-care guidance only when
no red flags are present; explicit "consult a clinician" framing on every
output.

**Is not**:

- a clinician — never says "I diagnose you with…", never replaces a doctor.
- a prescriber — never names a medication dose or recommends starting,
  stopping, switching, or substituting a prescription drug.
- a 911 — for a life-threatening situation we point at emergency services
  and stop talking, we don't try to manage the call.
- a clinical decision-support tool — we do not present `troponin`, `ECG`,
  `aspirin if not contraindicated` and similar clinical-order language to
  end users.

## 2. Industry framing

The architecture follows current consensus health-AI guidance:

| Principle | Source we align with | What it means in this repo |
|---|---|---|
| Safety-first | WHO ethics & governance for AI for health (LMM addendum, 2024) | Every symptom request must pass red-flag triage before education or self-care. |
| Human oversight | EU AI Act 2024 (medical software is high-risk) | Persona escalates emergencies and recommends clinician review on personal medical decisions; never claims to replace one. |
| Lifecycle change control | FDA PCCP for AI-enabled medical software | Every adapter change is versioned, tested, monitored and reversible (see `docs/medical/medical-ai-change-control.md`). |
| Responsible AI assurance | CHAI Responsible AI Guide; Joint Commission + CHAI guidance | Safety tests, audit logs, local validation, escalation metrics — all required before a tool ships in adapter mode. |
| Physician-centred deployment | AMA position 2025 | Specialist personas stay internal until governance, evaluation, and human-oversight model are in place. |

## 2.5. Production environment overrides

Defaults in `.env.example` are tuned for **development**. Operators
deploying to production MUST override the following:

| Variable | Dev default | Production value |
|---|---|---|
| `MEDICAL_MCP_OFFLINE_FALLBACK` | `true` (degrade gracefully) | `false` (fail loudly so the operator sees the upstream outage) |
| `MEDICAL_MCP_BEARER_TOKEN` | (empty / dev-token) | a real bearer token rotated per ops policy |
| `DOCTOR_AUDIT_LOG_PATH` | (stderr) | a path that the log shipper picks up |
| `DOCTOR_AUDIT_HASH_USER_INPUT` | `true` | leave `true` (any value other than `true` requires consent + privacy review) |

The adapter's own red-flag screen is **not** affected by
`MEDICAL_MCP_OFFLINE_FALLBACK` — it always runs locally before any upstream
call. Disabling offline fallback only changes how `doctor_general_info`
behaves when the upstream `searchMedicalKB` is unreachable.

## 3. Red-flag escalation list (mandatory)

The adapter's `safety.py` MUST detect at least the following and short-circuit
to an emergency envelope before any other output:

```
chest pain (+ sweating | radiating | shortness of breath)
shortness of breath (severe / sudden)
stroke symptoms / facial droop / one-sided weakness / sudden confusion
severe / uncontrolled bleeding
loss of consciousness / fainting
seizure
anaphylaxis / severe allergic reaction (throat swelling, difficulty breathing)
suicidal ideation / self-harm intent
overdose / poisoning
severe head injury / suspected concussion
sudden severe headache ("worst headache of my life")
sudden vision loss
severe abdominal pain
pregnancy bleeding / severe pregnancy pain / decreased fetal movement
high fever in infant (< 3 months any fever; < 2 yrs ≥ 39 °C)
stiff neck with fever
severe dehydration / blue lips / cyanosis
rapidly worsening symptoms
```

False positives are acceptable. **False negatives on this list are blocking.**

### 3.1 Structured signals (in addition to free-text regex)

The adapter accepts optional structured fields and escalates on them
**without** requiring the matching free-text wording:

| Field | Threshold | Escalation label |
|---|---|---|
| `age < 3 months` | any fever word OR temp ≥ 38°C | `infant fever (age <3 months)` |
| `age < 5 years` | temp ≥ 39°C | `high fever in young child` |
| `age < 5 years` | breathing difficulty / wheeze / grunt / retraction | `breathing difficulty in young child` |
| `age < 5 years` | lethargy / unresponsive / floppy / unrousable | `lethargy in young child` |
| `age < 5 years` | cyanosis / blue lips / blue around mouth | `cyanosis in young child` |
| `age < 5 years` | severe dehydration / sunken eyes / no wet diaper / no tears | `severe dehydration in young child` |
| `pregnant: true` | bleeding / spotting / hemorrhage | `pregnancy bleeding (structured)` |
| `pregnant: true` | severe / sharp / 10/10 pain | `severe pregnancy pain (structured)` |
| `pregnant: true` | decreased / no fetal movement / fewer kicks | `decreased fetal movement (structured)` |
| `postpartum: true` | heavy / soaking / gushing bleeding | `postpartum hemorrhage (structured)` |
| `postpartum: true` | severe pain / swollen leg / chest pain | `postpartum severe pain or swelling (structured)` |

Temperature parsing accepts `°C` / `°F` / `C` / `F` with body-temperature
sanity bounds (30-45°C, 86-113°F) so a `100 mg` dosing string never reads
as `100°`. Structured signals run **before** the upstream toolkit, so an
8-week-old's fever escalates with no `triageSymptoms` call at all.

## 4. Output filtering rules

Every tool response goes through the output filter before reaching the user.
The filter rewrites any clinical-order or diagnostic language:

| Disallowed pattern | Replacement |
|---|---|
| "You have <diagnosis>" / "It's <diagnosis>" | "Possible causes can include …, but only a clinician can diagnose." |
| "Take <drug> <dose>" / "<dose> mg" | "Ask a clinician or pharmacist about appropriate medication use." |
| "Start / stop / switch / increase / decrease <medication>" | "Do not start or stop medication without professional guidance." |
| Clinical-order tokens (`ECG`, `troponin`, `aspirin if not contraindicated`, `IV …`, `imaging now`, `give …`) | "Emergency clinicians may evaluate with tests and treatments as appropriate." |
| Specialist-as-authority phrasing ("Cardiology Specialist Agent diagnosed …") | Replaced with non-specialist summary in plain language. |

## 5. Tool exposure policy

The adapter MUST refuse to expose:

- `getPatient`, `getPatientVitals`, `getPatientMedicalProfile`, `getPatient360`
  — PHI; require auth + consent + audit not yet in place.
- `getDrugAlternatives` — requires clinician context; high liability.
- `calcClinicalScores` — clinical-only.

Allowed via the adapter (filtered):

- `triageSymptoms` — feeds `doctor_red_flags` and gate inside `doctor_self_care`.
- `searchMedicalKB` — feeds `doctor_general_info` (educational only).

Future, gated behind their own personas:

- `getDrugInteractions`, `getDrugContraindications`, filtered `getDrugInfo` →
  `Medication Safety Checker` persona, sprint after Sprint C.
- `scheduleAppointment` → `Appointment Coordinator` persona, after privacy
  policy + confirmation UX is in place.

## 6. Authentication

- Adapter ↔ toolkit: bearer token (`MEDICAL_MCP_BEARER_TOKEN`). Adapter
  refuses to start in production mode without it.
- Adapter ↔ MCP client: same `auth_type: bearer` declared in the persona's
  `mcp_servers.json` (offline development uses an explicit dev token in
  `.env.example`).
- Tokens never appear in audit logs.

## 7. Audit logging

Every adapter call logs (no PHI):

```
request_id, timestamp, tool, risk_level, red_flag_detected,
upstream_tool, upstream_status, blocked_categories, latency_ms, error_type
```

Raw user symptom text is **not** logged unless the deployment has a
documented privacy policy + consent flow. Default deployment hashes the
input and logs only the hash plus the structured fields above.

## 8. Release checklist (must be green before ship)

```
[ ] All persona JSON validates (validate_personas.py).
[ ] MCP server contract clean (validate_mcp_servers.py).
[ ] Adapter tests pass: contract + safety + adversarial.
[ ] Red-flag suite covers every entry in section 3.
[ ] Output-filter suite covers every row in section 4.
[ ] No PHI in test fixtures or logs.
[ ] Upstream auth + offline fallback both exercised in tests.
[ ] Rollback verified by re-pointing dependencies/mcp_servers.json
    at the legacy entrypoint and confirming validators still pass.
```

## 9. Rollback triggers

Roll back the adapter immediately on any of:

- Adapter error rate > 2% over a 5-minute window.
- Any confirmed emergency false-negative in production logs.
- Any output containing a medication dose, prescription, or "start/stop"
  language that escapes the filter.
- Any patient identifier exposed in a public response.
- Latency p99 > 8 s on `doctor_red_flags`.

Rollback method: revert
`personas/10-general-doctor/hpersona/dependencies/mcp_servers.json`
to its pre-Sprint-C version (commit `2a8870c`) and disable adapter via
`GENERAL_DOCTOR_ADAPTER_ENABLED=false`. The legacy stub remains in tree.

## 10. Roadmap

Phase A — Sprint C, this branch: General Doctor with the 3 canonical tools,
red-flag escalation, KB-backed education, self-care gated on triage.

Phase B — sprint after Sprint C: `doctor_medication_safety_check` (uses
`getDrugInteractions` + `getDrugContraindications` only; never `Alternatives`
or dosing).

Phase C — later: `doctor_appointment_intake` with explicit confirmation flow
and a privacy policy.

Phase D — clinician-facing only, gated behind clinical governance review:
specialist routing using the Medical-AI-Assistant-System internal agents.
Public users continue to see the General Doctor persona; specialist content
is summarised in plain language and never attributed to a "specialist agent".
