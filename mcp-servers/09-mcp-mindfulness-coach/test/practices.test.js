import assert from "node:assert/strict";
import { test } from "node:test";
import { meditation, grounding, focus } from "../src/practices.js";

test("meditation returns a script with paced (pause) cues", () => {
  const out = meditation({ minutes: 3, style: "box_breath" });
  assert.equal(out.minutes, 3);
  assert.equal(out.style, "box_breath");
  assert.ok(Array.isArray(out.script));
  assert.ok(out.script.some((line) => /\(pause/.test(line)));
  assert.match(out.disclaimer, /non-clinical/i);
});

test("meditation clamps minutes 1-20", () => {
  assert.equal(meditation({ minutes: 99 }).minutes, 20);
  assert.equal(meditation({ minutes: -3 }).minutes, 1);
});

test("grounding returns 5-4-3-2-1 steps by default", () => {
  const out = grounding({ trigger: "tense before a meeting" });
  assert.equal(out.steps.length, 5);
  assert.deepEqual(
    out.steps.map((s) => s.count),
    [5, 4, 3, 2, 1]
  );
});

test("grounding shortened to 3 senses keeps the closing 3-2-1 steps", () => {
  // Semantic: dropping senses removes the *opening* steps so the practice
  // still ends on the calmest beat (1 thing you can taste / imagine).
  const out = grounding({ trigger: "warming up", senses: 3 });
  assert.equal(out.steps.length, 3);
  assert.deepEqual(
    out.steps.map((s) => s.count),
    [3, 2, 1]
  );
});

test("focus produces breath cycles for the requested technique", () => {
  const box = focus({ duration_seconds: 90, technique: "box_breath" });
  assert.equal(box.technique, "box_breath");
  assert.ok(box.cycles >= 1);
  assert.ok(box.steps.every((s) => /four/i.test(s)));

  const fourSevenEight = focus({ duration_seconds: 60, technique: "478" });
  assert.ok(fourSevenEight.steps.every((s) => /seven|eight/i.test(s)));
});
