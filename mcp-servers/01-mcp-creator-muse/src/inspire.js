/**
 * Creator Muse business logic. No MCP / transport concerns here — this
 * module is a pure function so it stays easy to unit-test.
 *
 * Returns three deterministic-but-varied idea pitches following the
 * Hook → Build → Payoff → CTA structure described in the persona prompt.
 * Each idea ships with a caption and five hashtag suggestions so callers
 * have a complete short-form post in hand.
 */

const HOOK_OPENERS = [
  "POV:",
  "Stop scrolling —",
  "Nobody talks about this, but",
  "If you ever felt",
  "The 60-second version of",
];

const SCENES = [
  "fast cuts of context",
  "single take with on-screen captions",
  "split-screen before/after",
  "static b-roll + bold overlay text",
  "talking head + reaction inserts",
];

const PAYOFFS = [
  "the one detail that flips the whole story",
  "a stat people will screenshot",
  "the unexpected micro-tutorial",
  "the relatable confession that earns the share",
  "the visual punchline that begs a re-watch",
];

const CTAS = [
  "Save this so future-you doesn't waste 30 minutes.",
  "Comment your version and I'll stitch the best ones.",
  "Follow for the full 5-part series.",
  "Send to the friend you keep arguing with about this.",
  "Reply with your topic and I'll script the next one.",
];

const HASHTAG_BANKS = {
  default: ["creators", "shortform", "viral", "growth", "contentstrategy"],
  reels: ["reels", "reelsinstagram", "reelitfeelit", "reelsdaily", "reelsoftheday"],
  tiktok: ["tiktokmademebuyit", "tiktoktips", "fyp", "creatorlife", "shorts"],
  carousel: ["carouselpost", "swipeleft", "instaeducation", "valuepost", "saveforlater"],
  youtubeShorts: ["shorts", "ytshorts", "youtubeshorts", "shortsvideo", "viralshorts"],
};

const PLATFORM_HASHTAGS = {
  reels: HASHTAG_BANKS.reels,
  tiktok: HASHTAG_BANKS.tiktok,
  shorts: HASHTAG_BANKS.youtubeShorts,
  "youtube shorts": HASHTAG_BANKS.youtubeShorts,
  carousel: HASHTAG_BANKS.carousel,
  carousels: HASHTAG_BANKS.carousel,
};

function pickRotated(items, seed, offset = 0) {
  return items[(seed + offset) % items.length];
}

function tagSlug(s) {
  return String(s)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "")
    .slice(0, 30);
}

function platformHashtags(platform) {
  if (!platform) return HASHTAG_BANKS.default;
  return PLATFORM_HASHTAGS[platform.toLowerCase()] || HASHTAG_BANKS.default;
}

function seedFromTopic(topic) {
  let h = 0;
  for (const c of topic) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return h;
}

export function inspire({ topic, medium, tone, platform, count = 3 } = {}) {
  if (!topic || typeof topic !== "string") {
    throw new Error("topic is required");
  }
  const seed = seedFromTopic(topic);
  const platformBank = platformHashtags(platform);
  const topicTag = tagSlug(topic);
  const safeCount = Math.min(Math.max(Number.isInteger(count) ? count : 3, 1), 5);

  const ideas = Array.from({ length: safeCount }, (_, i) => {
    const hook = `${pickRotated(HOOK_OPENERS, seed, i)} ${topic}`.trim();
    const scene = pickRotated(SCENES, seed, i + 1);
    const payoff = pickRotated(PAYOFFS, seed, i + 2);
    const cta = pickRotated(CTAS, seed, i + 3);

    const caption =
      `${hook} — ${payoff}. ` +
      (tone ? `Keep it ${tone}. ` : "") +
      cta;

    const hashtagPool = [
      topicTag,
      ...platformBank,
      ...HASHTAG_BANKS.default,
    ].filter(Boolean);
    const hashtags = Array.from(new Set(hashtagPool)).slice(0, 5).map((t) => `#${t}`);

    return {
      id: `idea-${i + 1}`,
      hook,
      scene_idea: scene,
      payoff,
      cta,
      caption,
      hashtags,
      structure: ["Hook", "Build", "Payoff", "CTA"],
    };
  });

  return {
    topic,
    medium: medium || "short-form video",
    tone: tone || "playful",
    platform: platform || null,
    ideas,
    notes: [
      "Each idea follows Hook → Build → Payoff → CTA.",
      "Pick the one that reveals personality, not just information.",
      "Never claim guaranteed virality.",
    ],
  };
}
