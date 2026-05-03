# Design — Auto-install MCP Servers from Persona Bundles

**Status**: design only. No code changes in this commit. Implementation
plan + acceptance criteria + open questions for the maintainers.

**Goal**: when a user clicks **Install Persona** in HomePilot for one of
the 10 additive personas (Researcher, General Doctor, Creator Muse, …),
the persona's MCP servers (`mcp-researcher`, `mcp-general-doctor`, …)
auto-install locally — clone, install deps, allocate a port, spawn the
process, register in Context Forge — exactly as the existing community
personas do today (e.g. *Marcus Chen* installs `marcus-teams-coordinator`
as a community bundle).

After install, the new servers MUST appear in `Tools › MCP Servers ›
Installed Servers` alongside `hp-web-research`, `hp-exec-briefing`, and
the other built-in / virtual entries.

---

## 1. How HomePilot's installer works today (recon)

Probed `backend/app/agentic/mcp_installer.py` and `community/`. Four
`source_type` values are wired:

| `source_type` | Handler | Where it expects to find the server |
|---|---|---|
| `builtin` | `_install_builtin_server` | Bundled inside HomePilot itself; resolved by `builtin_id` in `available_ids`. |
| `community_bundle` | `install_community_bundle` | Pre-vendored in `community/shared/bundles/<id>/` (e.g. `scarlett_secretary`, `nova_collaborator`, `angel_stylist`). |
| `external` | `install_external_server` | Cloned from a git URL into `community/external/<id>/`. Tracked in `community/external/registry.json`. Port allocated from `community/shared/registry/port_map.json`. |
| `registry` | (lookup only) | Discoverable in a remote registry / Context Forge gateway. |

The Install-Persona flow:

1. Parses the `.hpersona` bundle (specifically `dependencies/mcp_servers.json`).
2. For every server name listed there, looks up the merged registry of
   the four source types above.
3. If found → runs the matching installer; success ⇒ port allocated +
   process spawned + registered in Context Forge.
4. If **not** found → marks the entry **Missing** in the Install dialog
   and shows: *"Some MCP servers cannot be auto-installed. The persona
   will work but may have limited functionality."* — exactly the
   message we see today for Researcher and General Doctor.

So *Marcus Chen* installs because `marcus-teams-coordinator` is bundled
under `community/shared/bundles/`. Our 10 servers fail because they
exist in `HomePilotAI/personas/mcp-servers/` but are **not** in any of
the four registries HomePilot consults.

---

## 2. What's missing for our 10 personas

Our `dependencies/mcp_servers.json` carries the runtime contract
(transport, port, /mcp endpoint, bearer policy, upstream block) but
**not** the install contract. HomePilot doesn't know:

- Where the source code lives (which repo, which branch, which subdir).
- How to install dependencies (`pip install -e .` / `npm install`).
- How to start the process (`python -m doctor.server …` /
  `node src/index.js`).
- Whether it has an upstream dependency (`mcp-general-doctor` requires
  `medical-mcp-toolkit`).
- Whether it requires any env vars (e.g.
  `MEDICAL_MCP_BEARER_TOKEN`).

---

## 3. Recommended design

### 3.1 One install model: `external` with subdir-clone

Our 10 servers live in **one repo**, multiple subdirectories. Cloning
the entire repo per server is wasteful. Use a single clone of
`HomePilotAI/personas` shared by all 10 servers, with each server
identified by its subdirectory.

```
~/.homepilot/community/external/
└── homepilotai-personas/                ← single shallow clone
    ├── .git/
    ├── mcp-servers/
    │   ├── 01-mcp-creator-muse/         ← per-server install root
    │   ├── 02-mcp-style-muse/
    │   ├── …
    │   └── 10-mcp-general-doctor/
    └── shared/                           ← shared deps (node_common, etc.)
```

`community/external/registry.json` gets one entry per server pointing
at the right subdir:

```json
{
  "mcp-researcher": {
    "source_type": "external",
    "source_repo": "https://github.com/HomePilotAI/personas",
    "source_ref":  "main",
    "source_subdir": "mcp-servers/04-mcp-researcher",
    "runtime": "python",
    "install_cmd": "python -m pip install -e \".[dev]\"",
    "start_cmd":   "python -m researcher.server --transport streamable-http --host 127.0.0.1 --port {PORT}",
    "health_url":  "http://127.0.0.1:{PORT}/mcp",
    "transport":   "streamable-http",
    "auth_type":   "open",
    "tools":       ["search_arxiv","read_paper","summarize_paper","compare_papers","build_literature_brief"],
    "env_required": [],
    "upstream":     null
  },
  …
}
```

