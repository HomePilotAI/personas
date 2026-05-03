/**
 * Academic-integrity guard for the Exam Coach persona.
 *
 * Refuses two patterns:
 *
 *   1. Active-exam assistance — language indicating the user is currently
 *      taking a real assessment ("I'm taking the SAT right now",
 *      "during the exam", "live test session"…). Practice and review
 *      flow through.
 *   2. Answer-only mode requests — "just give me the answer", "no
 *      explanation needed", "skip the working". Coach always returns an
 *      explanation alongside any answer.
 */

const ACTIVE_EXAM_PATTERNS = [
  /\b(during|in the middle of|currently taking|right now (in|during)|in my|on my)\b.*\b(exam|test|quiz|midterm|final|assessment)\b/i,
  /\bproctored\b/i,
  /\b(live|active) (exam|test|assessment)\b/i,
  /\btaking the (sat|gre|gmat|mcat|lsat|bar|nclex|toefl|ielts)\b.*\b(now|today)\b/i,
  /\b(exam|test|quiz) (is|started|begins) (now|in \d+ minute)/i,
];

const ANSWER_ONLY_PATTERNS = [
  /\b(just|only) (give|tell) me the answer\b/i,
  /\bno (need for|need to|need an?) explanation\b/i,
  /\bskip the (working|explanation|reasoning|steps)\b/i,
  /\banswer[- ]only\b/i,
  /\bdon'?t explain\b/i,
];

export const ACTIVE_EXAM_MESSAGE =
  "Exam Coach won't help with an actively-administered exam — that's an academic-integrity " +
  "line we don't cross. After the assessment is over, come back with the topic and the " +
  "questions you struggled with and we'll build a real review plan.";

export const ANSWER_ONLY_MESSAGE =
  "Every answer Exam Coach gives ships with an explanation — that's how the practice " +
  "actually moves the needle. Try the question yourself, then ask for the worked solution.";

export function detectActiveExam(text) {
  if (!text || typeof text !== "string") return null;
  for (const p of ACTIVE_EXAM_PATTERNS) {
    if (p.test(text)) return { reason: "active_exam_assistance_refused", matched: p.source };
  }
  return null;
}

export function detectAnswerOnly(text) {
  if (!text || typeof text !== "string") return null;
  for (const p of ANSWER_ONLY_PATTERNS) {
    if (p.test(text)) return { reason: "answer_only_mode_refused", matched: p.source };
  }
  return null;
}

export function withIntegrityGuard(fields, generator) {
  return (args = {}) => {
    for (const f of fields) {
      const v = args[f];
      const ae = detectActiveExam(v);
      if (ae) {
        return {
          refused: true,
          reason: ae.reason,
          matched_pattern: ae.matched,
          message: ACTIVE_EXAM_MESSAGE,
        };
      }
      const ao = detectAnswerOnly(v);
      if (ao) {
        return {
          refused: true,
          reason: ao.reason,
          matched_pattern: ao.matched,
          message: ANSWER_ONLY_MESSAGE,
        };
      }
    }
    return generator(args);
  };
}
