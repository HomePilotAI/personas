/**
 * Safety guardrail for the Personal Trainer persona.
 *
 * The persona is not a clinician (see scripts/persona_data.py system_prompt).
 * Any free-text input mentioning red-flag medical symptoms short-circuits the
 * workout/recovery/streak generators with a structured escalation envelope.
 */

const RED_FLAGS = [
  /\bchest pain\b/i,
  /\bsharp pain\b/i,
  /\bradiating pain\b/i,
  /\bshortness of breath\b/i,
  /\bcan'?t breathe\b/i,
  /\bdizz(y|iness)\b/i,
  /\bfainted?\b/i,
  /\bblack(ed)? out\b/i,
  /\bnumb(ness)?\b/i,
  /\btingling\b/i,
  /\bblood (in|when)\b/i,
  /\bhead inj(ury|ured)\b/i,
  /\bconcussion\b/i,
  /\bbleeding\b/i,
  /\bswollen\b/i,
  /\bpregnan(t|cy) complication/i,
];

export const ESCALATION_MESSAGE =
  "Stop the session. The symptom you described needs a medical professional, not a workout " +
  "plan. Please contact your physician or, for chest pain / shortness of breath / sudden " +
  "neurological symptoms / suspected concussion, call your local emergency number now. " +
  "Personal Trainer is not a clinician.";

export function detectRedFlag(text) {
  if (!text || typeof text !== "string") return null;
  for (const p of RED_FLAGS) {
    if (p.test(text)) {
      return {
        escalated: true,
        reason: "medical_red_flag_detected",
        matched_pattern: p.source,
        message: ESCALATION_MESSAGE,
        next_step:
          "Resume training only after a clinician clears the symptom. " +
          "Personal Trainer can rebuild the plan around any restrictions they give you.",
      };
    }
  }
  return null;
}

export function withRedFlagGuard(fields, generator) {
  return (args = {}) => {
    for (const f of fields) {
      const hit = detectRedFlag(args[f]);
      if (hit) return hit;
    }
    return generator(args);
  };
}
