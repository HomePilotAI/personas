/**
 * Mindfulness Coach business logic. Pure functions, no I/O.
 *
 * Generates meditation, grounding, and focus scripts in the persona's voice
 * (slow, short sentences, signposted (pause) cues). Never claims clinical
 * effect; the safety guard in safety.js short-circuits any crisis input.
 */

import { withCrisisGuard } from "./safety.js";

const NON_CLINICAL_DISCLAIMER =
  "This is a non-clinical practice. If distress is persistent, please reach " +
  "a licensed mental-health professional.";

function pause(seconds) {
  return `(pause ${seconds}s)`;
}

function meditationScript({ minutes = 5, theme = "rest", style = "body_scan" }) {
  const safeMinutes = Math.min(Math.max(minutes, 1), 20);
  const lines = [];
  lines.push(`Settle in. (pause)`);
  lines.push(`Let your eyes soften, or close them if that's comfortable. ${pause(3)}`);
  lines.push(`We'll spend about ${safeMinutes} minute${safeMinutes === 1 ? "" : "s"} together.`);
  lines.push(`Take one slow breath in through the nose. ${pause(4)}`);
  lines.push(`And out, a little longer than the in-breath. ${pause(5)}`);

  if (style === "body_scan") {
    lines.push(`Bring attention to the top of your head. ${pause(4)}`);
    lines.push(`Notice the temperature, any contact, any tingling — without changing it. ${pause(5)}`);
    lines.push(`Let attention drift to your shoulders. ${pause(4)}`);
    lines.push(`If they're up around your ears, allow them to drop on the next out-breath. ${pause(5)}`);
    lines.push(`Down to the chest, the belly, the seat. ${pause(5)}`);
    lines.push(`To the legs, and the soles of the feet. ${pause(5)}`);
  } else if (style === "box_breath") {
    for (let i = 0; i < Math.min(safeMinutes, 6); i++) {
      lines.push(`Breathe in for four. ${pause(4)}`);
      lines.push(`Hold for four. ${pause(4)}`);
      lines.push(`Out for four. ${pause(4)}`);
      lines.push(`Hold empty for four. ${pause(4)}`);
    }
  } else {
    lines.push(`Notice the breath wherever it's easiest to feel — nostrils, chest, belly. ${pause(6)}`);
    lines.push(`When the mind wanders, that's the practice — gently come back. ${pause(8)}`);
  }

  lines.push(`Return to a normal breath. ${pause(3)}`);
  lines.push(`Notice how the body feels now, compared to when we started. ${pause(4)}`);
  lines.push(`When you're ready, let your eyes open. The rest of your day is here.`);

  return {
    minutes: safeMinutes,
    theme,
    style,
    script: lines,
    disclaimer: NON_CLINICAL_DISCLAIMER,
    notes: [
      "Speak each line slowly; the (pause Ns) cue is for the reader, not the listener.",
      "If a thought intrudes, acknowledge it and return — that's the practice.",
    ],
  };
}

function groundingScript({ trigger = "anxious", senses = 5 }) {
  const safeSenses = Math.min(Math.max(senses, 3), 5);
  const steps = [];
  if (safeSenses >= 5) steps.push({ count: 5, sense: "see", prompt: "Name 5 things you can see right now." });
  if (safeSenses >= 4) steps.push({ count: 4, sense: "feel", prompt: "Name 4 things you can feel — texture, temperature, pressure." });
  if (safeSenses >= 3) steps.push({ count: 3, sense: "hear", prompt: "Name 3 things you can hear." });
  if (safeSenses >= 2) steps.push({ count: 2, sense: "smell", prompt: "Name 2 things you can smell, or recall." });
  if (safeSenses >= 1) steps.push({ count: 1, sense: "taste", prompt: "Name 1 thing you can taste, or imagine tasting." });

  return {
    technique: "5-4-3-2-1 sensory grounding",
    trigger,
    senses: safeSenses,
    steps,
    closing:
      "Take one slow breath after each step. The point isn't to be right — it's " +
      "to put attention back into the body and out of the loop.",
    disclaimer: NON_CLINICAL_DISCLAIMER,
  };
}

function focusScript({ duration_seconds = 90, technique = "box_breath", before_task = null }) {
  const safeDuration = Math.min(Math.max(duration_seconds, 30), 600);
  const cycles = Math.max(1, Math.floor(safeDuration / 16));
  const steps = [];

  if (technique === "box_breath") {
    for (let i = 0; i < cycles; i++) {
      steps.push("In for four. Hold for four. Out for four. Hold for four.");
    }
  } else if (technique === "478") {
    for (let i = 0; i < Math.max(1, Math.floor(cycles / 2)); i++) {
      steps.push("In through the nose for four. Hold for seven. Out through the mouth for eight.");
    }
  } else {
    for (let i = 0; i < cycles; i++) {
      steps.push("Slow in. Slower out.");
    }
  }

  return {
    technique,
    duration_seconds: safeDuration,
    cycles,
    steps,
    next_step:
      before_task
        ? `When the timer ends, return to: ${before_task}.`
        : "When the timer ends, pick the smallest next step and start it.",
    disclaimer: NON_CLINICAL_DISCLAIMER,
  };
}

// Public, crisis-guarded entry points.
export const meditation = withCrisisGuard(["theme"], (args) => meditationScript(args));
export const grounding = withCrisisGuard(["trigger"], (args) => groundingScript(args));
export const focus = withCrisisGuard(["before_task"], (args) => focusScript(args));
