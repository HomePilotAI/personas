/**
 * Personal Trainer business logic. Pure functions, no I/O.
 *
 * Programs are templates, not prescriptions. Every plan ships with:
 *   - explicit warm-up
 *   - RPE/RIR cues for main work
 *   - one regression + one progression per movement
 *   - injury-aware substitution if `current_injuries` is provided
 *   - a non-clinical disclaimer
 *
 * Red-flag medical symptoms short-circuit via withRedFlagGuard (see safety.js).
 */

import { withRedFlagGuard } from "./safety.js";

const NON_CLINICAL =
  "This is general fitness guidance, not medical advice. Stop and consult a physician if " +
  "you experience pain, dizziness, chest symptoms or sharp/sudden discomfort.";

const GOAL_TEMPLATES = {
  strength: {
    rpe: "RPE 7-8 (RIR 2-3)",
    sets: "3-5 sets x 3-6 reps",
    rest: "2-4 minutes",
    style: "Compound lifts first; accessories second; finisher optional.",
  },
  hypertrophy: {
    rpe: "RPE 7-9 (RIR 1-3)",
    sets: "3-4 sets x 8-12 reps",
    rest: "60-120 seconds",
    style: "Mix of compounds and isolations; control eccentrics.",
  },
  endurance: {
    rpe: "RPE 6-7 (zone 2 to threshold)",
    sets: "2-3 sets x 12-20 reps or 20-40 minutes continuous",
    rest: "30-90 seconds",
    style: "Higher reps; circuits acceptable; pair with conditioning blocks.",
  },
  general_health: {
    rpe: "RPE 6-7 (RIR 3-4)",
    sets: "2-3 sets x 8-12 reps",
    rest: "60-90 seconds",
    style: "Movement quality over intensity; full-body sessions 3x/week.",
  },
};

const SPLITS = {
  full_body: ["squat pattern", "hinge pattern", "push pattern", "pull pattern", "carry/core"],
  upper_lower: {
    upper: ["horizontal push", "horizontal pull", "vertical push", "vertical pull", "core"],
    lower: ["squat pattern", "hinge pattern", "single-leg", "calf/hamstring", "core"],
  },
  push_pull_legs: {
    push: ["bench press", "overhead press", "dips", "tricep extension", "lateral raise"],
    pull: ["row", "pull-up / lat pulldown", "rear delt", "biceps curl", "face pull"],
    legs: ["squat", "deadlift / hinge", "lunge", "leg curl", "calf raise"],
  },
};

const REGRESSIONS = {
  squat: { regression: "goblet box squat", progression: "tempo back squat" },
  deadlift: { regression: "RDL with light DBs", progression: "deficit deadlift" },
  bench: { regression: "DB bench press", progression: "pause bench press" },
  press: { regression: "seated DB press", progression: "push press" },
  row: { regression: "chest-supported row", progression: "Pendlay row" },
  pullup: { regression: "lat pulldown", progression: "weighted pull-up" },
  lunge: { regression: "split squat (rear-foot elevated)", progression: "walking lunge with load" },
};

function regressionFor(movement) {
  const m = String(movement || "").toLowerCase();
  for (const k of Object.keys(REGRESSIONS)) {
    if (m.includes(k)) return REGRESSIONS[k];
  }
  return { regression: "drop one set + reduce load 10-20%", progression: "add one rep per set or +2.5kg" };
}

function injuryFlag(injuries, movement) {
  if (!Array.isArray(injuries) || injuries.length === 0) return null;
  const m = String(movement).toLowerCase();
  const hits = injuries
    .map((i) => String(i || "").toLowerCase())
    .filter((i) => {
      if (!i) return false;
      if (i.includes("low back") && /(deadlift|squat|row|hinge)/.test(m)) return true;
      if (i.includes("knee") && /(squat|lunge|leg|jump)/.test(m)) return true;
      if (i.includes("shoulder") && /(press|push|bench|overhead)/.test(m)) return true;
      if (i.includes("elbow") && /(press|curl|extension|push)/.test(m)) return true;
      if (i.includes("wrist") && /(push|press|bench)/.test(m)) return true;
      return false;
    });
  return hits.length > 0 ? hits : null;
}

function buildSession(movements, goal, injuries) {
  const tmpl = GOAL_TEMPLATES[goal] || GOAL_TEMPLATES.general_health;
  return movements.map((m, idx) => {
    const reg = regressionFor(m);
    const flagged = injuryFlag(injuries, m);
    return {
      slot: idx + 1,
      movement: m,
      sets: tmpl.sets,
      rpe: tmpl.rpe,
      rest: tmpl.rest,
      regression: flagged ? `${reg.regression} (substitute due to ${flagged.join(", ")})` : reg.regression,
      progression: reg.progression,
      injury_caveat: flagged
        ? `Reported ${flagged.join(", ")} — work pain-free range only; reduce load 20-30%.`
        : null,
    };
  });
}

// ── Tool 1: workout plan ────────────────────────────────────────────────────

