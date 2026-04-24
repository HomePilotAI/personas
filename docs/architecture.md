# Architecture

This document outlines the high‑level architecture of the **HomePilot viral personas** repository.

Each persona in `personas/` is packaged according to the HomePilot `.hpersona` v2 specification.  The package is a zip archive containing a manifest, blueprint definitions, dependency declarations, assets and preview metadata.  These files live under the `hpersona/` folder in each persona directory.  A corresponding `gallery/` folder holds a preview image and registry entry used by the community gallery.

External MCP servers reside in `mcp-servers/`.  These servers are implemented using Node.js and Express.  They expose `/health` and `/tools` endpoints to integrate with the HomePilot runtime.  Each server includes a `server.json` file describing its metadata and the tools it provides.

Shared utilities and tooling live under `packages/`.  These include a stubbed hpersona builder, an MCP server core library, persona‑shared helpers and gallery tools.  JSON schemas for validation are defined in the `schemas/` directory.

Helper scripts for validation and building can be found in `scripts/`, and documentation is contained within this `docs/` directory.