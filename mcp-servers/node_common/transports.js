/**
 * Transport wiring for MCP servers.
 *
 * Two production transports are supported, matching the MCP spec:
 *   - stdio                — for local development and MCP Inspector launch.
 *   - streamable-http      — for Context Forge federation and Docker.
 *
 * stdio is connected to the McpServer directly. Streamable HTTP uses Express
 * with a per-request StreamableHTTPServerTransport (stateless mode), so each
 * request is a self-contained MCP exchange — friendly to load balancers and
 * the SDK's recommended pattern for HTTP deployments.
 */
import express from "express";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

const DEFAULT_HOST = "127.0.0.1";

/** Decide which transport to use based on env / argv. */
export function resolveTransportFromEnv(argv = process.argv) {
  const fromArg = argv
    .slice(2)
    .find((a) => a.startsWith("--transport="));
  const argTransport = fromArg ? fromArg.split("=")[1] : null;
  const transport = (
    argTransport ||
    process.env.MCP_TRANSPORT ||
    "stdio"
  ).toLowerCase();
  if (!["stdio", "streamable-http"].includes(transport)) {
    throw new Error(
      `Unsupported MCP_TRANSPORT=${transport}; expected stdio | streamable-http`
    );
  }
  return transport;
}

export async function startStdioTransport(server) {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  return { transport, close: async () => server.close() };
}

export async function startStreamableHttpTransport(server, options = {}) {
  const host = options.host || process.env.MCP_HOST || DEFAULT_HOST;
  const port = Number(options.port || process.env.MCP_PORT || 0);
  if (!port) {
    throw new Error(
      "Streamable HTTP transport requires a port (MCP_PORT or options.port)"
    );
  }
  const endpoint = options.endpoint || process.env.MCP_ENDPOINT || "/mcp";

  const app = express();
  app.use(express.json({ limit: options.jsonLimit || "1mb" }));

  // Liveness probe for Docker / Kubernetes. Not part of the MCP protocol.
  app.get("/health", (_req, res) => {
    res.json({
      status: "ok",
      server: server.server?.name || "mcp-server",
      transport: "streamable-http",
      timestamp: new Date().toISOString(),
    });
  });

  // Stateless: every request creates its own transport, processes the JSON-RPC
  // message and tears down. Matches the SDK's recommended HTTP pattern.
  app.post(endpoint, async (req, res) => {
    try {
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
      });
      res.on("close", () => {
        transport.close().catch(() => {});
      });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (err) {
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: "2.0",
          error: { code: -32603, message: String(err?.message || err) },
          id: null,
        });
      }
    }
  });

  // Inspector UI sometimes probes GET on the endpoint — answer politely.
  app.get(endpoint, (_req, res) => {
    res.status(405).json({
      jsonrpc: "2.0",
      error: { code: -32000, message: "Use POST for MCP messages" },
      id: null,
    });
  });

  const httpServer = await new Promise((resolve, reject) => {
    const s = app.listen(port, host, (err) => (err ? reject(err) : resolve(s)));
  });

  return {
    server: httpServer,
    address: `http://${host}:${port}${endpoint}`,
    close: () =>
      new Promise((resolve, reject) =>
        httpServer.close((err) => (err ? reject(err) : resolve()))
      ),
  };
}