function buildWorkoutPlan({
  goal = "general_health",
  experience = "beginner",
  days_per_week = 3,
  split = "full_body",
  current_injuries = [],
  notes,  // free-text — checked by the safety guard before we ever get here
}) {
  const safeDays = Math.min(Math.max(Number.isInteger(days_per_week) ? days_per_week : 3, 1), 6);
  const safeGoal = GOAL_TEMPLATES[goal] ? goal : "general_health";

  const warmup = [
    "5 minutes easy cardio (rower / bike / brisk walk)",
    "Joint circles: ankles, hips, T-spine — 30 seconds each",
    "Two ramp-up sets at 50% and 70% of working weight before main work",
  ];

  const sessions = [];
  if (split === "upper_lower") {
    for (let i = 0; i < safeDays; i++) {
      const isUpper = i % 2 === 0;
      const movements = isUpper ? SPLITS.upper_lower.upper : SPLITS.upper_lower.lower;
      sessions.push({
        day: i + 1,
        focus: isUpper ? "upper" : "lower",
        warmup,
        main: buildSession(movements, safeGoal, current_injuries),
      });
    }
  } else if (split === "push_pull_legs") {
    const order = ["push", "pull", "legs"];
    for (let i = 0; i < safeDays; i++) {
      const focus = order[i % 3];
      sessions.push({
        day: i + 1,
        focus,
        warmup,
        main: buildSession(SPLITS.push_pull_legs[focus], safeGoal, current_injuries),
      });
    }
  } else {
    for (let i = 0; i < safeDays; i++) {
      sessions.push({
        day: i + 1,
        focus: "full_body",
        warmup,
        main: buildSession(SPLITS.full_body, safeGoal, current_injuries),
      });
    }
  }

  return {
    goal: safeGoal,
    template: GOAL_TEMPLATES[safeGoal],
    experience,
    split,
    days_per_week: safeDays,
    current_injuries: current_injuries || [],
    sessions,
    notes_acknowledged: notes ? String(notes).slice(0, 1000) : null,
    deload_rule: "Plan a deload week every 4-6 weeks: same movements, drop volume to ~60%.",
    disclaimer: NON_CLINICAL,
  };
}

// ── Tool 2: recovery check ──────────────────────────────────────────────────

function recoveryCheck({
  sleep_hours = 7,
  soreness_0_10 = 3,
  perceived_exertion_0_10 = 5,
  hrv_trend = "steady",
  notes,
}) {
  const sleep = Math.max(0, Math.min(14, Number(sleep_hours)));
  const sore = Math.max(0, Math.min(10, Number(soreness_0_10)));
  const rpe = Math.max(0, Math.min(10, Number(perceived_exertion_0_10)));

  // Composite readiness, 0-100. Higher is more ready.
  let score = 100;
  if (sleep < 6) score -= (6 - sleep) * 8;
  if (sleep < 4) score -= 10;
  score -= sore * 4;
  score -= Math.max(0, rpe - 5) * 3;
  if (hrv_trend === "down") score -= 12;
  if (hrv_trend === "up") score += 4;
  score = Math.max(0, Math.min(100, Math.round(score)));

  let recommendation;
  if (score >= 75) {
    recommendation = "green: train as planned.";
  } else if (score >= 55) {
    recommendation = "amber: lower top-set intensity by 1 RPE; cut accessory volume 25%.";
  } else if (score >= 35) {
    recommendation = "yellow: technique-only session at RPE 5-6 or active recovery.";
  } else {
    recommendation = "red: skip the workout; prioritise sleep and walking.";
  }

  return {
    inputs: { sleep_hours: sleep, soreness_0_10: sore, perceived_exertion_0_10: rpe, hrv_trend },
    score,
    recommendation,
    notes_acknowledged: notes ? String(notes).slice(0, 600) : null,
    disclaimer: NON_CLINICAL,
  };
}

// ── Tool 3: streak ──────────────────────────────────────────────────────────

function streak({
  sessions_completed_this_week = 0,
  weeks_active = 0,
  planned_rest_days = 0,
}) {
  const completed = Math.max(0, Math.min(14, Number(sessions_completed_this_week)));
  const weeks = Math.max(0, Math.min(520, Number(weeks_active)));
  const rest = Math.max(0, Math.min(7, Number(planned_rest_days)));

  const deload_due = weeks > 0 && weeks % 5 === 0;
  let band;
  if (weeks < 2) band = "starting";
  else if (weeks < 8) band = "building";
  else if (weeks < 26) band = "established";
  else band = "veteran";

  return {
    band,
    sessions_completed_this_week: completed,
    weeks_active: weeks,
    planned_rest_days: rest,
    rest_is_progress: true,
    deload_due,
    message: deload_due
      ? "You're at a deload week. Same movements, ~60% volume. The streak counts a deload as a session."
      : completed >= 3
        ? `Strong week — ${completed} sessions in. Protect tomorrow's rest day; momentum is built by recovery, not just reps.`
        : completed === 0
          ? "Pick the smallest possible session today. 20 minutes counts. Streaks are built by showing up tired, not by hitting PRs."
          : `On track — ${completed} session${completed === 1 ? "" : "s"} this week. One more before the next rest day.`,
    disclaimer: NON_CLINICAL,
  };
}

// Public, red-flag-guarded entry points.
export const workoutPlan = withRedFlagGuard(["notes"], (args) => buildWorkoutPlan(args));
export const recovery = withRedFlagGuard(["notes"], (args) => recoveryCheck(args));
export const trackStreak = (args) => streak(args || {});

export const _internals = { GOAL_TEMPLATES, regressionFor, injuryFlag };