### 3.2 Install manifest in the .hpersona bundle

Add **one new optional field** to each persona's
`dependencies/mcp_servers.json`:

```json
{
  "schema_version": 1,
  "servers": [
    {
      "name": "mcp-researcher",
      "default_port": 9104,
      "transport": "streamable-http",
      "tools_provided": ["search_arxiv", …],

      "install": {
        "source_type":   "external",
        "source_repo":   "https://github.com/HomePilotAI/personas",
        "source_ref":    "main",
        "source_subdir": "mcp-servers/04-mcp-researcher",
        "runtime":       "python",
        "install_cmd":   "python -m pip install -e .",
        "start_cmd":     "python -m researcher.server --transport streamable-http --host 127.0.0.1 --port {PORT}",
        "health_url":    "http://127.0.0.1:{PORT}/mcp",
        "env_required":  [],
        "upstream":      null
      }
    }
  ]
}
```

The `install` block is the **single source of truth** HomePilot needs.
When it's present, the server is auto-installable; when it's absent
(legacy bundles), the existing "Missing" warning fires — full backwards
compat.

### 3.3 Doctor needs an upstream dependency

`mcp-general-doctor` calls `medical-mcp-toolkit` at runtime. Encode
that as a separate dependency entry that HomePilot installs first:

```json
"upstream": {
  "name":          "medical-mcp-toolkit",
  "source_repo":   "https://github.com/ruslanmv/medical-mcp-toolkit",
  "source_ref":    "main",
  "runtime":       "python",
  "install_cmd":   "make install",
  "start_cmd":     "make run-api PORT={PORT}",
  "health_url":    "http://127.0.0.1:{PORT}/health",
  "env_required":  ["MEDICAL_MCP_BEARER_TOKEN"]
}
```

HomePilot's installer treats `upstream` as a recursive install, so the
toolkit comes up before the doctor adapter and `MEDICAL_MCP_URL` /
`MEDICAL_MCP_BEARER_TOKEN` get populated automatically.

### 3.4 Port allocation

Each server has a `default_port` (9101-9110). HomePilot already
allocates ports from `community/shared/registry/port_map.json`. The
installer:

1. Tries `default_port` first.
2. If occupied → walks `9101-9199` for the first free port.
3. Records the chosen port in `port_map.json` so future starts reuse it.

`{PORT}` in `start_cmd` / `health_url` is substituted at spawn time.

### 3.5 Context Forge registration

After install, HomePilot already calls
`server_manager.register_external(...)` to add the new MCP into the
local Context Forge. Our servers need:

- `endpoint`: `http://127.0.0.1:{PORT}/mcp`
- `transport`: `streamable-http`
- `auth_type`: matches the `auth_type` in `server.json`
- `tools`: matches `tools_provided` in the dependency entry

Once registered, they appear in the *Installed Servers* list with the
same UI affordances as `hp-web-research`, `hp-exec-briefing`, etc.

---

## 4. Required changes to the personas pack

1. **Add `install` block to each `mcp_servers.json`** (10 files). One
   per persona, all pointing at the same repo + subdir convention.
2. **Update `scripts/persona_data.py`** with a per-persona
   `install_manifest` field; `scripts/generate_metadata.py` writes it
   into the dependency file. Single source of truth keeps regeneration
   safe.
3. **Update `docs/medical/medical-ai-tool-policy.md`** §1 with the new
   `install` field shape; update `docs/research/source-policy.md` with
   the same.
4. **Validator extension**: `validate_personas.py` already checks
   tool-name consistency. Add a new check:
   *"if `dependencies/mcp_servers.json` declares an `install` block, it
   MUST carry `source_type`, `start_cmd`, and `health_url`"*.
5. **CI step**: add a smoke test in `.github/workflows/build-personas.yml`
   that, for one persona (the researcher), runs the install + start +
   health check sequence end-to-end so the install manifest can't drift
   from reality.

No runtime code changes inside the MCP servers themselves. The
`install` block is pure metadata.

---

## 5. Required changes to HomePilot

1. **`mcp_installer.install_external_server`**: extend to accept a
   `source_subdir` field. When set, after `git clone` the installer
   `cd`s into `community/external/<repo>/<subdir>/` before running
   `install_cmd` and `start_cmd`.
2. **Recursive `upstream` handling**: when an entry has an `upstream`
   sibling, install it first (idempotent — multiple personas can share
   the same upstream toolkit), capture its allocated port, and inject
   `MEDICAL_MCP_URL=http://127.0.0.1:<upstream_port>` /
   `MEDICAL_MCP_BEARER_TOKEN=<generated>` into the dependent server's
   environment.
