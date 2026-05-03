import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { meditation, grounding, focus } from "./practices.js";

export const tools = [
  {
    name: "mindfulness_meditation",
    description:
      "Generate a guided meditation script of N minutes with paced breath cues. Always non-clinical; defers to a licensed professional for persistent distress.",
    schema: {
      minutes: z
        .number()
        .int()
        .min(1)
        .max(20)
        .optional()
        .describe("Length of the meditation in minutes (1-20, default 5)."),
      theme: z
        .string()
        .max(120)
        .optional()
        .describe(
          "Free-text intent for the session. Crisis-language input triggers escalation."
        ),
      style: z
        .enum(["body_scan", "box_breath", "open_awareness"])
        .optional()
        .describe("Practice style; default 'body_scan'."),
    },
    handler: (args) => jsonResult(meditation(args)),
  },
  {
    name: "mindfulness_grounding",
    description:
      "Lead a 5-4-3-2-1 sensory grounding exercise. If the user mentions crisis-level distress, the response replaces the script with an escalation message.",
    schema: {
      trigger: z
        .string()
        .max(120)
        .optional()
        .describe(
          "What surfaced — e.g. 'anxious', 'overwhelmed', 'spiralling'. Crisis-language input triggers escalation."
        ),
      senses: z
        .number()
        .int()
        .min(3)
        .max(5)
        .optional()
        .describe("How many sensory steps to include (3-5, default 5)."),
    },
    handler: (args) => jsonResult(grounding(args)),
  },
  {
    name: "mindfulness_focus",
    description:
      "Run a short focus / breath-led micro-session (box breath or 4-7-8) to reset attention before a task.",
    schema: {
      duration_seconds: z
        .number()
        .int()
        .min(30)
        .max(600)
        .optional()
        .describe("Total duration in seconds (30-600, default 90)."),
      technique: z
        .enum(["box_breath", "478", "long_exhale"])
        .optional()
        .describe("Breath technique; default 'box_breath'."),
      before_task: z
        .string()
        .max(200)
        .optional()
        .describe("Optional reminder of the next concrete task to return to."),
    },
    handler: (args) => jsonResult(focus(args)),
  },
];
