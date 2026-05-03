import assert from "node:assert/strict";
import { test } from "node:test";
import { scene, choice, ending } from "../src/storyteller.js";
import { normalizeVibe, buildSessionVibe, _internals } from "../src/storyteller.js";

test("scene mode returns a single scene with beats and choices", () => {
  const out = scene({ mode: "scene", persona: "Lina", scene_number: 2, total_scenes: 4 });
  assert.equal(out.mode, "scene");
  assert.equal(out.scene.number, 2);
  assert.equal(out.scene.total, 4);
  assert.ok(Array.isArray(out.scene.beats));
  assert.equal(out.scene.beats.length, 3);
  assert.ok(out.scene.choices.length >= 1);
});

test("scene resolution scene has no choices but a next-scene hook", () => {
  const out = scene({ mode: "scene", scene_number: 4, total_scenes: 4 });
  assert.equal(out.scene.focus, "resolution");
  assert.equal(out.scene.choices.length, 0);
  assert.match(out.scene.next_scene_hook, /story_ending/i);
});

test("scene project mode preserves the legacy branching shape", () => {
  const out = scene({
    mode: "project",
    persona: "Lina",
    companion: "Theo",
    idea: "rooftop confession",
    scene_count: 4,
  });
  assert.equal(out.mode, "project");
  assert.ok(out.project_id.startsWith("liveplay-lina-"));
  assert.equal(out.scenes.length, 4);
  assert.equal(out.endings.length, 3);
  assert.match(out.production_readiness.status, /ready/);
});

test("scene scene_count and total_scenes clamp to 3-6", () => {
  const out = scene({ mode: "project", scene_count: 99 });
  assert.equal(out.scenes.length, 6);
  const out2 = scene({ mode: "scene", scene_number: 99, total_scenes: 99 });
  assert.equal(out2.scene.total, 6);
});

test("choice returns the requested number of choices with outcomes", () => {
  const out = choice({ scene_summary: "two characters at odds", persona: "Mia", count: 3 });
  assert.equal(out.choices.length, 3);
  for (const c of out.choices) {
    assert.ok(c.label && c.outcome);
  }
});

test("choice clamps count to 2-3", () => {
  assert.equal(choice({ scene_summary: "x", count: 0 }).choices.length, 2);
  assert.equal(choice({ scene_summary: "x", count: 99 }).choices.length, 3);
});

test("ending returns the named arc and a closing beat", () => {
  const growth = ending({ arc: "growth", persona: "Lina" });
  assert.equal(growth.arc, "growth");
  assert.match(growth.ending.id, /growth/);
  assert.ok(growth.ending.closing_beat);

  const balanced = ending({ arc: "balanced", persona: "Lina" });
  assert.equal(balanced.arc, "balanced");
  assert.match(balanced.ending.id, /balance/);

  const chaos = ending({ arc: "chaos", persona: "Lina" });
  assert.equal(chaos.arc, "chaos");
  assert.match(chaos.ending.id, /chaos/);
});

test("normalizeVibe falls back to 'playful' for unknown vibes", () => {
  assert.equal(normalizeVibe("brutal"), "playful");
  assert.equal(normalizeVibe("CINEMATIC"), "cinematic");
  assert.equal(normalizeVibe(undefined), "playful");
});

test("buildSessionVibe is preserved verbatim from the legacy server", () => {
  const v = buildSessionVibe({ persona: "Mia", vibe: "cinematic", idea: "rooftop confession" });
  assert.equal(v.persona, "Mia");
  assert.equal(v.vibe, "cinematic");
  assert.match(v.short_prompt, /Mia/);
  assert.match(v.short_prompt, /Theme: rooftop confession/);
  assert.equal(v.notes.length, 3);
});

test("internal _internals exposes vibes + endings for inspection", () => {
  assert.ok(_internals.ALLOWED_VIBES.includes("playful"));
  assert.equal(_internals.ENDINGS.length, 3);
});
