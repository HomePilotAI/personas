# Medical AI Privacy

How the General Doctor adapter handles user health text. The principle is
**data minimisation**: never collect more than the tool needs, never store
raw health text by default, never share it with third parties beyond the
declared upstream `medical-mcp-toolkit`.

## 1. What we collect, on every call

Per-call, in-memory only:

- `symptoms[]` — the list passed by the client.
- `age`, `sex`, `topic`, `audience`, `free_text` — only when the tool
  schema accepts them.

Per-call, persisted (audit log only, no PHI):

- `request_id`, `timestamp`, `tool`, `risk_level`,
  `red_flag_detected`, `matched_red_flags[]` (these are *labels* like
  `"chest pain"`, not the user's exact wording),
- `upstream_tool`, `upstream_status`, `blocked_categories[]`,
- `latency_ms`, `error_type`,
- `user_input_sha256` — SHA-256 of the user's free-text fields when
  `DOCTOR_AUDIT_HASH_USER_INPUT=true` (default).

## 2. What we explicitly do **not** collect

The persona prompt and the adapter contract both refuse to ask for or
forward:

- full name, address, national ID, insurance number, medical record
  number, exact date of birth,
- patient identifiers in any form (`getPatient*` upstream tools are
  forbidden — see `medical-ai-tool-policy.md` §1),
- attachments / images / files,
- contact details of friends / family / clinicians.

A future authenticated patient workflow (Phase B+) may collect a subset
of these *only* under an explicit consent step plus the data-protection
controls below.

## 3. What we do **not** log

- Raw user free text (only SHA-256 when hashing is on).
- Bearer tokens.
- Upstream response bodies — the audit log records that a call happened
  and what status came back, never the contents.
- Anything that could be used to re-identify a user across requests.

The audit log line is a single JSON object with the fields above. If
operators run with `DOCTOR_AUDIT_HASH_USER_INPUT=false` they accept that
the digest field becomes empty — they do **not** get the raw text in the
log either way.

## 4. Where data flows

```
user → MCP client → mcp-general-doctor adapter
                        ├── adapter regex (in-memory) ── no network
                        └── upstream HTTP POST /invoke ── medical-mcp-toolkit
                                                                ↓
                                                       toolkit's data path
```

The adapter does not call any third-party service other than the
configured `MEDICAL_MCP_URL`. There is no telemetry beacon, no analytics,
no error-reporting webhook by default.

## 5. Retention

By default the audit log goes to stderr (the container log). Persisted
audit logs live wherever `DOCTOR_AUDIT_LOG_PATH` points; retention is the
responsibility of the operator's log infrastructure. We recommend:

| Data | Retention |
|---|---|
| Audit log (no-PHI events) | 30-90 days for ops debugging; aggregate counters can keep longer. |
| Upstream toolkit logs | per the toolkit's privacy policy. |
| User free-text | not retained by the adapter. |

## 6. Consent surface

The persona's first sentence is the disclaimer:

> "I can share general information, but please consult a healthcare
> professional for personal medical advice."

That sentence is the implicit consent surface for the educational scope.
Any change that broadens the scope (e.g. introducing a `Medication Safety
Checker` that reads drug interactions) must add an explicit confirmation
step before sending the user's drug list upstream and must update this
document.

## 7. Right to deletion

Because the adapter retains no PHI by default, "delete my data" reduces to:

1. Operator deletes the audit log entries that match the user's session
   (if persisted at all).
2. Upstream toolkit handles its own deletion per its policy.

The adapter exposes no API for "show me / forget me" because there is no
per-user record in the adapter. This is intentional.

## 8. PHI exposure incident

If an audit-log entry, a public response, or a third-party service ever
contains raw user health text or a patient identifier, follow
`medical-ai-incident-response.md`. PHI exposure is a P1 incident and
triggers an immediate adapter rollback per
`medical-ai-safety-policy.md` §9.
