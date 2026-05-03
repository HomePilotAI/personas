import assert from "node:assert/strict";
import { test } from "node:test";
import { workoutPlan, recovery, trackStreak } from "../src/training.js";

test("workoutPlan produces N sessions with warmup + main + regressions", () => {
  const out = workoutPlan({
    goal: "hypertrophy",
    days_per_week: 4,
    split: "upper_lower",
  });
  assert.equal(out.sessions.length, 4);
  for (const s of out.sessions) {
    assert.ok(Array.isArray(s.warmup));
    assert.ok(s.main.length >= 4);
    for (const m of s.main) {
      assert.ok(m.regression);
      assert.ok(m.progression);
      assert.ok(m.rpe);
    }
  }
  assert.match(out.disclaimer, /not medical/i);
});

test("workoutPlan attaches injury caveats and substitutes regressions", () => {
  const out = workoutPlan({
    goal: "strength",
    days_per_week: 2,
    split: "full_body",
    current_injuries: ["low back"],
  });
  // The hinge slot should pick up an injury caveat.
  const hinge = out.sessions[0].main.find((m) => /hinge/.test(m.movement));
  assert.ok(hinge, "expected a hinge movement in a full_body session");
  assert.ok(hinge.injury_caveat, "expected injury caveat on hinge");
  assert.match(hinge.regression, /low back/i);
});

test("workoutPlan clamps days_per_week to 1-6", () => {
  assert.equal(workoutPlan({ days_per_week: 99 }).sessions.length, 6);
  assert.equal(workoutPlan({ days_per_week: 0 }).sessions.length, 1);
});

test("recovery composes a 0-100 score with traffic-light recommendation", () => {
  const great = recovery({
    sleep_hours: 8,
    soreness_0_10: 1,
    perceived_exertion_0_10: 5,
    hrv_trend: "up",
  });
  assert.ok(great.score >= 75);
  assert.match(great.recommendation, /green/i);

  const wrecked = recovery({
    sleep_hours: 3,
    soreness_0_10: 9,
    perceived_exertion_0_10: 9,
    hrv_trend: "down",
  });
  assert.ok(wrecked.score <= 35);
  assert.match(wrecked.recommendation, /skip|red/i);
});

test("trackStreak honors planned rest and surfaces deload at week 5/10/15...", () => {
  const week1 = trackStreak({ sessions_completed_this_week: 0, weeks_active: 1 });
  assert.equal(week1.band, "starting");
  assert.equal(week1.deload_due, false);

  const week5 = trackStreak({ sessions_completed_this_week: 3, weeks_active: 5 });
  assert.equal(week5.deload_due, true);
  assert.match(week5.message, /deload/i);

  const veteran = trackStreak({ weeks_active: 60 });
  assert.equal(veteran.band, "veteran");
});
