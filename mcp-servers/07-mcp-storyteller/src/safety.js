/**
 * Content safety guard for the Storyteller.
 *
 * The persona's system prompt explicitly refuses sexual content involving
 * minors, explicit violence against minors, and hateful tropes. We replicate
 * that as a tool-level guardrail so the refusal is consistent regardless of
 * which tool is invoked. The default rating is SFW; callers can request NSFW
 * but never the absolute red lines.
 */

const HARD_REFUSALS = [
  /\bminor(s)?\b.*\b(sex|sexual|nude|nudity|porn)/i,
  /\b(sex|sexual|nude|nudity|porn)\b.*\bminor(s)?\b/i,
  /\bunderage\b/i,
  /\bchild(ren)?\b.*\b(sex|sexual|porn|abuse)/i,
  /\b(rape|torture)\b.*\b(child|minor|kid|teen)/i,
  /\b(genocide|ethnic cleansing).*\b(plan|how to|step)/i,
  /\b(plan|how to|step[- ]?by[- ]?step|instructions?).*\b(genocide|ethnic cleansing)/i,
];

const HATEFUL_TROPES = [
  /\b(slur|slurs)\b.*\b(use|generate|write)/i,
  /\b(jew|black|asian|muslim|gay|trans).*\b(deserve|inferior|subhuman)/i,
  /\bfinal solution\b/i,
];

export const HARD_REFUSAL_MESSAGE =
  "Storyteller refuses this scene. The persona will not produce sexual or " +
  "violent content involving minors, hateful content targeting protected " +
  "groups, or material that depicts real-world atrocities as instructions. " +
  "Pick a different premise and I'll happily stage it.";

export function detectHardRefusal(text) {
  if (!text || typeof text !== "string") return null;
  for (const p of HARD_REFUSALS) {
    if (p.test(text)) {
      return { reason: "hard_refusal_minors_or_atrocity", matched: p.source };
    }
  }
  for (const p of HATEFUL_TROPES) {
    if (p.test(text)) {
      return { reason: "hard_refusal_hateful_content", matched: p.source };
    }
  }
  return null;
}

export function withContentGuard(fields, generator) {
  return (args = {}) => {
    for (const f of fields) {
      const hit = detectHardRefusal(args[f]);
      if (hit) {
        return {
          refused: true,
          reason: hit.reason,
          matched_pattern: hit.matched,
          message: HARD_REFUSAL_MESSAGE,
        };
      }
    }
    return generator(args);
  };
}
