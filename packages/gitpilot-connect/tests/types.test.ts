import { describe, expect, it } from 'vitest';
import { ConnectionConfigSchema, WorkspaceTargetSchema } from '../src/types.js';

describe('schemas', () => {
  it('rejects invalid connection names', () => {
    expect(() =>
      ConnectionConfigSchema.parse({
        name: 'Has Spaces',
        endpoint: 'http://x/mcp',
        auth: { source: 'inline', token: 'verysecret' },
        enabledTools: ['gitpilot.healthz'],
        scopes: ['read'],
        workspace: { kind: 'github', owner: 'a', repo: 'b', branch: 'main' }
      })
    ).toThrow();
  });

  it('rejects empty enabledTools', () => {
    expect(() =>
      ConnectionConfigSchema.parse({
        name: 'ok',
        endpoint: 'http://x/mcp',
        auth: { source: 'inline', token: 'verysecret' },
        enabledTools: [],
        scopes: ['read'],
        workspace: { kind: 'github', owner: 'a', repo: 'b', branch: 'main' }
      })
    ).toThrow();
  });

  it('accepts a local workspace', () => {
    expect(() =>
      WorkspaceTargetSchema.parse({ kind: 'local', path: '/tmp/app' })
    ).not.toThrow();
  });

  it('rejects a local workspace with empty path', () => {
    expect(() => WorkspaceTargetSchema.parse({ kind: 'local', path: '' })).toThrow();
  });
});
