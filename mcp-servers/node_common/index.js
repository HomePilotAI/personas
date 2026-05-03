/**
 * Shared MCP server framework used by every Node persona MCP server.
 *
 * Servers stay tiny and only declare:
 *   - canonical metadata ({ name, version })
 *   - their tool list (name, description, schema, handler)
 *
 * They get for free:
 *   - real MCP protocol via @modelcontextprotocol/sdk
 *   - stdio + Streamable HTTP transports
 *   - structured content-block responses
 *   - typed error envelopes
 *   - input validation through zod
 */
export { createPersonaMcpServer } from "./createMcpServer.js";
export { runServer } from "./run.js";
export { textResult, jsonResult, mixedResult } from "./responses.js";
export { ToolError, fromZodError, errorResult } from "./errors.js";
export { commonSchemas } from "./schemas.js";
export {
  startStdioTransport,
  startStreamableHttpTransport,
  resolveTransportFromEnv,
} from "./transports.js";
