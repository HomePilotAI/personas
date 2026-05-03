import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { workoutPlan, recovery, trackStreak } from "./training.js";

export const tools = [
  {
    name: "trainer_workout_plan",
    description:
      "Build a structured workout plan with warm-up, main work (RPE/RIR cues), regression and progression. Honors reported injuries; surfaces medical-escalation flag for red-flag symptoms.",
    schema: {
      goal: z
        .enum(["strength", "hypertrophy", "endurance", "general_health"])
        .optional()
        .describe("Primary training goal (default 'general_health')."),
      experience: z
        .enum(["beginner", "intermediate", "advanced"])
        .optional()
        .describe("Lifter experience level (default 'beginner')."),
      days_per_week: z
        .number()
        .int()
        .min(1)
        .max(6)
        .optional()
        .describe("Training days per week (1-6, default 3)."),
      split: z
        .enum(["full_body", "upper_lower", "push_pull_legs"])
        .optional()
        .describe("Programming split (default 'full_body')."),
      current_injuries: z
        .array(z.string().min(2).max(80))
        .max(10)
        .optional()
        .describe(
          "Free-text injury list (e.g. ['low back', 'right knee']). Movements that aggravate them get a regression and a load cut."
        ),
      notes: z
        .string()
        .max(1000)
        .optional()
        .describe(
          "Optional free-text context. Crisis / red-flag medical language triggers an escalation envelope."
        ),
    },
    handler: (args) => jsonResult(workoutPlan(args)),
  },
  {
    name: "trainer_recovery_check",
    description:
      "Score readiness for the next session from sleep, soreness, RPE, and HRV trend; output is a recommendation, not a clinical assessment.",
    schema: {
      sleep_hours: z.number().min(0).max(14).optional(),
      soreness_0_10: z.number().min(0).max(10).optional(),
      perceived_exertion_0_10: z.number().min(0).max(10).optional(),
      hrv_trend: z.enum(["up", "steady", "down", "unknown"]).optional(),
      notes: z
        .string()
        .max(600)
        .optional()
        .describe(
          "Optional free-text context. Crisis / red-flag medical language triggers an escalation envelope."
        ),
    },
    handler: (args) => jsonResult(recovery(args)),
  },
  {
    name: "trainer_streak",
    description:
      "Track and reinforce a training streak with deload guidance every 4-6 weeks; never punishes a planned rest day.",
    schema: {
      sessions_completed_this_week: z.number().int().min(0).max(14).optional(),
      weeks_active: z.number().int().min(0).max(520).optional(),
      planned_rest_days: z.number().int().min(0).max(7).optional(),
    },
    handler: (args) => jsonResult(trackStreak(args)),
  },
];
