/**
 * Safety guardrail for the Mindfulness Coach.
 *
 * The persona is explicitly non-clinical (see scripts/persona_data.py
 * system_prompt). When user input mentions crisis-level distress we replace
 * any generated script with a clear escalation message pointing to a
 * licensed professional / local crisis line. We err on the side of
 * over-escalating: false positives are inconvenient, missed crisis cues
 * could be harmful.
 */

const CRISIS_PATTERNS = [
  /\bsuicid(e|al)\b/i,
  /\bkill (myself|me)\b/i,
  /\bend(ing|ed|s)?\s+(it all|my life|it)\b/i,
  /\bself[- ]harm/i,
  /\bcutting myself\b/i,
  /\boverdose\b/i,
  /\bpanic attack\b/i,
  /\bcan'?t (breathe|stop crying)\b/i,
  /\bflashback(s)?\b/i,
  /\bptsd\b/i,
];

export const ESCALATION_MESSAGE =
  "I'm a mindfulness companion, not a clinician. What you're describing sounds like " +
  "it deserves a real human professional — please reach a licensed mental-health " +
  "provider or your local crisis line right now. In the US you can dial or text 988; " +
  "in the UK call Samaritans on 116 123; elsewhere search 'mental health crisis line' " +
  "with your country name. If you're in immediate danger, contact emergency services.";

export const ESCALATION_RESOURCES = [
  { region: "US", line: "988 Suicide & Crisis Lifeline", contact: "call or text 988" },
  { region: "UK / IE", line: "Samaritans", contact: "call 116 123 (free)" },
  { region: "AU", line: "Lifeline Australia", contact: "call 13 11 14" },
  { region: "International", line: "findahelpline.com", contact: "directory of crisis lines worldwide" },
];

/**
 * Inspect a user-provided text field. If any crisis pattern hits, returns an
 * escalation envelope; otherwise returns null and callers proceed normally.
 */
export function detectCrisis(text) {
  if (!text || typeof text !== "string") return null;
  for (const pattern of CRISIS_PATTERNS) {
    if (pattern.test(text)) {
      return {
        escalated: true,
        reason: "crisis_signal_detected",
        matched_pattern: pattern.source,
        message: ESCALATION_MESSAGE,
        resources: ESCALATION_RESOURCES,
      };
    }
  }
  return null;
}

/**
 * Wrap a generator so a crisis signal short-circuits the script. `fields`
 * is the array of free-text fields to inspect on the input args.
 */
export function withCrisisGuard(fields, generator) {
  return (args = {}) => {
    for (const f of fields) {
      const hit = detectCrisis(args[f]);
      if (hit) return hit;
    }
    return generator(args);
  };
}
