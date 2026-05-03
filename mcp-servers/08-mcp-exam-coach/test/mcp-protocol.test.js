import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-exam-coach",
  version: "1.0.0",
  tools,
  sampleArgs: {
    exam_question: { topic: "Bayes' theorem", difficulty: "medium", count: 2 },
    exam_plan: {
      exam_iso: "2026-08-15T09:00:00Z",
      topics: ["limits", "derivatives", "integrals"],
      hours_per_day: 1.5,
    },
    exam_explain: { topic: "linear independence", depth: "intuition" },
  },
  invalidArgs: {
    exam_question: { topic: "x", count: 99 },
    exam_plan: { topics: [] }, // missing exam_iso, empty topics
    exam_explain: { topic: "x", depth: "ultra" }, // depth not in enum
  },
});
