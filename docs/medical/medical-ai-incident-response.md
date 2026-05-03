# Medical AI Incident Response

Single-page playbook for incidents involving the General Doctor adapter,
the persona, or the upstream `medical-mcp-toolkit`. Tuned for speed, not
exhaustiveness.

## 1. Severity ladder

| Severity | Examples | Time-to-mitigate target |
|---|---|---|
| **P1 (life-safety)** | Confirmed emergency false-negative in production logs; medication dose escaping the filter; PHI / patient identifier in a public response; persona refusing to escalate a chest-pain / suicidal-ideation / overdose case. | < 15 minutes. |
| **P2 (safety degradation)** | Upstream offline rate sustained > 5% for 30 minutes; adapter error rate > 2% over 5 minutes; latency p99 > 8 s on `doctor_red_flags`; persona emitting a diagnosis verbatim. | < 60 minutes. |
| **P3 (quality)** | Disclaimer missing on a single response shape; specific red-flag category dropping in production despite no test regression; rare upstream 5xx spike. | < 24 hours. |

## 2. Mitigation, by severity

### P1

```
1.  Flip GENERAL_DOCTOR_ADAPTER_ENABLED=false in the deployment env.
    The adapter immediately starts returning AdapterDisabledResult on
    every call. No deploy required.
2.  Confirm via Inspector / curl that every tool returns the disabled
    envelope (no clinical content in the body).
3.  Capture the offending audit-log line (with sha256) — do NOT capture
    raw user text from any other source.
4.  Open an incident, severity P1.
5.  If the cause is a code path that already exists in main, also
    `git revert` the SHA that introduced it and tag a hotfix release.
6.  Do not re-enable the adapter until the failing case has a passing
    test in `tests/test_adversarial.py` or `tests/test_safety.py`.
```

### P2

```
1.  Decide: rollback or repair.
    - If the cause is upstream (toolkit outage, version skew), fail
      fast: leave adapter on, rely on offline_fallback, monitor.
    - If the cause is the adapter, flip the disable flag.
2.  Track latency / error / offline-rate metrics until they recover.
3.  Open an incident, severity P2; root cause within 24 hours.
```

### P3

```
1.  Open a ticket; no rollback needed.
2.  Add a regression test before fixing.
```

## 3. The disable flag is the kill switch

```
GENERAL_DOCTOR_ADAPTER_ENABLED=false
```

When set, every tool returns:

```json
{
  "disclaimer": "I can share general information, but please consult …",
  "tool": "<tool>",
  "adapter_enabled": false,
  "message": "The General Doctor adapter is currently disabled …"
}
```

No clinical content of any kind escapes. The persona stays callable, MCP
clients stay connected, no code change needed.

## 4. Per-trigger runbook

| Trigger | First check | First action |
|---|---|---|
| Emergency false-negative | Find the audit line; reproduce the input via test | P1 — disable + add red-flag pattern + test |
| Dose / prescription leak | Find the upstream snippet via the `blocked_content` field; reproduce | P1 — disable + add filter pattern + test |
| PHI in response | Verify in Inspector; reproduce in fixture | P1 — disable + identify the upstream tool + remove from `exposed_upstream_tools` if introduced by mistake |
| Upstream 5xx spike | Toolkit `/health` and version | P2 — confirm offline_fallback engaging; alert toolkit team |
| Adapter latency spike | Audit `latency_ms` p99 + `error_type` distribution | P2 — disable if > 8 s; investigate (httpx timeout? upstream? CPU?) |
| Disclaimer missing | Reproduce in Inspector | P3 — fix the schema's default; add test |

## 5. Comms templates

**Internal — P1**:

> "P1 medical AI incident: <one-line description>. Adapter disabled at
> <timestamp>. Symptoms: <…>. Audit line: <sha256 only>. Owner: <person>.
> Postmortem within 48 h."

**External — if the persona is publicly user-facing and a real user was
affected**:

> "We disabled the General Doctor companion at <timestamp> after detecting
> <category, no specifics>. Until it is re-enabled the assistant will tell
> users to contact a healthcare professional and will not provide health
> information. We will update when the issue is resolved."

We do not name patients, symptoms, or messages.

## 6. Postmortem checklist

For every P1 and P2:

```
[ ] Timeline (detection → mitigation → resolution).
[ ] Root cause (code / config / upstream / data).
[ ] Why our tests didn't catch it.
[ ] New test(s) added (must fail on the pre-fix code).
[ ] Doc update — at least medical-ai-change-control.md changelog row.
[ ] Action items with owners and dates.
```
