# @homepilot/gitpilot-connect

Setup wizard + runtime client that connects HomePilot personas to a
GitPilot MCP server.

**Strictly additive.** This package never reads or writes existing
HomePilot personas, never edits the registry, and never alters any
schema. It only *adds*:

* a new connection config under `~/.homepilot/connections/<name>.json`
* a new persona file under `~/.homepilot/personas/<slug>.hpersona`
* a new dependency manifest matching the existing
  `schemas/dependencies-mcp-servers.schema.json`

The wizard is opt-in: nothing happens unless the user clicks
"Connect GitPilot" in HomePilot's MCP Servers screen.

## Install

```bash
pnpm add @homepilot/gitpilot-connect
```

## Headless usage (CLI / scripts)

```ts
import { GitPilotClient, buildPersonaArtefacts } from '@homepilot/gitpilot-connect';

const client = new GitPilotClient({
  endpoint: 'http://localhost:8000/mcp-server/mcp',
  token: process.env.GITPILOT_MCP_SERVER_TOKEN
});

const probe = await client.test();
if (!probe.ok) throw new Error(probe.error);

const tools = await client.listTools();

const artefacts = buildPersonaArtefacts({
  config: {
    name: 'my-gitpilot',
    endpoint: client.endpoint,
    auth: { source: 'keychain', entryName: 'gitpilot-token' },
    enabledTools: tools.map((t) => t.name).slice(0, 6),
    scopes: ['read', 'plan'],
    workspace: { kind: 'github', owner: 'me', repo: 'app', branch: 'main' }
  }
});
// write artefacts.dependenciesJson + artefacts.personaContents wherever you like
```

## React wizard

```tsx
import { Wizard } from '@homepilot/gitpilot-connect/react';

<Wizard
  onComplete={(artefacts) => writePersonaToDisk(artefacts)}
  onCancel={() => closeModal()}
/>
```

The wizard is self-contained: 7 steps, resumable from
`localStorage`, never persists tokens.

## Steps

| # | Name | Required actions |
|---|------|------------------|
| 1 | Welcome / prerequisites | Check the GitPilot endpoint is reachable. |
| 2 | Endpoint & auth | Paste URL + token; "Test connection" runs a real probe. |
| 3 | Capability preview | Tick which tools the persona may call. |
| 4 | Workspace pick | Choose a GitHub repo + branch *or* a local folder. |
| 5 | Permissions | Toggle the read / plan / mutation scope flags. |
| 6 | Persona binding | Pick existing Coder persona or generate a new one. |
| 7 | Review & save | Diff preview, then write the two artefacts. |

## Best practices applied

* **Progressive disclosure** — ≤3 fields per step.
* **Test before commit** — steps 2 and 4 require a successful probe.
* **Diff before write** — step 7 shows the JSON the wizard will save.
* **Resumable** — wizard state survives reload via localStorage; tokens
  never written to disk.
* **Reversible** — "Save disabled" option; uninstall = delete two files.
* **Least privilege** — mutation scopes off by default; the wizard
  surfaces the policy banner before enabling them.
* **Idempotent re-run** — re-running for an existing connection name
  offers "Update" not "Add"; manifest-hash drift detection asks before
  overwriting hand-edits.
* **Accessibility** — keyboard-only flow, ARIA on the stepper, focus
  management on step change.

## Architecture

```
┌───────── HomePilot UI ─────────┐
│  Settings → MCP Servers        │
│   + Connect GitPilot button    │
│            │                   │
│            ▼                   │
│  <Wizard /> (this package)     │
│     │                          │
│     ├── client.ts ──▶ GitPilot MCP server (via HTTPS)
│     │                          │
│     ├── state.ts (localStorage, no token)
│     │                          │
│     └── persona-writer.ts ─▶ ~/.homepilot/{personas,connections}/
└────────────────────────────────┘
```

The client only talks to GitPilot during the wizard. At runtime the
Coder persona invokes tools through MCP Context Forge as usual.

## License

Apache-2.0
