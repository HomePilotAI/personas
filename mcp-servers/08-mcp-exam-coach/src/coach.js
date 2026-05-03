/**
 * Exam Coach business logic. Pure functions, no I/O.
 *
 * Three tools:
 *   - exam_question: practice questions for a topic at a difficulty band.
 *     Each item ships with difficulty, correct answer, and explanation.
 *   - exam_plan: spaced-repetition study plan from now → exam date.
 *   - exam_explain: layered explanations with a self-check question.
 *
 * Academic-integrity guard (see safety.js) refuses active-exam help and
 * answer-only requests.
 */

import { withIntegrityGuard } from "./safety.js";

const NON_OFFICIAL =
  "This is study guidance, not accredited instruction. For official policies, " +
  "deadlines and accommodations, consult your institution.";

const DIFFICULTY_BANDS = ["easy", "medium", "hard"];

const QUESTION_TYPES = ["mcq", "short_answer", "applied", "explain"];

const STEM_TEMPLATES = {
  easy: (topic) => `Define the core idea of ${topic} in one sentence.`,
  medium: (topic) => `Compare two common approaches inside ${topic}; when does each win?`,
  hard: (topic) => `Given a non-obvious edge case in ${topic}, predict the failure mode and justify it.`,
};

const TYPE_ADAPTERS = {
  mcq: (stem) => ({
    stem,
    options: ["A. ...", "B. ...", "C. ...", "D. ..."],
    correct_letter: "A",
    note: "Author should fill the option strings in the calling system.",
  }),
  short_answer: (stem) => ({
    stem,
    expected_length: "2-3 sentences",
  }),
  applied: (stem) => ({
    stem: `${stem} Show your work.`,
    rubric: ["Sets up the problem", "Names the relevant concept", "Lands the conclusion"],
  }),
  explain: (stem) => ({
    stem: `${stem} Explain like you'd teach it to a peer who just missed the lecture.`,
    rubric: ["Mentions the prerequisite", "Uses one concrete example", "Names a common pitfall"],
  }),
};

// ── Tool 1: exam_question ──────────────────────────────────────────────────

function buildQuestions({
  topic,
  difficulty = "medium",
  question_type = "mcq",
  count = 3,
  context, // checked by guard
}) {
  if (!topic || typeof topic !== "string") throw new Error("topic is required");
  const safeDifficulty = DIFFICULTY_BANDS.includes(difficulty) ? difficulty : "medium";
  const safeType = QUESTION_TYPES.includes(question_type) ? question_type : "mcq";
  const safeCount = Math.min(Math.max(Number.isInteger(count) ? count : 3, 1), 10);

  const stemFn = STEM_TEMPLATES[safeDifficulty];
  const adapt = TYPE_ADAPTERS[safeType];

  const questions = Array.from({ length: safeCount }, (_, i) => ({
    id: `q-${i + 1}`,
    difficulty: safeDifficulty,
    type: safeType,
    ...adapt(stemFn(topic)),
    correct_answer: `Refer to the explanation; the correct answer for variant ${i + 1} is the option/answer that aligns with: ${stemFn(topic)}`,
    explanation:
      `Because the question targets ${safeDifficulty}-band reasoning on "${topic}", ` +
      "the correct answer follows from the core principle, not from a memorized fact. " +
      "Re-derive it on a blank page before moving on.",
  }));

  return {
    topic,
    difficulty: safeDifficulty,
    question_type: safeType,
    count: safeCount,
    questions,
    notes: [
      "Every item carries a correct answer + explanation — no answer-only mode.",
      "If a learner misses 2+ in a row at this band, drop one band before re-trying.",
    ],
    disclaimer: NON_OFFICIAL,
  };
}

// ── Tool 2: exam_plan ──────────────────────────────────────────────────────

function dayDiff(a, b) {
  const ms = b.getTime() - a.getTime();
  return Math.round(ms / (24 * 60 * 60 * 1000));
}

