import assert from "node:assert/strict";
import { test } from "node:test";
import { proposeLayout, buildPalette, buildShoppingList } from "../src/stylist.js";

test("proposeLayout returns up to 3 layout options for known rooms", () => {
  const out = proposeLayout({ room: "living", length_m: 5.2, width_m: 3.6, options: 3 });
  assert.equal(out.room, "living");
  assert.equal(out.layouts.length, 3);
  for (const l of out.layouts) {
    assert.ok(l.focus_zone);
    assert.ok(l.anchor_piece);
    assert.ok(Array.isArray(l.arrangement));
    assert.ok(l.arrangement.length >= 3);
  }
});

test("proposeLayout falls back to 'living' for unknown rooms and clamps options", () => {
  const out = proposeLayout({ room: "ballroom", options: 99 });
  assert.equal(out.room, "living");
  assert.equal(out.layouts.length, 3);
});

test("buildPalette emits 60/30/10 with hex anchors and materials", () => {
  const out = buildPalette({ room: "office", mood: "cool_modern" });
  assert.equal(out.mood, "cool_modern");
  assert.ok(out.palette.sixty.hex.startsWith("#"));
  assert.ok(out.palette.thirty.hex.startsWith("#"));
  assert.ok(out.palette.ten.hex.startsWith("#"));
  assert.ok(out.materials.length >= 3);
});

test("buildPalette tolerates unknown mood by defaulting to warm_minimal", () => {
  const out = buildPalette({ room: "bedroom", mood: "neon_brutalism" });
  assert.equal(out.mood, "warm_minimal");
});

test("buildShoppingList groups items across 3 tiers", () => {
  const out = buildShoppingList({ room: "kitchen", palette: "earth_organic" });
  assert.deepEqual(out.tiers, ["good", "better", "heirloom"]);
  for (const it of out.items) {
    assert.equal(it.tiers.length, 3);
    assert.ok(it.tiers.every((t) => t.guidance));
  }
});
