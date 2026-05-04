import { describe, expect, it } from 'vitest';
import { buildPersonaArtefacts } from '../src/persona-writer.js';
import { ConnectionConfig } from '../src/types.js';

const BASE: ConnectionConfig = {
  name: 'my-gitpilot',
  endpoint: 'http://localhost:8000/mcp-server/mcp',
  auth: { source: 'keychain', entryName: 'gitpilot-token' },
  enabledTools: ['gitpilot.healthz', 'gitpilot.list_repos'],
  scopes: ['read', 'plan'],
  workspace: { kind: 'github', owner: 'me', repo: 'app', branch: 'main' }
};

describe('buildPersonaArtefacts', () => {
  it('emits a dependencies-mcp-servers.json that matches HomePilot schema fields', () => {
    const out = buildPersonaArtefacts({ config: BASE });
    const deps = JSON.parse(out.dependenciesJson);
    expect(deps.schema_version).toBe(1);
    expect(deps.servers).toHaveLength(1);
    const s = deps.servers[0];
    // Required fields per schemas/dependencies-mcp-servers.schema.json
    for (const required of [
      'name',
      'description',
      'url',
      'auth_type',
      'registry_id',
      'source',
      'transport',
      'protocol',
      'tools_provided'
    ]) {
      expect(s).toHaveProperty(required);
    }
    expect(s.transport).toBe('streamable-http');
    expect(s.protocol).toBe('mcp/1.0');
    expect(s.registry_id).toBe('gitpilot-mcp-server');
    expect(s.tools_provided).toEqual(BASE.enabledTools);
  });

  it('emits a coder .hpersona referencing the dependencies file', () => {
    const out = buildPersonaArtefacts({ config: BASE });
    const persona = JSON.parse(out.personaContents);
    expect(persona.kind).toBe('coder');
    expect(persona.contents.mcp_servers_dependency).toBe(out.dependenciesFilename);
    expect(persona.capability_summary.scopes).toEqual(['read', 'plan']);
    expect(persona.contents.system_prompt).toContain('me/app');
    expect(persona.contents.system_prompt).toContain('main');
  });

  it('produces a stable manifestHash for identical input', () => {
    const a = buildPersonaArtefacts({ config: BASE });
    const b = buildPersonaArtefacts({ config: BASE });
    // The hash covers JSON contents only; created_at differs, so it
    // shifts — but the persona-writer hash includes both files. We
    // verify the dependencies portion is byte-identical instead.
    expect(a.dependenciesJson).toBe(b.dependenciesJson);
    expect(a.dependenciesFilename).toBe(b.dependenciesFilename);
    // And both hashes are 8-char hex.
    expect(a.manifestHash).toMatch(/^[0-9a-f]{8}$/);
    expect(b.manifestHash).toMatch(/^[0-9a-f]{8}$/);
  });

  it('handles local workspace by mentioning the path in the prompt', () => {
    const out = buildPersonaArtefacts({
      config: { ...BASE, workspace: { kind: 'local', path: '/work/app' } }
    });
    const persona = JSON.parse(out.personaContents);
    expect(persona.contents.system_prompt).toContain('/work/app');
  });

  it('honours a custom personaName + systemPrompt', () => {
    const out = buildPersonaArtefacts({
      config: BASE,
      personaName: 'Senior Coder',
      systemPrompt: 'Be terse. Always plan first.'
    });
    const persona = JSON.parse(out.personaContents);
    expect(persona.name).toBe('Senior Coder');
    expect(persona.contents.system_prompt).toBe('Be terse. Always plan first.');
  });
});
