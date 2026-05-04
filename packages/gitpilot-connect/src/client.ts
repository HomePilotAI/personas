// packages/gitpilot-connect/src/client.ts
//
// Tiny REST client for the GitPilot MCP server. Used by:
//   * step 2 (connection test)
//   * step 3 (capability listing)
//   * step 4 (repo + branch listing)
//   * runtime (the persona invokes tools through MCP Context Forge,
//     not through this client; this client is wizard-only).
//
// We deliberately avoid bringing in a heavyweight HTTP library: the
// global fetch is enough, and keeping the dep surface tiny lets the
// wizard run inside HomePilot's existing bundle without bloat.

import { z } from 'zod';

export interface GitPilotClientOptions {
  endpoint: string;
  /** Bearer token for authenticated calls. Optional: tools/list is public. */
  token?: string;
  /** Per-request timeout in milliseconds. */
  timeoutMs?: number;
  /** Pluggable fetch (used by tests). */
  fetchImpl?: typeof fetch;
}

export interface ConnectionTestResult {
  ok: boolean;
  reachable: boolean;
  authenticated: boolean;
  toolCount: number;
  responseTimeMs: number;
  error?: string;
}

const HealthzSchema = z.object({
  status: z.string(),
  server: z.string().optional(),
  tool_count: z.number().int().nonnegative()
});

const ToolDefSchema = z.object({
  name: z.string(),
  description: z.string().optional(),
  scope: z.string().optional(),
  inputSchema: z.unknown().optional()
});

const ToolListSchema = z.object({
  tools: z.array(ToolDefSchema)
});

const CallEnvelopeSchema = z.object({
  success: z.boolean().optional(),
  tool: z.string().optional(),
  scope: z.string().optional(),
  call_id: z.string().optional(),
  elapsed_ms: z.number().optional(),
  result: z.unknown().optional()
});

function healthzPath(endpoint: string): string {
  // The bridge mounts {mount}/healthz alongside the JSON envelope at {mount}.
  return endpoint.endsWith('/') ? `${endpoint}healthz` : `${endpoint}/healthz`;
}

export class GitPilotClient {
  private readonly endpoint: string;
  private readonly token?: string;
  private readonly timeoutMs: number;
  private readonly fetchImpl: typeof fetch;

  constructor(opts: GitPilotClientOptions) {
    this.endpoint = opts.endpoint;
    this.token = opts.token;
    this.timeoutMs = opts.timeoutMs ?? 10_000;
    this.fetchImpl = opts.fetchImpl ?? fetch;
  }

  /** Step 2 "Test connection" implementation. Never throws. */
  async test(): Promise<ConnectionTestResult> {
    const started = Date.now();
    let reachable = false;
    let authenticated = false;
    let toolCount = 0;
    let error: string | undefined;

    // Stage 1 — unauthenticated /healthz.
    try {
      const resp = await this.timed(() =>
        this.fetchImpl(healthzPath(this.endpoint), { method: 'GET' })
      );
      reachable = resp.ok;
      if (resp.ok) {
        const body = HealthzSchema.parse(await resp.json());
        toolCount = body.tool_count;
      } else {
        error = `healthz HTTP ${resp.status}`;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }

    // Stage 2 — authenticated tools/call gitpilot.healthz (only if we have a token).
    if (reachable && this.token) {
      try {
        const out = await this.callTool('gitpilot.healthz', {});
        authenticated = !!out?.success;
        if (!authenticated) {
          error = error ?? 'auth probe failed';
        }
      } catch (e) {
        error = error ?? (e instanceof Error ? e.message : String(e));
      }
    }

    return {
      ok: reachable && (this.token ? authenticated : true),
      reachable,
      authenticated,
      toolCount,
      responseTimeMs: Date.now() - started,
      error
    };
  }

  /** Step 3 "capability preview". */
  async listTools(): Promise<z.infer<typeof ToolListSchema>['tools']> {
    const resp = await this.timed(() =>
      this.fetchImpl(this.endpoint, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ method: 'tools/list' })
      })
    );
    if (!resp.ok) throw new Error(`tools/list HTTP ${resp.status}`);
    return ToolListSchema.parse(await resp.json()).tools;
  }

  /** Generic tools/call. */
  async callTool(name: string, args: Record<string, unknown>): Promise<z.infer<typeof CallEnvelopeSchema>> {
    if (!this.token) throw new Error('callTool requires a token');
    const resp = await this.timed(() =>
      this.fetchImpl(this.endpoint, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${this.token}`
        },
        body: JSON.stringify({
          method: 'tools/call',
          tool: name,
          arguments: args
        })
      })
    );
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`tools/call ${name} HTTP ${resp.status} ${text}`);
    }
    return CallEnvelopeSchema.parse(await resp.json());
  }

  // ---- internal --------------------------------------------------------
  private async timed<T>(fn: () => Promise<T>): Promise<T> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      return await Promise.race<T>([
        fn(),
        new Promise<T>((_, reject) => {
          timer = setTimeout(
            () => reject(new Error(`timeout after ${this.timeoutMs}ms`)),
            this.timeoutMs
          );
        })
      ]);
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
}
