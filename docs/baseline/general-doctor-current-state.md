# Baseline — `General Doctor` persona (pre-Sprint-C)

Captured before any medical adapter changes so behaviour can be diffed and
rolled back if needed.

## Persona files (commit `2a8870c`, sprint-B branch)

| Path | State |
|---|---|
| `personas/10-general-doctor/hpersona/manifest.json` | hpersona v2; capability_summary.personality_tools = `[doctor_general_info, doctor_red_flags, doctor_self_care]`. |
| `personas/10-general-doctor/hpersona/blueprint/persona_agent.json` | system_prompt declares non-clinical, escalates emergencies, never prescribes. |
| `personas/10-general-doctor/hpersona/dependencies/tools.json` | `doctor_general_info`, `doctor_red_flags`, `doctor_self_care`. |
| `personas/10-general-doctor/hpersona/dependencies/mcp_servers.json` | declares `mcp-general-doctor` at `http://localhost:9110`, transport=HTTP, auth=open, tools_provided = the 3 above. |
| `personas/10-general-doctor/hpersona/preview/card.json` | tools[] = the 3 above; gallery card. |
| `personas/10-general-doctor/gallery/registry-entry.json` | gallery shape; tags = `lifestyle`, `professional`. |

## MCP server files

| Path | State |
|---|---|
| `mcp-servers/10-mcp-general-doctor/server.json` | declares 3 tools (`doctor_general_info`, `doctor_red_flags`, `doctor_self_care`) with placeholder descriptions; `protocol: HTTP`, `transport: HTTP`, `auth_type: open`. |
| `mcp-servers/10-mcp-general-doctor/src/index.js` | Express stub: `app.post('/general_health_advice')` returns `Tool general_health_advice is not implemented yet.` Tool name does **not** match `server.json`. |
| `mcp-servers/10-mcp-general-doctor/src/tools.js` | `[{name: 'general_health_advice', ...}]` — also doesn't match. |
| `mcp-servers/10-mcp-general-doctor/src/index.py` | FastAPI shim using `python_common.app_base`; declares the 3 canonical tools, returns "not implemented yet" for each. |

`scripts/validate_mcp_servers.py` lists `10-mcp-general-doctor` in
`PENDING_MIGRATION`, so the existing drift across `server.json` / `tools.js` /
`index.js` is reported as WARN, not FAIL.

## Validator state on the baseline commit

```
[+] 01-09 servers (except 10) strict-PASS contract checks
[~] WARN 10-mcp-general-doctor: src/tools.js declares tool(s) not in server.json: ['general_health_advice']
[~] WARN 10-mcp-general-doctor: server.json declares tool(s) missing from src/tools.js: ['doctor_general_info', 'doctor_red_flags', 'doctor_self_care']
[~] WARN 10-mcp-general-doctor: src/index.js does not POST-handle declared tool(s): ['doctor_general_info', 'doctor_red_flags', 'doctor_self_care']
WARN — 3 drift issue(s) on 1 server(s) still pending MCP migration
PASS — every migrated MCP server is structurally valid and contract-consistent
```

## Behaviour today

- The Node entrypoint, the Python FastAPI shim, and `server.json` all return stubs.
- No upstream call to `medical-mcp-toolkit`.
- No safety filter, no red-flag escalation, no audit logging, no auth.
- The persona system prompt already declares the safety posture, but no tool implementation enforces it — that's what Sprint C lands.

## Why we don't delete this folder

The Sprint-C plan is non-destructive: the upgraded adapter lands in the same
folder using the same canonical tool names so the persona contract is stable,
but every change is committed atomically and is reversible by checking out
this baseline commit. See `docs/medical/medical-ai-safety-policy.md` for the
release/rollback rules.
