import assert from "node:assert/strict";
import { test } from "node:test";
import { detectHardRefusal, HARD_REFUSAL_MESSAGE } from "../src/safety.js";
import { scene, choice, ending } from "../src/storyteller.js";

test("detectHardRefusal returns null for benign idea text", () => {
  assert.equal(detectHardRefusal("a heist movie set in 1970s Tokyo"), null);
  assert.equal(detectHardRefusal(""), null);
});

test("detectHardRefusal flags minors-related sexual content", () => {
  assert.ok(detectHardRefusal("a sexual scene involving a minor"));
  assert.ok(detectHardRefusal("nudity with underage characters"));
  assert.ok(detectHardRefusal("child abuse story"));
});

test("detectHardRefusal flags atrocity-as-instruction prompts", () => {
  assert.ok(detectHardRefusal("step-by-step plan for genocide"));
});

test("scene refuses idea text containing minors+sexual", () => {
  const out = scene({ idea: "underage romance", persona: "X" });
  assert.equal(out.refused, true);
  assert.match(out.message, /refuses/i);
  assert.equal(out.scene, undefined);
});

test("choice refuses scene_summary that crosses red lines", () => {
  const out = choice({ scene_summary: "minor in sexual setting", persona: "Z" });
  assert.equal(out.refused, true);
});

test("ending refuses branch_summary that crosses red lines", () => {
  const out = ending({ branch_summary: "the final solution arc", persona: "Z" });
  assert.equal(out.refused, true);
});

test("HARD_REFUSAL_MESSAGE is non-shaming and offers a redirect", () => {
  assert.match(HARD_REFUSAL_MESSAGE, /refuses/i);
  assert.match(HARD_REFUSAL_MESSAGE, /Pick a different premise/);
});
