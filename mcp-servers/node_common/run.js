/**
 * One-line bootstrap for persona MCP servers.
 *
 * Per-server entrypoints typically just do:
 *
 *   import { createPersonaMcpServer, runServer } from "@homepilot/mcp-node-common";
 *   import { tools } from "./tools.js";
 *   await runServer({ name: "mcp-creator-muse", version: "1.0.0", tools });
 *
 * Transport is selected via `--transport=` argv or `MCP_TRANSPORT` env.
 * stdio is the default so MCP Inspector works without any flags.
 */
import { createPersonaMcpServer } from "./createMcpServer.js";
import {
  resolveTransportFromEnv,
  startStdioTransport,
  startStreamableHttpTransport,
} from "./transports.js";

export async function runServer({ name, version, tools, port: defaultPort }) {
  const server = createPersonaMcpServer({ name, version, tools });
  const transport = resolveTransportFromEnv();

  if (transport === "stdio") {
    await startStdioTransport(server);
    process.stderr.write(
      `[${name}] connected via stdio (${tools.length} tool${tools.length === 1 ? "" : "s"})\n`
    );
    return;
  }

  const port = Number(process.env.MCP_PORT || defaultPort);
  const { address } = await startStreamableHttpTransport(server, { port });
  process.stderr.write(
    `[${name}] streamable-http listening on ${address} (${tools.length} tool${tools.length === 1 ? "" : "s"})\n`
  );
}
