import assert from "node:assert/strict";
import { test } from "node:test";
import { inspire } from "../src/inspire.js";

test("returns the requested number of ideas", () => {
  const out = inspire({ topic: "the productivity wars", count: 4 });
  assert.equal(out.ideas.length, 4);
  assert.equal(out.topic, "the productivity wars");
});

test("each idea includes hook, scene, payoff, cta, caption and 5 hashtags", () => {
  const out = inspire({ topic: "espresso routines" });
  for (const idea of out.ideas) {
    assert.ok(idea.hook && typeof idea.hook === "string");
    assert.ok(idea.scene_idea);
    assert.ok(idea.payoff);
    assert.ok(idea.cta);
    assert.ok(idea.caption.includes(idea.cta) || idea.caption.length > 0);
    assert.equal(idea.hashtags.length, 5);
    assert.deepEqual(idea.structure, ["Hook", "Build", "Payoff", "CTA"]);
  }
});

test("platform bias swaps the hashtag bank", () => {
  const tiktok = inspire({ topic: "lentils", platform: "tiktok" });
  const reels = inspire({ topic: "lentils", platform: "reels" });
  const tiktokTags = tiktok.ideas[0].hashtags.join(" ");
  const reelsTags = reels.ideas[0].hashtags.join(" ");
  assert.ok(/fyp|tiktok/i.test(tiktokTags));
  assert.ok(/reels/i.test(reelsTags));
});

test("count is clamped to 1-5", () => {
  assert.equal(inspire({ topic: "x", count: 99 }).ideas.length, 5);
  assert.equal(inspire({ topic: "x", count: -3 }).ideas.length, 1);
});

test("tone is included in the caption when provided", () => {
  const out = inspire({ topic: "sourdough", tone: "encouraging" });
  assert.ok(out.ideas[0].caption.toLowerCase().includes("encouraging"));
});

test("topic is required", () => {
  assert.throws(() => inspire({}), /topic/i);
});
