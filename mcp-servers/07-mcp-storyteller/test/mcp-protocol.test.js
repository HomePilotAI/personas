import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-storyteller",
  version: "1.0.0",
  tools,
  sampleArgs: {
    story_scene: {
      mode: "scene",
      persona: "Lina",
      scene_number: 2,
      total_scenes: 4,
      vibe: "cinematic",
    },
    story_choice: {
      scene_summary: "Two characters meet on a rooftop after the storm.",
      persona: "Lina",
      count: 2,
    },
    story_ending: {
      arc: "growth",
      persona: "Lina",
      branch_summary: "The user chose honesty across both decisions.",
    },
  },
  invalidArgs: {
    story_scene: { scene_number: 99, total_scenes: 99 },
    story_choice: { count: 1 },
    story_ending: { arc: "tragic" },
  },
});
