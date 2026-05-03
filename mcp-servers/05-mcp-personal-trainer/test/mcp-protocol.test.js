import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-personal-trainer",
  version: "1.0.0",
  tools,
  sampleArgs: {
    trainer_workout_plan: {
      goal: "hypertrophy",
      days_per_week: 3,
      split: "full_body",
      current_injuries: ["right knee"],
    },
    trainer_recovery_check: {
      sleep_hours: 7.5,
      soreness_0_10: 3,
      perceived_exertion_0_10: 5,
      hrv_trend: "steady",
    },
    trainer_streak: {
      sessions_completed_this_week: 3,
      weeks_active: 12,
      planned_rest_days: 2,
    },
  },
  invalidArgs: {
    trainer_workout_plan: { days_per_week: 99 },
    trainer_recovery_check: { sleep_hours: 30 },
    trainer_streak: { sessions_completed_this_week: -5 },
  },
});
