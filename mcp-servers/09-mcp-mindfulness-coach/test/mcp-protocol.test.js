import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-mindfulness-coach",
  version: "1.0.0",
  tools,
  sampleArgs: {
    mindfulness_meditation: { minutes: 3, style: "body_scan", theme: "rest before bed" },
    mindfulness_grounding: { trigger: "anxious before a meeting", senses: 5 },
    mindfulness_focus: { duration_seconds: 90, technique: "box_breath" },
  },
  invalidArgs: {
    mindfulness_meditation: { minutes: 99 },
    mindfulness_grounding: { senses: 1 },
    mindfulness_focus: { duration_seconds: 5 },
  },
});
