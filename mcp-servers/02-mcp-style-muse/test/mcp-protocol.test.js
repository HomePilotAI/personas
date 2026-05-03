import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-style-muse",
  version: "1.0.0",
  tools,
  sampleArgs: {
    style_muse_outfit: { occasion: "date", vibe: "bold", weather: "warm" },
    style_muse_variant: { base_look: "olive jacket + cream tee + dark jeans", count: 2 },
  },
  invalidArgs: {
    style_muse_outfit: { occasion: "not-a-real-occasion" },
    style_muse_variant: { base_look: "ab" },
  },
});
