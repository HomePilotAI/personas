# gitpilot-mcp-server (HomePilot catalog entry)

This directory is HomePilot's pointer at GitPilot's MCP server. It is
*not* the server source; GitPilot lives at
<https://github.com/ruslanmv/gitpilot> and the server module is
`gitpilot/mcp_server.py` there.

## How users get here

1. **Settings → MCP Servers → + Connect GitPilot** in HomePilot.
2. The `wizard_compatible: true` flag in `register.json` tells HomePilot
   to launch `@homepilot/gitpilot-connect` (the wizard package).
3. The wizard runs the seven steps (welcome → endpoint → capabilities →
   workspace → permissions → persona → review).
4. On finish the wizard writes a new `coder-*.hpersona` and a sibling
   `*.dependencies-mcp-servers.json` under `~/.homepilot/`.

No existing HomePilot files are modified at any point.

## Setup checklist on the GitPilot side

The wizard cannot start a GitPilot for you. The user must already have:

```bash
# In the GitPilot repo:
export GITPILOT_EXPOSE_MCP_SERVER=true
export GITPILOT_MCP_SERVER_TOKEN=$(openssl rand -hex 32)
# Optional, only if you want create_pr / run_skill:
export GITPILOT_MCP_SERVER_ALLOW_MUTATION=true
export GITPILOT_MCP_SERVER_MUTATION_TOKEN=$(openssl rand -hex 32)
make run
```

The wizard step 1 probes `/mcp-server/mcp/healthz` on this URL.
