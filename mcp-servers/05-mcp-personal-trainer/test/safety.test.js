import assert from "node:assert/strict";
import { test } from "node:test";
import { detectRedFlag, ESCALATION_MESSAGE } from "../src/safety.js";
import { workoutPlan, recovery } from "../src/training.js";

test("detectRedFlag returns null for benign text", () => {
  assert.equal(detectRedFlag("I want to add deadlifts"), null);
  assert.equal(detectRedFlag(""), null);
  assert.equal(detectRedFlag(undefined), null);
});

test("detectRedFlag flags chest pain and shortness of breath", () => {
  assert.ok(detectRedFlag("I had chest pain during squats"));
  assert.ok(detectRedFlag("shortness of breath at the top of the stairs"));
});

test("detectRedFlag flags neuro-style symptoms and head injury", () => {
  assert.ok(detectRedFlag("I felt dizzy and almost blacked out"));
  assert.ok(detectRedFlag("Possible concussion last weekend"));
  assert.ok(detectRedFlag("numbness down my left arm"));
});

test("workoutPlan short-circuits on red-flag notes", () => {
  const out = workoutPlan({ goal: "strength", days_per_week: 3, notes: "I had chest pain yesterday" });
  assert.equal(out.escalated, true);
  assert.equal(out.reason, "medical_red_flag_detected");
  assert.equal(out.sessions, undefined);
  assert.match(out.message, /clinician|medical/i);
});

test("recovery short-circuits on red-flag notes", () => {
  const out = recovery({ sleep_hours: 4, notes: "lots of dizziness lately" });
  assert.equal(out.escalated, true);
});

test("escalation message names emergency action", () => {
  assert.match(ESCALATION_MESSAGE, /emergency|physician|clinician/i);
});
