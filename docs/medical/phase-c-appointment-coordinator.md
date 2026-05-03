# Phase C — Appointment Coordinator (design)

**Status**: design only. Lands after Phase B (Medication Safety Checker)
ships and a privacy policy + explicit confirmation UX is in place.

## 1. Purpose

A persona that helps a user book a medical appointment with a clinician.
The bar for shipping is **higher** than for Phase B because this is the
first persona that intends to call a state-changing upstream tool
(`scheduleAppointment`). Until then, the persona stays in design.

## 2. Hard constraints

- The adapter MUST never schedule without an explicit user confirmation
  message in the same session. "Schedule it for Tuesday at 10am, please"
  is **not** confirmation; the adapter must echo back the proposed slot
  and the user must reply with an unambiguous confirm.
- Emergency triage takes precedence. If the user describes any red flag
  during the booking flow, the persona MUST stop the booking flow and
  escalate to the General Doctor → emergency path.
- The adapter MUST NOT call any patient tool (`getPatient*`,
  `getPatient360`) unless the deployment has shipped a real
  authentication + consent + audit-retention story. Those tools stay on
  the refused list by default.
- The adapter MUST NOT pre-fetch the user's medical record to "help"
  them describe their symptom. Data minimisation per
  `medical-ai-privacy.md`.

## 3. Persona shape

| Field | Value |
|---|---|
| `id` | `appointment-coordinator` |
| `name` | `Appointment Coordinator` |
| `role` | Appointment Coordinator |
| `class_id` | `secretary` (reused) |
| `tags` | `productivity`, `professional` |
| `nsfw` | `false` |
| `opening_message` | "Hi — I'm Appointment Coordinator. I can help you draft an appointment intake, propose times, and confirm a booking. I won't book anything until you explicitly confirm. If your situation feels urgent, please tell me — I'll route you to emergency triage instead." |

## 4. Tools (3, public)

| Tool | Upstream call | Notes |
|---|---|---|
| `appointment_intake` | none (in-adapter only) | Builds a structured intake from the user's free text — preferred date / time / specialty / brief reason. Output is a draft envelope (no upstream side effect). |
| `appointment_propose_slots` | `scheduleAppointment` (read mode if upstream supports it) OR an offline calendar stub | Returns 3 proposed slots in the user's timezone + a fallback. |
| `appointment_confirm` | `scheduleAppointment` (write) | **Only** runs if the inbound payload includes `confirm: true` AND the slot id matches one returned by `appointment_propose_slots` in the same session. Otherwise refuses with a clear error. |

## 5. Confirmation flow

```
appointment_intake → appointment_propose_slots → user picks a slot
                                              ↓
                          appointment_confirm with { slot_id, confirm: true }
                                              ↓
                                        upstream scheduleAppointment
                                              ↓
                                          confirmation envelope:
                                            { booked: true, slot, confirmation_id }
```

Anti-patterns the adapter explicitly refuses:

- `appointment_confirm` called without `confirm: true` → refused with
  `{"error": "missing_explicit_confirmation"}`.
- `appointment_confirm` called with a `slot_id` that wasn't proposed in
  this session → refused; sessions are short-lived in-memory mappings
  the adapter tracks per `request_id`.
- `appointment_confirm` called when the user's most recent free-text
  field contains a red flag → escalation envelope, **not** a booking.

## 6. Privacy posture

- The intake form does **not** ask for: full name, address, national ID,
  insurance number, MRN, exact date of birth.
- It accepts: free-text reason (filtered), preferred specialty
  (enum), preferred date/time window, contact preference (phone /
  email / clinic-portal — not the value, just the channel).
- Real PII (name, DOB, contact value) is collected by the booking
  endpoint outside the MCP tool surface, under the deployment's
  authentication + consent flow. The adapter never sees those fields.

## 7. Adapter wiring

```
Appointment Coordinator persona
        ↓
mcp-appointment-coordinator (Python FastMCP, port 9112)
        ↓
medical safety gateway (re-uses doctor's red-flag screen +
                        secretary-pro's draft-only policy)
        ↓
medical-mcp-toolkit /invoke
   └── scheduleAppointment    (read for propose, write for confirm)
   └── searchMedicalKB        (filtered, optional, for specialty hints)
```

Reuse: the doctor's red-flag detector AND the secretary-pro
`draft-only` policy together cover this persona's safety story. We do
not invent a new guardrail shape.

## 8. Tests

```
tests/test_safety.py            — red-flag short-circuit during intake;
                                  red-flag short-circuit during slot
                                  proposal; never-book-without-confirm.
tests/test_tools.py             — intake / propose / confirm happy paths.
tests/test_confirm_required.py  — confirm flow:
                                    no confirm field → refusal
                                    confirm + unknown slot → refusal
                                    confirm + matched slot → upstream call
tests/test_legacy_http.py       — same FastAPI TestClient pattern.
tests/test_adversarial.py       — jailbreak ("book without asking me"),
                                  PHI exfiltration (intake asking for SSN),
                                  red-flag mid-flow (chest pain in the
                                  reason field).
```

Minimum: 60+ tests before this persona is enabled in any environment
where real users can reach it.

## 9. Production gating signals (post-deploy)

- "Appointments booked without explicit `confirm: true`" — must be 0.
  Any non-zero value is an instant rollback.
- "Appointments booked while a red flag was present in the same
  session" — must be 0.
- "PII fields appearing in the audit log" — must be 0.

## 10. Definition of done

```
[ ] Privacy policy committed at docs/medical/medical-ai-privacy.md (the
    appointment-flow extension) and reviewed before code lands.
[ ] Confirmation UX agreed with HomePilot (every client renders
    "are you sure?" before sending appointment_confirm).
[ ] Phase-C persona ships in personas/12-appointment-coordinator/.
[ ] mcp-appointment-coordinator adapter at port 9112 with all three
    Sprint-D transports (streamable-http / legacy-http / hybrid).
[ ] 60+ tests, all green; the three "must be 0" production metrics
    are wired into the eval suite.
[ ] medical-ai-tool-policy.md / evaluation-suite / change-control
    updated.
[ ] Inspector configs added (single + bundled stdio + http).
[ ] docker-compose.mcp.yml entry added.
[ ] 30 days of Phase-B production audit logs reviewed before
    Phase-C is enabled in any user-facing environment.
```
