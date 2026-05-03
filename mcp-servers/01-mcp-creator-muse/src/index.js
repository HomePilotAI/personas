#!/usr/bin/env node
/**
 * Creator Muse MCP server entrypoint.
 *
 * Run with stdio for MCP Inspector:
 *
 *   node src/index.js
 *
 * Run with Streamable HTTP for Context Forge / Docker:
 *
 *   MCP_TRANSPORT=streamable-http MCP_PORT=9101 node src/index.js
 */
import { runServer } from "@homepilot/mcp-node-common/run";
import { tools } from "./tools.js";

await runServer({
  name: "mcp-creator-muse",
  version: "1.0.0",
  tools,
  port: 9101,
});
