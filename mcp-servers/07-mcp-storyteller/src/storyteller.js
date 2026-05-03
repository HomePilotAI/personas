/**
 * Storyteller business logic. Pure functions, no I/O.
 *
 * Preserves the scene / branching / endings logic that previously lived in
 * the Express index.js (buildSessionVibe, buildBranchingProject, vibe
 * normalization, ending list) and exposes it as three canonical MCP tools:
 *
 *   - story_scene  → describes one scene with beats and a next-scene hook
 *   - story_choice → drafts 2-3 player choices for a scene
 *   - story_ending → resolves the arc into Growth / Balanced / Chaos
 *
 * The legacy (and richer) `build_branching_video_project` is kept reachable
 * via story_scene's `mode: "project"` so any caller that depended on the
 * previous shape doesn't lose data.
 *
 * All free-text inputs go through withContentGuard (see safety.js) — the
 * persona refuses sexual/violent content involving minors and hateful
 * tropes regardless of which tool is invoked.
 */

import { withContentGuard } from "./safety.js";

const ALLOWED_VIBES = [
  "teasing",
  "playful",
  "romantic",
  "mysterious",
  "cinematic",
  "comedic",
  "dramatic",
  "cozy",
  "high-energy",
];

const FOCUS_FOR_SCENE = (scene_number, total) =>
  scene_number === 1
    ? "hook"
    : scene_number === total
      ? "resolution"
      : "decision";

const ENDINGS = [
  { id: "ending_growth", title: "Growth Arc", summary: "User unlocks confident mastery." },
  { id: "ending_balance", title: "Balanced Arc", summary: "User succeeds with stable trust." },
  { id: "ending_chaos", title: "Chaos Arc", summary: "Bold risks create a memorable twist." },
];

function pick(arr, seed) {
  return arr[Math.abs(seed) % arr.length];
}

