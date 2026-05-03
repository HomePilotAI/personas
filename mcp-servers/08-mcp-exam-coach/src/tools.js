import { z } from "zod";
import { jsonResult } from "@homepilot/mcp-node-common/responses";
import { examQuestion, examPlan, examExplain } from "./coach.js";

export const tools = [
  {
    name: "exam_question",
    description:
      "Generate practice questions for a topic at a target difficulty. Each question ships with the correct answer and an explanation — never answer-only.",
    schema: {
      topic: z.string().min(2).max(200).describe("Subject / topic to drill."),
      difficulty: z
        .enum(["easy", "medium", "hard"])
        .optional()
        .describe("Target difficulty band (default 'medium')."),
      question_type: z
        .enum(["mcq", "short_answer", "applied", "explain"])
        .optional()
        .describe("Question shape (default 'mcq')."),
      count: z.number().int().min(1).max(10).optional().describe("Number of questions (1-10, default 3)."),
      context: z
        .string()
        .max(800)
        .optional()
        .describe(
          "Optional learner context. Active-exam language or answer-only requests trigger a refusal envelope."
        ),
    },
    handler: (args) => jsonResult(examQuestion(args)),
  },
  {
    name: "exam_plan",
    description:
      "Build a spaced-repetition / retrieval-practice study plan from a target date and topic list.",
    schema: {
      exam_iso: z.string().describe("Exam datetime as ISO 8601."),
      topics: z
        .array(z.string().min(2).max(120))
        .min(1)
        .max(30)
        .describe("Up to 30 topics to cover."),
      hours_per_day: z.number().min(0.25).max(8).optional().describe("Daily study budget (default 1 hour)."),
      start_iso: z
        .string()
        .optional()
        .describe("Optional plan start; defaults to 'now'."),
      notes: z
        .string()
        .max(600)
        .optional()
        .describe(
          "Optional learner context. Active-exam language or answer-only requests trigger a refusal envelope."
        ),
    },
    handler: (args) => jsonResult(examPlan(args)),
  },
  {
    name: "exam_explain",
    description:
      "Explain a concept at a requested depth (intuition / standard / rigorous) with worked examples and a self-check question.",
    schema: {
      topic: z.string().min(2).max(200),
      depth: z.enum(["intuition", "standard", "rigorous"]).optional(),
      prior_knowledge: z
        .string()
        .max(400)
        .optional()
        .describe("Optional prior-knowledge context. Active-exam / answer-only language triggers a refusal envelope."),
    },
    handler: (args) => jsonResult(examExplain(args)),
  },
];
