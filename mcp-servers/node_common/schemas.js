/**
 * Reusable zod schema fragments shared across persona MCP servers.
 *
 * Tool handlers should compose these instead of redefining the same shapes.
 * Keep this file small — when in doubt, prefer a per-server schema over a
 * generic one here.
 */
import { z } from "zod";

export const commonSchemas = {
  /** Free-text user input with a sane upper bound. */
  topic: z
    .string()
    .min(1, "topic is required")
    .max(2000, "topic must be ≤ 2000 chars"),

  /** A short tone tag like "playful", "formal", "encouraging". */
  tone: z.string().min(1).max(40).optional(),

  /** An integer count with bounds; usable for max_results, durations, etc. */
  count: (min = 1, max = 50) => z.number().int().min(min).max(max),

  /** ISO 8601 datetime string. */
  isoDatetime: z
    .string()
    .regex(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/,
      "must be an ISO 8601 datetime"
    ),

  /** A safe URL (http or https). */
  httpUrl: z.string().url().refine(
    (u) => /^https?:\/\//i.test(u),
    "must be an http(s) URL"
  ),
};
