import assert from "node:assert/strict";
import { test } from "node:test";
import { examQuestion, examPlan, examExplain } from "../src/coach.js";

test("examQuestion produces N items with answer + explanation", () => {
  const out = examQuestion({ topic: "Bayes' theorem", count: 4, difficulty: "medium" });
  assert.equal(out.questions.length, 4);
  for (const q of out.questions) {
    assert.equal(q.difficulty, "medium");
    assert.ok(q.correct_answer);
    assert.ok(q.explanation);
  }
});

test("examQuestion clamps count to 1-10 and validates topic", () => {
  assert.equal(examQuestion({ topic: "x", count: 999 }).questions.length, 10);
  assert.equal(examQuestion({ topic: "x", count: 0 }).questions.length, 1);
  assert.throws(() => examQuestion({}), /topic/);
});

test("examPlan produces sessions across the time window with mock + deload", () => {
  const out = examPlan({
    exam_iso: "2026-08-15T09:00:00Z",
    topics: ["limits", "derivatives", "integrals"],
    start_iso: "2026-07-15T00:00:00Z",
    hours_per_day: 1.5,
  });
  assert.equal(out.days_until_exam, 31);
  assert.ok(out.sessions.length > 6);
  assert.ok(out.sessions.some((s) => s.mode === "mock_exam"));
  assert.ok(out.sessions.some((s) => s.mode === "deload"));
  assert.ok(out.sessions.some((s) => s.mode === "retrieval_practice"));
});

test("examPlan rejects invalid inputs", () => {
  assert.throws(() => examPlan({}), /exam_iso/);
  assert.throws(
    () => examPlan({ exam_iso: "tomorrow", topics: ["x"] }),
    /ISO/
  );
  assert.throws(() => examPlan({ exam_iso: "2026-08-15T09:00:00Z", topics: [] }), /topics/);
});

test("examExplain produces three depths with self-check", () => {
  for (const depth of ["intuition", "standard", "rigorous"]) {
    const out = examExplain({ topic: "compactness", depth });
    assert.equal(out.depth, depth);
    assert.ok(out.explanation.length > 30);
    assert.ok(out.worked_example);
    assert.ok(out.self_check.question);
  }
});

test("examExplain falls back to 'standard' for unknown depth", () => {
  const out = examExplain({ topic: "x", depth: "ultra" });
  assert.equal(out.depth, "standard");
});
