import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { buildOutfit, buildVariants } from "./style.js";

export const tools = [
  {
    name: "style_muse_outfit",
    description:
      "Build a head-to-toe outfit for a given occasion / vibe with palette suggestions and styling notes.",
    schema: {
      occasion: z
        .enum(["business", "casual", "date", "party", "outdoor", "travel"])
        .describe("Where the outfit needs to land."),
      vibe: z
        .enum(["warm", "cool", "bold", "pastel", "earth"])
        .optional()
        .describe("Palette register; defaults to 'earth'."),
      weather: z
        .string()
        .max(60)
        .optional()
        .describe("Optional weather context, e.g. 'cold rain', 'hot and dry'."),
      anchor_piece: z
        .string()
        .max(120)
        .optional()
        .describe("A specific item the user wants to build around."),
    },
    handler: (args) => jsonResult(buildOutfit(args)),
  },
  {
    name: "style_muse_variant",
    description:
      "Generate before/after styling variants of a base look — switch one element at a time so the user can see what changed.",
    schema: {
      base_look: z
        .string()
        .min(3)
        .max(280)
        .describe("Description of the base outfit / look to riff on."),
      count: z
        .number()
        .int()
        .min(1)
        .max(5)
        .optional()
        .describe("Number of variants (default 3, max 5)."),
    },
    handler: (args) => jsonResult(buildVariants(args)),
  },
];
