import { describe, expect, it, vi } from 'vitest';
import { GitPilotClient } from '../src/client.js';

function fakeFetch(handler: (req: Request) => Response | Promise<Response>): typeof fetch {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const req = new Request(url, init);
    return handler(req);
  }) as unknown as typeof fetch;
}

describe('GitPilotClient.test()', () => {
  it('reports reachable+authenticated when both stages succeed', async () => {
    const fetchImpl = fakeFetch(async (req) => {
      if (req.url.endsWith('/healthz')) {
        return new Response(
          JSON.stringify({ status: 'ok', tool_count: 10 }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        );
      }
      // tools/call gitpilot.healthz
      const body = await req.json();
      expect(body.method).toBe('tools/call');
      expect(body.tool).toBe('gitpilot.healthz');
      expect(req.headers.get('authorization')).toBe('Bearer abc');
      return new Response(
        JSON.stringify({ success: true, tool: 'gitpilot.healthz', result: { status: 'ok' } }),
        { status: 200, headers: { 'content-type': 'application/json' } }
      );
    });
    const client = new GitPilotClient({
      endpoint: 'http://gp/mcp-server/mcp',
      token: 'abc',
      fetchImpl
    });
    const out = await client.test();
    expect(out.ok).toBe(true);
    expect(out.reachable).toBe(true);
    expect(out.authenticated).toBe(true);
    expect(out.toolCount).toBe(10);
  });

  it('reports unreachable on 5xx', async () => {
    const fetchImpl = fakeFetch(async () => new Response('boom', { status: 503 }));
    const out = await new GitPilotClient({ endpoint: 'http://gp/mcp-server/mcp', fetchImpl }).test();
    expect(out.ok).toBe(false);
    expect(out.reachable).toBe(false);
  });

  it('reports reachable but unauthenticated when probe 401s', async () => {
    const fetchImpl = fakeFetch(async (req) => {
      if (req.url.endsWith('/healthz')) {
        return new Response(JSON.stringify({ status: 'ok', tool_count: 5 }), {
          status: 200,
          headers: { 'content-type': 'application/json' }
        });
      }
      return new Response('Unauthorized', { status: 401 });
    });
    const out = await new GitPilotClient({
      endpoint: 'http://gp/mcp-server/mcp',
      token: 'wrong',
      fetchImpl
    }).test();
    expect(out.reachable).toBe(true);
    expect(out.authenticated).toBe(false);
    expect(out.ok).toBe(false);
  });

  it('listTools parses the MCP tools/list envelope', async () => {
    const fetchImpl = fakeFetch(
      async () =>
        new Response(
          JSON.stringify({
            tools: [
              { name: 'gitpilot.healthz', scope: 'read' },
              { name: 'gitpilot.create_pr', scope: 'mutation' }
            ]
          }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        )
    );
    const tools = await new GitPilotClient({
      endpoint: 'http://gp/mcp-server/mcp',
      fetchImpl
    }).listTools();
    expect(tools).toHaveLength(2);
    expect(tools[0].name).toBe('gitpilot.healthz');
  });

  it('callTool requires a token', async () => {
    const client = new GitPilotClient({ endpoint: 'http://gp/mcp-server/mcp' });
    await expect(client.callTool('gitpilot.healthz', {})).rejects.toThrow(/token/);
  });
});
