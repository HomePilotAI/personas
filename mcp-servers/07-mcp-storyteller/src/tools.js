import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { scene, choice, ending } from "./storyteller.js";

const VIBE_ENUM = z.enum([
  "teasing",
  "playful",
  "romantic",
  "mysterious",
  "cinematic",
  "comedic",
  "dramatic",
  "cozy",
  "high-energy",
]);

export const tools = [
  {
    name: "story_scene",
    description:
      "Generate the next branching scene (SETTING · MOOD · BEATS · CHOICE · NEXT-SCENE HOOK), under ~200 words.",
    schema: {
      mode: z
        .enum(["scene", "project"])
        .optional()
        .describe(
          "'scene' (default) returns one scene; 'project' returns the legacy full branching project (preserved for callers that used build_branching_video_project)."
        ),
      persona: z.string().min(1).max(60).optional(),
      vibe: VIBE_ENUM.optional(),
      scene_number: z.number().int().min(1).max(6).optional(),
      total_scenes: z.number().int().min(3).max(6).optional(),
      scene_count: z.number().int().min(3).max(6).optional().describe("Project mode only."),
      companion: z
        .string()
        .max(80)
        .optional()
        .describe("Optional second character; goes through the content-safety guard."),
      idea: z
        .string()
        .max(280)
        .optional()
        .describe("Theme / premise; goes through the content-safety guard."),
      render_mode: z.enum(["video", "image"]).optional(),
      rating: z.enum(["sfw", "nsfw"]).optional().describe("Default 'sfw'. Hard refusals apply at any rating."),
    },
    handler: (args) => jsonResult(scene(args)),
  },
  {
    name: "story_choice",
    description:
      "Draft 2-3 player choices for the current scene with outcome notes; choices reveal personality, not just information.",
    schema: {
      scene_summary: z
        .string()
        .max(600)
        .optional()
        .describe("One-paragraph summary of the scene the choices follow."),
      persona: z.string().min(1).max(60).optional(),
      count: z.number().int().min(2).max(3).optional(),
      vibe: VIBE_ENUM.optional(),
    },
    handler: (args) => jsonResult(choice(args)),
  },
  {
    name: "story_ending",
    description:
      "Resolve a branch into one of three endings (Growth / Balanced / Chaos) with a closing beat.",
    schema: {
      arc: z.enum(["growth", "balanced", "chaos"]).optional(),
      persona: z.string().min(1).max(60).optional(),
      branch_summary: z
        .string()
        .max(800)
        .optional()
        .describe("Summary of the branch leading to the ending."),
      vibe: VIBE_ENUM.optional(),
    },
    handler: (args) => jsonResult(ending(args)),
  },
];