function slugify(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export function normalizeVibe(vibe) {
  if (!vibe) return "playful";
  const requested = String(vibe).trim().toLowerCase();
  return ALLOWED_VIBES.includes(requested) ? requested : "playful";
}

// Re-implementation of the legacy buildSessionVibe shape, exposed so callers
// who relied on it keep their data even after the protocol change.
export function buildSessionVibe({ persona = "Lina", vibe = "playful", idea = "" } = {}) {
  const normalizedVibe = normalizeVibe(vibe);
  const ideaText = idea ? ` Theme: ${idea}.` : "";
  return {
    persona,
    vibe: normalizedVibe,
    short_prompt:
      `${normalizedVibe} ${persona} live-play session with flirty tension, clear stakes, and ` +
      `escalating choices.${ideaText}`.trim(),
    notes: [
      "Keep prompts short and visual so video clips stay coherent.",
      "Each branch should reveal personality, not just information.",
      "Escalate emotional stakes across choices to improve retention.",
    ],
  };
}

// ── Tool 1: story_scene ─────────────────────────────────────────────────────

function singleScene({
  persona = "Lina",
  scene_number = 1,
  total_scenes = 4,
  vibe = "playful",
  companion,
  idea,
  rating = "sfw",
}) {
  const total = Math.min(Math.max(Number.isInteger(total_scenes) ? total_scenes : 4, 3), 6);
  const num = Math.min(Math.max(Number.isInteger(scene_number) ? scene_number : 1, 1), total);
  const v = normalizeVibe(vibe);
  const focus = FOCUS_FOR_SCENE(num, total);

  const beats =
    focus === "hook"
      ? [
          `Open on ${persona}, framed in ${v} light. One line of dialogue tells us who they are.`,
          `Establish the user's goal in a single visual beat — no exposition.`,
          `End on a glance / cut that promises a choice.`,
        ]
      : focus === "resolution"
        ? [
            `Resolve the choice the user just made — show, don't tell.`,
            `${persona} reacts: a moment of recognition or defiance.`,
            `Cut to the ending hook for the next tool call.`,
          ]
        : [
            `${persona} faces the consequence of choice ${num - 1}.`,
            `A second character (${companion || "a stranger"}) reframes the stakes.`,
            `Land on a charged silence before the next decision.`,
          ];

  const choices =
    focus === "resolution"
      ? []
      : [
          { id: `scene_${num}_choice_a`, label: "Lean in", outcome: "Increases intimacy and narrative risk." },
          { id: `scene_${num}_choice_b`, label: "Play it safe", outcome: "Keeps trust high but reduces dramatic payoff." },
        ];

  return {
    mode: "scene",
    persona,
    rating,
    vibe: v,
    scene: {
      id: `scene_${num}`,
      number: num,
      total: total,
      focus,
      title: `${persona} ${focus} ${num}`,
      setting: `${v} ${idea || "live-play moment"} — ${companion ? `with ${companion}` : "intimate framing"}.`,
      mood: v,
      beats,
      choices,
      next_scene_hook:
        focus === "resolution"
          ? "Hand off to story_ending for the closing beat."
          : `Tease the consequence of whichever choice the user picks; story_choice can draft the alternates.`,
    },
    target_words: 200,
  };
}

function buildProject({
  persona = "Lina",
  companion,
  idea,
  vibe = "playful",
  render_mode = "video",
  scene_count = 4,
  rating = "sfw",
}) {
  const total = Math.min(Math.max(Number.isInteger(scene_count) ? scene_count : 4, 3), 6);
  const v = normalizeVibe(vibe);
  const projectId = `liveplay-${slugify(persona)}-${Date.now().toString().slice(-6)}`;

  const scenes = Array.from({ length: total }, (_, i) =>
    singleScene({
      persona,
      scene_number: i + 1,
      total_scenes: total,
      vibe: v,
      companion,
      idea,
      rating,
    }).scene
  );

  return {
    mode: "project",
    project_id: projectId,
    persona,
    rating,
    companion: companion || null,
    render_media: render_mode === "image" ? "image" : "video",
    idea: idea || null,
    vibe_prompt: buildSessionVibe({ persona, vibe: v, idea }).short_prompt,
    format: {
      type: "branching-ai-video",
      has_scenes: true,
      has_choices: true,
      has_endings: true,
    },
    scenes,
    endings: ENDINGS,
    production_readiness: {
      status: "ready-for-production",
      checks: [
        "Scene-to-choice continuity included",
        "3 unique endings provided",
        "Video prompts are concise and reusable",
        "Supports fast image mode fallback",
      ],
    },
  };
}

// ── Tool 2: story_choice ────────────────────────────────────────────────────

function draftChoices({
  scene_summary,
  persona = "Lina",
  count = 2,
  vibe = "playful",
}) {
  const v = normalizeVibe(vibe);
  const safeCount = Math.min(Math.max(Number.isInteger(count) ? count : 2, 2), 3);

  const seed = (scene_summary || persona).length;
  const lean = pick(["lean in", "step closer", "double down", "hold the gaze"], seed);
  const safe = pick(["change the subject", "step back", "ask a question", "redirect"], seed + 1);
  const wild = pick(["walk away", "name the silence", "flip the script", "tell the truth"], seed + 2);

  const allChoices = [
    {
      id: "choice_lean",
      label: `${lean.charAt(0).toUpperCase() + lean.slice(1)}`,
      outcome: "Higher intimacy + higher narrative risk; ${persona} commits.".replace("${persona}", persona),
      reveals: `${persona} is curious about more than the surface story.`,
    },
    {
      id: "choice_safe",
      label: `${safe.charAt(0).toUpperCase() + safe.slice(1)}`,
      outcome: "Trust stays high, dramatic payoff drops; the next scene tightens.",
      reveals: `${persona} is aware of stakes the user hasn't named yet.`,
    },
    {
      id: "choice_wild",
      label: `${wild.charAt(0).toUpperCase() + wild.slice(1)}`,
      outcome: "Branch flips on its head; can lead to the Chaos ending.",
      reveals: `${persona} refuses the comfortable answer.`,
    },
  ];

  return {
    mode: "choice",
    scene_summary: scene_summary || null,
    persona,
    vibe: v,
    rule: "2-3 choices, each rewriting the next scene. Choices reveal personality, not just info.",
    choices: allChoices.slice(0, safeCount),
  };
}

// ── Tool 3: story_ending ────────────────────────────────────────────────────

function pickEnding({
  arc = "growth",
  persona = "Lina",
  branch_summary,
  vibe = "playful",
}) {
  const v = normalizeVibe(vibe);
  const safeArc = ["growth", "balanced", "chaos"].includes(arc) ? arc : "growth";
  const ending = ENDINGS.find((e) => e.id === `ending_${safeArc === "balanced" ? "balance" : safeArc}`);

  const closing =
    safeArc === "growth"
      ? `${persona} steps into the moment with steady eyes — the user's growth shows on their face.`
      : safeArc === "balanced"
        ? `${persona} chooses repair over winning — trust holds, the door stays open.`
        : `${persona} flips the table; the audience laughs, gasps, and remembers it.`;

  return {
    mode: "ending",
    arc: safeArc,
    persona,
    vibe: v,
    branch_summary: branch_summary || null,
    ending: {
      id: ending.id,
      title: ending.title,
      summary: ending.summary,
      closing_beat: closing,
      target_words: 80,
    },
    options: ENDINGS,
  };
}

// Public, content-guarded entry points.
export const scene = withContentGuard(["idea", "companion"], (args) =>
  args && args.mode === "project" ? buildProject(args) : singleScene(args)
);
export const choice = withContentGuard(["scene_summary"], (args) => draftChoices(args));
export const ending = withContentGuard(["branch_summary"], (args) => pickEnding(args));

export const _internals = { ALLOWED_VIBES, ENDINGS, buildProject, singleScene };
