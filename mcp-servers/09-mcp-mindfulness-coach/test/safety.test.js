import assert from "node:assert/strict";
import { test } from "node:test";
import { detectCrisis, ESCALATION_MESSAGE } from "../src/safety.js";
import { meditation, grounding, focus } from "../src/practices.js";

test("detectCrisis returns null for benign text", () => {
  assert.equal(detectCrisis("I want to relax before bed"), null);
  assert.equal(detectCrisis(""), null);
  assert.equal(detectCrisis(undefined), null);
});

test("detectCrisis flags suicidal language", () => {
  for (const text of [
    "I'm having suicidal thoughts",
    "I want to kill myself",
    "I feel like ending it",
  ]) {
    const hit = detectCrisis(text);
    assert.ok(hit, `expected crisis hit for: ${text}`);
    assert.equal(hit.escalated, true);
    assert.match(hit.message, /licensed|crisis line/i);
  }
});

test("detectCrisis flags self-harm and panic-attack language", () => {
  assert.ok(detectCrisis("I've been cutting myself"));
  assert.ok(detectCrisis("I'm having a panic attack right now"));
  assert.ok(detectCrisis("I keep getting flashbacks from the accident"));
});

test("meditation short-circuits to escalation when theme contains crisis language", () => {
  const out = meditation({ theme: "I want to end my life", minutes: 5 });
  assert.equal(out.escalated, true);
  assert.equal(out.reason, "crisis_signal_detected");
  assert.ok(out.resources.length >= 3);
  assert.equal(out.script, undefined, "no script when crisis detected");
});

test("grounding short-circuits to escalation when trigger contains crisis language", () => {
  const out = grounding({ trigger: "I'm about to overdose" });
  assert.equal(out.escalated, true);
  assert.match(out.message, /988|Samaritans/);
});

test("focus passes through normally for benign before_task", () => {
  const out = focus({ before_task: "write the next paragraph", duration_seconds: 60 });
  assert.notEqual(out.escalated, true);
  assert.ok(out.steps.length >= 1);
  assert.match(out.next_step, /write the next paragraph/);
});

test("escalation message names a crisis resource", () => {
  assert.match(ESCALATION_MESSAGE, /988|Samaritans|crisis/i);
});