function buildPlan({
  exam_iso,
  topics = [],
  hours_per_day = 1,
  start_iso,
  notes,  // checked by guard
}) {
  if (!exam_iso) throw new Error("exam_iso is required");
  const exam = new Date(exam_iso);
  if (Number.isNaN(exam.getTime())) throw new Error("exam_iso is not a valid ISO datetime");
  const start = start_iso ? new Date(start_iso) : new Date();
  if (Number.isNaN(start.getTime())) throw new Error("start_iso is not a valid ISO datetime");
  if (!Array.isArray(topics) || topics.length === 0) throw new Error("topics must be a non-empty array");
  if (topics.length > 30) throw new Error("topics capped at 30 per plan");

  const days = Math.max(1, dayDiff(start, exam));
  const dailyHours = Math.max(0.25, Math.min(Number(hours_per_day) || 1, 8));

  // Spaced-repetition windows — each topic gets initial, +1d, +3d, +7d, +14d.
  const windows = [0, 1, 3, 7, 14];

  const sessions = [];
  topics.forEach((rawTopic, i) => {
    const topic = String(rawTopic).slice(0, 120);
    const slotStart = Math.floor((i / topics.length) * (days * 0.6));
    for (const offset of windows) {
      const dayIndex = slotStart + offset;
      if (dayIndex < days) {
        const date = new Date(start.getTime() + dayIndex * 24 * 60 * 60 * 1000);
        sessions.push({
          day_index: dayIndex,
          date: date.toISOString().slice(0, 10),
          topic,
          mode: offset === 0 ? "first_pass" : "retrieval_practice",
          window_label: offset === 0 ? "initial" : `+${offset}d review`,
          minutes: Math.round(dailyHours * 60 / Math.max(1, topics.length / 2)),
        });
      }
    }
  });
  sessions.sort((a, b) => a.day_index - b.day_index);

  // Reserve final 2 days for full mock + light review.
  if (days >= 2) {
    const mockDate = new Date(start.getTime() + (days - 2) * 24 * 60 * 60 * 1000);
    const reviewDate = new Date(start.getTime() + (days - 1) * 24 * 60 * 60 * 1000);
    sessions.push({
      day_index: days - 2,
      date: mockDate.toISOString().slice(0, 10),
      topic: "full mock under exam conditions",
      mode: "mock_exam",
      window_label: "T-2 mock",
      minutes: Math.min(Math.round(dailyHours * 60 + 60), 240),
    });
    sessions.push({
      day_index: days - 1,
      date: reviewDate.toISOString().slice(0, 10),
      topic: "light review of weakest topics + sleep",
      mode: "deload",
      window_label: "T-1 deload",
      minutes: Math.round(dailyHours * 30),
    });
  }

  return {
    exam_iso: exam.toISOString(),
    start_iso: start.toISOString(),
    days_until_exam: days,
    hours_per_day: dailyHours,
    topics,
    method: "spaced repetition + retrieval practice (windows: 0, +1, +3, +7, +14 days)",
    sessions,
    rules_of_thumb: [
      "First pass earns the right to re-test, not the right to feel confident.",
      "Retrieval > re-reading. Close the book before answering.",
      "Sleep before the exam beats one more hour of cramming.",
    ],
    notes_acknowledged: notes ? String(notes).slice(0, 600) : null,
    disclaimer: NON_OFFICIAL,
  };
}

// ── Tool 3: exam_explain ───────────────────────────────────────────────────

const DEPTHS = ["intuition", "standard", "rigorous"];

function explain({
  topic,
  depth = "standard",
  prior_knowledge,  // checked by guard
}) {
  if (!topic || typeof topic !== "string") throw new Error("topic is required");
  const safeDepth = DEPTHS.includes(depth) ? depth : "standard";

  const intuition = `In one breath: ${topic} is the question of how a system gets from inputs to outputs without breaking the rules it sets for itself.`;
  const standard = `${intuition} The standard treatment introduces the core formalism, walks through one canonical example, and names the most common failure mode.`;
  const rigorous = `${standard} The rigorous version restates the assumptions, proves the lemma the result rests on, and shows where the proof breaks under relaxed conditions.`;

  const body =
    safeDepth === "intuition" ? intuition : safeDepth === "rigorous" ? rigorous : standard;

  return {
    topic,
    depth: safeDepth,
    explanation: body,
    worked_example: `Pick the smallest concrete instance of ${topic}; solve it twice — once with the formal definition, once from intuition. The gap between the two is your real understanding.`,
    self_check: {
      question: `In your own words, when does ${topic} stop applying?`,
      hint: "Look for an assumption you've been quietly relying on.",
    },
    prior_knowledge_acknowledged: prior_knowledge ? String(prior_knowledge).slice(0, 400) : null,
    disclaimer: NON_OFFICIAL,
  };
}

// Public, integrity-guarded entry points.
export const examQuestion = withIntegrityGuard(["topic", "context"], (args) => buildQuestions(args));
export const examPlan = withIntegrityGuard(["notes"], (args) => buildPlan(args));
export const examExplain = withIntegrityGuard(["topic", "prior_knowledge"], (args) => explain(args));

export const _internals = { DIFFICULTY_BANDS, QUESTION_TYPES, DEPTHS };
