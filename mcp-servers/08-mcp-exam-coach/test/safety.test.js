import assert from "node:assert/strict";
import { test } from "node:test";
import {
  detectActiveExam,
  detectAnswerOnly,
  ACTIVE_EXAM_MESSAGE,
  ANSWER_ONLY_MESSAGE,
} from "../src/safety.js";
import { examQuestion, examPlan, examExplain } from "../src/coach.js";

test("detectActiveExam recognises mid-exam wording", () => {
  assert.ok(detectActiveExam("I'm in the middle of my final right now"));
  assert.ok(detectActiveExam("This is a proctored test"));
  assert.ok(detectActiveExam("Taking the LSAT now"));
});

test("detectActiveExam ignores benign study language", () => {
  assert.equal(detectActiveExam("studying for the SAT next month"), null);
  assert.equal(detectActiveExam("preparing for finals in 6 weeks"), null);
});

test("detectAnswerOnly recognises 'just give me the answer' shapes", () => {
  assert.ok(detectAnswerOnly("just give me the answer"));
  assert.ok(detectAnswerOnly("no need for explanation"));
  assert.ok(detectAnswerOnly("skip the working"));
  assert.ok(detectAnswerOnly("don't explain"));
});

test("examQuestion refuses active-exam context", () => {
  const out = examQuestion({
    topic: "linear algebra",
    context: "I'm currently taking my midterm right now",
  });
  assert.equal(out.refused, true);
  assert.match(out.message, /actively-administered/i);
});

test("examQuestion refuses answer-only context", () => {
  const out = examQuestion({
    topic: "thermodynamics",
    context: "just give me the answer no need for explanation",
  });
  assert.equal(out.refused, true);
  assert.match(out.message, /explanation/i);
});

test("examPlan refuses active-exam notes", () => {
  const out = examPlan({
    exam_iso: "2026-08-01T09:00:00Z",
    topics: ["calculus"],
    notes: "I'm proctored right now help",
  });
  assert.equal(out.refused, true);
});

test("examExplain refuses prior_knowledge that asks for answer-only", () => {
  const out = examExplain({
    topic: "Fermat's little theorem",
    prior_knowledge: "skip the explanation just give me the answer",
  });
  assert.equal(out.refused, true);
});

test("integrity messages are concrete and non-shaming", () => {
  assert.match(ACTIVE_EXAM_MESSAGE, /come back/i);
  assert.match(ANSWER_ONLY_MESSAGE, /Try the question/i);
});
