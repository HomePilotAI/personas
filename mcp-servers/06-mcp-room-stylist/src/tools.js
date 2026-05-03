import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { proposeLayout, buildPalette, buildShoppingList } from "./stylist.js";

const ROOM_ENUM = z.enum([
  "living",
  "bedroom",
  "kitchen",
  "office",
  "diningroom",
  "studio",
]);

const PALETTE_ENUM = z.enum([
  "warm_minimal",
  "cool_modern",
  "earth_organic",
  "bright_playful",
]);

export const tools = [
  {
    name: "room_layout",
    description:
      "Propose 2-3 room layout options for a footprint and primary use, with zoning and circulation notes.",
    schema: {
      room: ROOM_ENUM.describe("Room type."),
      length_m: z.number().positive().max(40).optional().describe("Room length in metres."),
      width_m: z.number().positive().max(40).optional().describe("Room width in metres."),
      primary_use: z
        .string()
        .max(120)
        .optional()
        .describe("How the room is mainly used (e.g. 'WFH + occasional yoga')."),
      options: z
        .number()
        .int()
        .min(1)
        .max(3)
        .optional()
        .describe("Number of layout options (default 3, max 3)."),
    },
    handler: (args) => jsonResult(proposeLayout(args)),
  },
  {
    name: "room_palette",
    description:
      "Generate a 60/30/10 color palette and material story for the room with hex anchors.",
    schema: {
      room: ROOM_ENUM,
      mood: PALETTE_ENUM
        .optional()
        .describe("Palette register (default 'warm_minimal')."),
    },
    handler: (args) => jsonResult(buildPalette(args)),
  },
  {
    name: "room_shopping_list",
    description:
      "Curate a shoppable list across 3 price tiers (good / better / heirloom), grouped by zone.",
    schema: {
      room: ROOM_ENUM,
      palette: PALETTE_ENUM
        .optional()
        .describe("Anchor palette name (must match a room_palette mood)."),
      budget: z
        .enum(["tight", "balanced", "generous"])
        .optional()
        .describe("Overall budget posture (default 'balanced')."),
    },
    handler: (args) => jsonResult(buildShoppingList(args)),
  },
];
