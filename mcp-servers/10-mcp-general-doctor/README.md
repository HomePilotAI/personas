# mcp-general-doctor (Python, FastMCP)

Python-native MCP **safety adapter** for the General Doctor persona. The
adapter is intentionally narrow: three canonical tools, every input swept for
emergency red flags before any upstream call, every output passed through a
content filter that strips diagnostic / dosing / clinical-order language, and
every call audited (no PHI).

The capability layer is the upstream
[`medical-mcp-toolkit`](https://github.com/ruslanmv/medical-mcp-toolkit) —
this adapter calls its `POST /invoke` over bearer-authed HTTP and exposes
**only** `triageSymptoms` and `searchMedicalKB` to the persona.

The constitution is in
[`docs/medical/medical-ai-safety-policy.md`](../../docs/medical/medical-ai-safety-policy.md).

## Tools (canonical contract)

| Name | Status | What it does |
|---|---|---|
| `doctor_red_flags` | sprint-C | Adapter regex screen → if hit, escalation envelope and **no upstream call**. Otherwise calls `triageSymptoms` and filters the response. |
| `doctor_general_info` | sprint-C | Calls `searchMedicalKB`, summarises 1-2 hits, scrubs diagnostic / dosing / clinical-order language. |
| `doctor_self_care` | sprint-C | Runs the same red-flag screen first; refuses to give self-care if anything fires. Otherwise general "rest, hydrate, monitor, seek care if …". |

The adapter never exposes the other 10 toolkit tools. Patient identifiers,
drug alternatives, clinical scores, and appointment scheduling are gated
behind future personas (see safety policy §10).

## Quickstart

```bash
cd mcp-servers/10-mcp-general-doctor
cp .env.example .env
pip install -e .
```

### stdio (MCP Inspector)

```bash
python -m doctor.server --transport stdio
```

### Streamable HTTP (Context Forge / Docker)

```bash
python -m doctor.server --transport streamable-http --host 0.0.0.0 --port 9110
```

Endpoint: `http://<host>:9110/mcp`.

### Talking to a real `medical-mcp-toolkit`

```bash
# In one shell:
git clone https://github.com/ruslanmv/medical-mcp-toolkit
cd medical-mcp-toolkit
make install && BEARER_TOKEN=dev-token make run-api   # listens on :9090

# In another shell, point the adapter at it:
export MEDICAL_MCP_URL=http://localhost:9090
export MEDICAL_MCP_BEARER_TOKEN=dev-token
python -m doctor.server --transport streamable-http --port 9110
```

If the toolkit is unreachable and `MEDICAL_MCP_OFFLINE_FALLBACK=true`
(the default), the adapter degrades to a deterministic local fake for
educational queries — but the **adapter's own** red-flag detector still runs,
so emergency screening keeps working with no upstream at all.

## Configuration

Every knob is an env var (see [`.env.example`](./.env.example)):

| Var | Default | Purpose |
|---|---|---|
| `DOCTOR_MCP_TRANSPORT` | `stdio` | `stdio` \| `streamable-http` \| `sse` |
| `DOCTOR_MCP_PORT` | `9110` | HTTP transport port |
| `GENERAL_DOCTOR_ADAPTER_ENABLED` | `true` | Rollback knob; when `false`, every tool returns a typed disabled envelope. |
| `MEDICAL_MCP_URL` | `http://localhost:9090` | Upstream toolkit base URL |
| `MEDICAL_MCP_BEARER_TOKEN` | — | Bearer for upstream `/invoke` |
| `MEDICAL_MCP_OFFLINE_FALLBACK` | `true` | Degrade gracefully if upstream is down |
| `ENABLE_PATIENT_TOOLS` | `false` | Defence-in-depth: never set true on this adapter |
| `ENABLE_DRUG_ALTERNATIVES` | `false` | Same |
| `ENABLE_APPOINTMENT_SCHEDULING` | `false` | Same |
| `DOCTOR_AUDIT_LOG_PATH` | (stderr) | JSON-lines audit log destination |
| `DOCTOR_AUDIT_HASH_USER_INPUT` | `true` | SHA-256 user text in audit logs (no raw PHI) |

## Layout

```
mcp-servers/10-mcp-general-doctor/
├── pyproject.toml
├── .env.example
├── README.md
├── server.json                     # MCP server registry metadata
├── src/doctor/
│   ├── __init__.py
│   ├── config.py                   # env-driven runtime config
│   ├── schemas.py                  # pydantic response shapes
│   ├── safety.py                   # red-flag detector + output filter
│   ├── upstream.py                 # HTTP client to medical-mcp-toolkit
│   ├── audit.py                    # no-PHI audit logging
│   └── server.py                   # FastMCP entry point
└── tests/
    ├── conftest.py                 # fake upstream + tool invocation helpers
    ├── test_safety.py              # red-flag + output-filter unit tests
    ├── test_tools.py               # 3 tools end-to-end
    ├── test_upstream.py            # httpx MockTransport happy + offline paths
    ├── test_audit.py               # no PHI escapes; hash digest stable
    └── test_server_contract.py     # FastMCP registers the canonical 3
```

## Safety guarantees

- **Adapter regex runs first.** If the user mentions chest pain, stroke
  signs, severe bleeding, suicidal ideation, overdose, pregnancy emergency,
  infant high fever, sudden severe headache, etc., we short-circuit to an
  escalation envelope and never query the upstream.
- **Output filter runs on every upstream response.** Diagnosis language,
  medication dosing, start/stop/switch instructions, clinical-order tokens
  (`ECG`, `troponin`, `aspirin if not contraindicated`, `IV fluids`,
  `imaging now`), and specialist-as-authority phrasing are rewritten.
  `blocked_content` enumerates which categories were caught.
- **Self-care is gated on triage.** Even when the adapter regex misses,
  if the upstream returns `acuity == "emergency"`, `doctor_self_care`
  refuses to give self-care guidance and returns the escalation envelope.
- **Adapter knows its limits.** Patient-360, drug alternatives, clinical
  scores, and appointment scheduling are categorically refused — never via
  the public tools, never via `auth=open`.

See `docs/medical/medical-ai-safety-policy.md` for the full constitution and
the release / rollback rules.
