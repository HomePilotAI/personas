// packages/gitpilot-connect/src/persona-writer.ts
//
// Produces the two artefacts step 7 ("Review & Save") writes:
//
//   1. dependencies-mcp-servers.json: matches HomePilot's existing
//      schemas/dependencies-mcp-servers.schema.json. The wizard appends
//      a single entry; nothing existing is modified.
//
//   2. <slug>.hpersona: a minimal but valid HomePilot persona of kind
//      "coder" referencing the connection by name (NOT by URL or
//      token). Rotating credentials later does not require rewriting
//      personas.
//
// Idempotence:
//   * buildPersonaArtefacts() returns the bytes; it does not touch the
//     filesystem. The caller chooses where to write (browser download,
//     Tauri bridge, Node fs, etc.).
//   * A stable manifestHash is returned so the wizard can detect drift
//     when the user re-runs against the same connection name.

import { ConnectionConfig } from './types.js';

export interface PersonaArtefacts {
  /** Filename hint, e.g. "my-gitpilot.dependencies-mcp-servers.json". */
  dependenciesFilename: string;
  dependenciesJson: string;
  /** Filename hint, e.g. "coder-my-gitpilot.hpersona". */
  personaFilename: string;
  personaContents: string;
  /** Stable hash over the canonical JSON of both artefacts. */
  manifestHash: string;
}

const DEPENDENCIES_SCHEMA_VERSION = 1;

export interface BuildOptions {
  config: ConnectionConfig;
  /** Persona display name (step 6). Defaults to "Coder ({connection-name})". */
  personaName?: string;
  /** Optional system-prompt override (step 6). */
  systemPrompt?: string;
}

export function buildPersonaArtefacts(opts: BuildOptions): PersonaArtefacts {
  const { config } = opts;
  const personaName = opts.personaName ?? `Coder (${config.name})`;
  const personaSlug = `coder-${config.name}`;

  const dependencies = {
    schema_version: DEPENDENCIES_SCHEMA_VERSION,
    servers: [
      {
        name: config.name,
        description: 'GitPilot MCP server bound by gitpilot-connect wizard',
        url: config.endpoint,
        auth_type: 'bearer',
        registry_id: 'gitpilot-mcp-server',
        source: { type: 'registry', registry_id: 'gitpilot-mcp-server' },
        transport: 'streamable-http',
        protocol: 'mcp/1.0',
        tools_provided: [...config.enabledTools]
      }
    ]
  };

  const persona = {
    package_version: 1,
    schema_version: 1,
    kind: 'coder',
    project_type: 'persona',
    name: personaName,
    slug: personaSlug,
    created_at: new Date().toISOString(),
    capability_summary: {
      scopes: [...config.scopes],
      workspace: config.workspace
    },
    contents: {
      system_prompt:
        opts.systemPrompt ??
        defaultSystemPrompt(config.name, config.workspace),
      mcp_servers_dependency: `${config.name}.dependencies-mcp-servers.json`
    }
  };

  const dependenciesJson = JSON.stringify(dependencies, null, 2) + '\n';
  const personaContents = JSON.stringify(persona, null, 2) + '\n';
  const manifestHash = stableHash(dependenciesJson + personaContents);

  return {
    dependenciesFilename: `${config.name}.dependencies-mcp-servers.json`,
    dependenciesJson,
    personaFilename: `${personaSlug}.hpersona`,
    personaContents,
    manifestHash
  };
}

function defaultSystemPrompt(
  connectionName: string,
  workspace: ConnectionConfig['workspace']
): string {
  const ws =
    workspace.kind === 'github'
      ? `the GitHub repository ${workspace.owner}/${workspace.repo} on branch ${workspace.branch}`
      : `the local folder ${workspace.path}`;
  return [
    `You are a Coder persona connected to GitPilot via the MCP server "${connectionName}".`,
    `Your working scope is ${ws}.`,
    'Always plan changes with gitpilot.plan before any mutation.',
    'Never call gitpilot.create_pr without explicit user confirmation.',
    'Prefer gitpilot.describe_repo and gitpilot.classify_topology to understand context.'
  ].join(' ');
}

/** Tiny non-cryptographic stable hash (FNV-1a 32-bit, hex). */
function stableHash(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = (hash * 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, '0');
}
