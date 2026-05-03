/**
 * Tool definitions for the Creator Muse MCP server.
 *
 * Keeping each tool's name string identical to the server.json declaration
 * is enforced by scripts/validate_mcp_servers.py — never rename in only one
 * place.
 */
import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { inspire } from "./inspire.js";

export const tools = [
  {
    name: "creator_muse_inspire",
    description:
      "Generate scroll-stopping content ideas (hook + scene + CTA) with caption + 5 hashtags for short-form video / carousels.",
    schema: {
      topic: z
        .string()
        .min(1, "topic is required")
        .max(280, "topic must be ≤ 280 chars"),
      medium: z
        .string()
        .max(60)
        .optional()
        .describe("e.g. 'short-form video', 'carousel', 'newsletter'"),
      tone: z
        .string()
        .max(40)
        .optional()
        .describe("e.g. 'playful', 'educational', 'punchy'"),
      platform: z
        .enum([
          "reels",
          "tiktok",
          "shorts",
          "youtube shorts",
          "carousel",
          "carousels",
        ])
        .optional()
        .describe("Platform to bias hashtag suggestions."),
      count: z
        .number()
        .int()
        .min(1)
        .max(5)
        .optional()
        .describe("Number of ideas to generate (default 3, max 5)."),
    },
    handler: (args) => jsonResult(inspire(args)),
  },
];
