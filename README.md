# HomePilot  Personas Pack

This repository contains a suite of **essential personas** and their associated external MCP servers for the HomePilot project.  Each persona is packaged according to the HomePilot `.hpersona` v2 format and includes blueprint definitions, dependency declarations, assets and preview metadata.  The goal of these personas is to showcase how different personality types can be built and shared via HomePilot while adhering to the latest package schema and external server contract.

## Repository structure

- **`personas/`** – Source directories for each persona.  Inside each persona folder you will find a `hpersona/` directory with the package contents and a `gallery/` directory with preview assets and registry entries.
- **`mcp-servers/`** – External MCP servers that provide additional capabilities for each persona.  These are minimal Express applications exposing health and tool endpoints.
- **`packages/`** – Shared libraries and tooling used for building and validating persona packages.  These include the hpersona builder, an MCP server core, persona‑shared helpers and gallery tools.
- **`schemas/`** – JSON schemas used to validate the structure of manifests, blueprints, dependencies and preview cards.
- **`scripts/`** – Helper scripts for validating and building personas.  These scripts are invoked from npm scripts and the Makefile.
- **`docs/`** – Documentation describing the architecture, persona format, server contract, publishing workflow and strategy for making personas go viral.
- **`dist/`** – Built artifacts.  When you run the build scripts, generated `.hpersona` packages and gallery previews are placed under this folder.
- **`registry/`** – Registry metadata for personas and MCP servers.  After building, the registry files are used to publish packages to the HomePilot community gallery.

## Getting started

To install dependencies and run the validation scripts you can use the Makefile:

```sh
make install
make test
```

The `install` target will install Node dependencies for the root and workspace packages, while the `test` target will run simple validation scripts to ensure the persona and MCP server directories are present and contain the expected files.

To build the personas into `.hpersona` packages for distribution you would normally run the build scripts under the `scripts/` folder.  These have been stubbed out in this repository and can be extended to perform actual packaging.

For more details on the package format and design considerations please consult the documents in the `docs/` directory.