3. **`env_required` UX**: when the install manifest declares required
   env vars, the Install dialog grows a small form before the install
   step asking the user to paste the value (with "skip" allowed for
   non-required entries). Values are stored in
   `~/.homepilot/community/external/<server>/.env` (chmod 600), never
   echoed to logs.
4. **Lifecycle UI**: existing Manage / Discover panel already has
   start / stop / uninstall affordances per server — no UI change
   needed. The new servers slot into the existing list.
5. **First-run dependency check**: before calling `install_cmd`,
   verify Python ≥ 3.11 / Node ≥ 22 are on `$PATH`. Surface the gap
   to the user instead of failing inside pip / npm.

---

## 6. End-to-end user flow

```
User: clicks "Install Persona" on Researcher card in the gallery
  ↓
HomePilot: downloads researcher-1.0.0.hpersona via /community/download/...
  ↓
HomePilot: parses dependencies/mcp_servers.json
            sees install.source_type = "external"
            sees install.source_subdir = "mcp-servers/04-mcp-researcher"
            sees install.runtime = "python"
  ↓
HomePilot: shows "Install: Researcher" dialog
            MCP Servers:
              ✅ mcp-researcher (will install: external, ~5s)
            (no env vars required for researcher)
            [Cancel] [Install Persona]
  ↓
User: Install Persona
  ↓
HomePilot:
  1. git clone --depth 1 https://github.com/HomePilotAI/personas
       → ~/.homepilot/community/external/homepilotai-personas/
  2. cd mcp-servers/04-mcp-researcher && pip install -e .
  3. allocate port 9104 (default) or next free in 9101-9199
  4. spawn: python -m researcher.server --transport streamable-http
              --host 127.0.0.1 --port 9104
  5. wait for /mcp to respond (timeout 30s)
  6. register in local Context Forge:
       endpoint=http://127.0.0.1:9104/mcp transport=streamable-http
       tools=[search_arxiv, read_paper, …]
  7. record in community/external/registry.json
  8. record in port_map.json
  ↓
UI: card moves from "Discover" to "Installed"
    Tools › MCP Servers › Installed shows: hp-web-research, …,
    mcp-researcher (5 tools, Streamable HTTP, 127.0.0.1:9104)
```

For **General Doctor**, step 4 is preceded by a recursive install of
`medical-mcp-toolkit` (port 9090), then the doctor adapter spawns with
`MEDICAL_MCP_URL=http://127.0.0.1:9090` and the user-supplied bearer
token captured in step 3 of the Install dialog.

---

## 7. Lifecycle: install / start / stop / status / uninstall

| Action | What happens |
|---|---|
| install | clone repo (or fetch latest if already cloned) → cd subdir → run `install_cmd` → register in `community/external/registry.json`. Does NOT spawn. |
| start | allocate or reuse port → run `start_cmd` → poll `health_url` → register in Context Forge. |
| status | check process is alive AND `health_url` responds 200/405 → green. Anything else → red with last 50 lines of the install log. |
| stop | SIGTERM the process → wait 5s → SIGKILL → unregister from Context Forge. Port stays reserved in `port_map.json`. |
| uninstall | stop → remove subdir from `community/external/<repo>/<subdir>/` → drop registry + port_map entries → remove `~/.homepilot/community/external/<server>/.env`. Repo clone is kept if other servers from the same repo are still installed; removed otherwise. |

All five actions are already implemented for `external` servers in
`mcp_installer.py` / `mcp_uninstaller.py`. The only addition is
`source_subdir` awareness in install + start path resolution.

---

## 8. Failure modes + rollback

| Failure | Detection | Mitigation |
|---|---|---|
| `git clone` fails (network, auth) | non-zero exit | install fails; user sees the git error verbatim. No partial state on disk (rollback by `rm -rf`). |
| `install_cmd` fails (missing toolchain, dep conflict) | non-zero exit | fail with last 50 lines of `community/external/install_logs/<server>.log`; clone left in place so the user can retry without re-cloning. |
| `start_cmd` runs but `health_url` never green | timeout | kill process; install dialog shows red; the *Manage* tab keeps the entry so the user can retry start. |
| Port conflict | `bind` error | installer auto-walks to next free port and retries once. |
| Upstream toolkit fails | upstream's own install / health failure | the dependent server is **not** installed; user sees "upstream `medical-mcp-toolkit` failed: <reason>". Fully reversible. |
| Missing env var | install dialog form is empty | install button stays disabled; user gets a clear message. |

