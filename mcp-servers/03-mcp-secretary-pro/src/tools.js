import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { proposeSlots, draftReminder, triageInbox } from "./secretary.js";

export const tools = [
  {
    name: "secretary_schedule",
    description:
      "Propose 3 time-zone-aware meeting slots plus a fallback. Drafts only — never books.",
    schema: {
      duration_minutes: z
        .number()
        .int()
        .min(15)
        .max(240)
        .optional()
        .describe("Meeting length in minutes (15-240, default 30)."),
      attendee_timezones: z
        .array(z.string().min(2).max(10))
        .min(1)
        .max(10)
        .optional()
        .describe(
          "Short timezone names (e.g. ['UTC', 'CET', 'PST']). Up to 10."
        ),
      earliest_iso: z
        .string()
        .optional()
        .describe(
          "Earliest acceptable start as an ISO datetime; defaults to 'now'."
        ),
      search_days: z
        .number()
        .int()
        .min(1)
        .max(21)
        .optional()
        .describe("How many days ahead to search (default 5)."),
    },
    handler: (args) => jsonResult(proposeSlots(args)),
  },
  {
    name: "secretary_remind",
    description:
      "Create time-aware reminder drafts. Output is a structured reminder envelope; the caller decides whether to commit it to a real reminder system.",
    schema: {
      title: z.string().min(1).max(200).describe("Short reminder title."),
      due_iso: z.string().describe("Due time as an ISO datetime."),
      channel: z
        .enum(["calendar", "tasks", "notification", "email"])
        .optional()
        .describe("Suggested channel for the reminder (default 'calendar')."),
      urgency: z
        .enum(["now", "today", "this_week", "defer"])
        .optional()
        .describe("Urgency bucket (default 'today')."),
      context: z
        .string()
        .max(1000)
        .optional()
        .describe("Optional context blob — what's the reminder about."),
    },
    handler: (args) => jsonResult(draftReminder(args)),
  },
  {
    name: "secretary_triage",
    description:
      "Sort inbox items into Now / Today / This Week / Defer buckets with a one-line rationale per item.",
    schema: {
      items: z
        .array(
          z.object({
            id: z.union([z.string(), z.number()]).optional(),
            from: z.string().max(200).optional(),
            subject: z.string().max(280).optional(),
            snippet: z.string().max(600).optional(),
          })
        )
        .max(100)
        .describe("Inbox items to classify (max 100 per call)."),
    },
    handler: (args) => jsonResult(triageInbox(args)),
  },
];
