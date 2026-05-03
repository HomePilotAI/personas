/**
 * MCP protocol smoke tests for creator-muse — run via the shared harness so
 * every server gets the same protocol coverage with a 5-line config.
 */
import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-creator-muse",
  version: "1.0.0",
  tools,
  sampleArgs: {
    creator_muse_inspire: { topic: "AI productivity", platform: "reels", count: 2 },
  },
  invalidArgs: {
    creator_muse_inspire: { topic: "" }, // empty topic violates min(1)
  },
});