Hard rule: **install MUST be idempotent and reversible**. A failed
install MUST leave the user's HomePilot in the same state as before.

---

## 9. Phased delivery

| Phase | Deliverable | Owner |
|---|---|---|
| 1 | Add the `install` block to each `dependencies/mcp_servers.json` (this repo); regenerate; validators check the new fields | personas repo |
| 2 | Extend `mcp_installer.install_external_server` with `source_subdir` (HomePilot repo) | HomePilot repo |
| 3 | Recursive `upstream` install for the doctor (HomePilot repo) | HomePilot repo |
| 4 | Add the 10 entries to `community/shared/registry/shared_registry.json` so they are discoverable from `Discover › Add Server` even before the persona is installed | HomePilot repo |
| 5 | CI smoke test: spawn the researcher, hit /mcp, list tools, kill | personas repo |
| 6 | Doc: `docs/INSTALL_PERSONA.md` in HomePilot describing the user flow + supported runtimes (Python 3.11+ / Node 22+) | HomePilot repo |
| 7 | Beta: ship behind a feature flag `INSTALL_EXTERNAL_PERSONAS=true`. After two weeks of green telemetry, flip default | platform |
| 8 | GA: remove the flag; *Install Persona* button on every persona in the gallery actually installs everything | platform |

Phases 1-3 unblock the **Researcher** (no upstream); phase 3 unblocks
the **Doctor** (needs medical-mcp-toolkit upstream). Phases 4-8 are
polish.

---

## 10. Open questions for the HomePilot maintainer

1. **Subdir-clone vs per-server tarball.** Subdir-clone is lighter (one
   400 MB shallow clone vs ten ~10 MB tarballs) but assumes git is on
   the user's machine. Tarballs work everywhere but require us to ship
   ten new files on R2. **Recommend: subdir-clone, with a tarball
   fallback for the air-gapped case.**

2. **Repo pinning.** Should `source_ref` track `main` (always-fresh,
   risk of breakage) or pin to a release tag (`personas-1.0.0`)? **Recommend:
   pinned tag in `install` block; HomePilot's "Update server" action
   bumps to the latest tag.**

3. **Sandboxing.** External servers run as the same user as HomePilot.
   Is that acceptable, or do we want each spawned MCP to run under a
   dedicated user / cgroup? **Recommend: same-user for v1; revisit
   when we add unaudited community servers.**

4. **Bearer-token bootstrap for the doctor.** Should HomePilot generate
   a fresh token per install (and inject it into both the toolkit and
   the adapter) or require the user to paste their own? **Recommend:
   auto-generate `secrets.token_urlsafe(32)`, store in `.env` chmod 600,
   user sees "✓ token generated" in the dialog.**

5. **Upgrade flow.** When the persona pack ships a new version (1.1.0),
   does HomePilot keep both versions installed or replace the old one?
   **Recommend: replace by default with a `--keep-old` opt-out so users
   can pin a specific version.**

6. **Telemetry.** Do we need anonymous install-success / install-fail
   counts to help the personas-pack maintainers? **Recommend: yes, but
   gated behind `--allow-install-telemetry` flag, off by default.**

---

## 11. Summary

The current "Missing" message comes from one missing piece of metadata:
the `install` block in each persona's `dependencies/mcp_servers.json`.
Add that field on the personas side, teach HomePilot's existing
`external` installer about subdir-clone + recursive upstream deps, and
the **Install Persona** button starts working for our 10 additive
personas exactly the way it works for *Marcus Chen* today.

Implementation effort: ~3 days personas-side, ~5 days HomePilot-side,
1 day for the CI smoke test, 1 day for the docs. Total: ~2 weeks
including the beta flag + GA gate.

The 10 servers are already shipping real MCP, so once the install glue
lands, **Tools › MCP Servers › Installed Servers** will list:

```
hp-web-research              2 tools
hp-exec-briefing             4 tools
hp-decision-room             8 tools
hp-default-readonly         39 tools
hp-home-default              2 tools
mcp-creator-muse             1 tool      ← new
mcp-style-muse               2 tools     ← new
mcp-secretary-pro            3 tools     ← new
mcp-researcher               5 tools     ← new
mcp-personal-trainer         3 tools     ← new
mcp-room-stylist             3 tools     ← new
mcp-storyteller              3 tools     ← new
mcp-exam-coach               3 tools     ← new
mcp-mindfulness-coach        3 tools     ← new
mcp-general-doctor           3 tools     ← new (+ medical-mcp-toolkit upstream)
```

24 tools added, 24 personas live in the gallery, one click installs
both the persona and its MCP server.
