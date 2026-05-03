import assert from "node:assert/strict";
import { test } from "node:test";
import { buildOutfit, buildVariants } from "../src/style.js";

test("buildOutfit returns palette + 4 anchor pieces for known occasions", () => {
  const out = buildOutfit({ occasion: "business", vibe: "cool" });
  assert.equal(out.occasion, "business");
  assert.equal(out.vibe, "cool");
  assert.ok(out.palette.base.length >= 2);
  assert.ok(out.pieces.top);
  assert.ok(out.pieces.bottom);
  assert.ok(out.pieces.shoes);
  assert.equal(out.pieces.accents.length, 2);
});

test("buildOutfit normalizes unknown occasion + vibe to defaults", () => {
  const out = buildOutfit({ occasion: "spaceflight", vibe: "neon" });
  assert.equal(out.occasion, "casual");
  assert.equal(out.vibe, "earth");
});

test("buildOutfit folds weather context into styling notes", () => {
  const cold = buildOutfit({ occasion: "casual", weather: "cold and rainy" });
  assert.ok(cold.styling_notes.some((n) => /coat|scarf/i.test(n)));
  const hot = buildOutfit({ occasion: "casual", weather: "hot afternoon" });
  assert.ok(hot.styling_notes.some((n) => /jacket|breathe/i.test(n)));
});

test("buildVariants returns the requested number of variants", () => {
  const out = buildVariants({ base_look: "black tee + dark jeans + white sneakers", count: 4 });
  assert.equal(out.variants.length, 4);
  for (const v of out.variants) {
    assert.ok(v.before && v.after);
    assert.ok(v.axis);
    assert.notEqual(v.before, v.after);
  }
});

test("buildVariants requires base_look", () => {
  assert.throws(() => buildVariants({}), /base_look/i);
});

test("buildVariants count clamps to 1-5", () => {
  assert.equal(buildVariants({ base_look: "x", count: 99 }).variants.length, 5);
  assert.equal(buildVariants({ base_look: "x", count: 0 }).variants.length, 1);
});
