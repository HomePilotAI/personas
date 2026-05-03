/**
 * Secretary Pro business logic. Pure functions, no I/O.
 *
 * Three tools:
 *   - proposeSlots: 3 timezone-aware proposals + fallback for a duration
 *     and attendee zone list. Working hours per zone are 09:00-18:00 local.
 *   - draftReminder: build a structured reminder envelope (no side effects).
 *   - triageInbox: bucket inbox items by urgency with a short rationale.
 *
 * Policy: this server NEVER actually sends a message or creates a real
 * calendar entry. Outputs are drafts; the caller commits them.
 */

// ── Time helpers ────────────────────────────────────────────────────────────

const ZONE_OFFSETS = {
  // Common business zones — kept small. Hours are offsets from UTC.
  // DST is ignored on purpose; this is a draft, not a booking.
  UTC: 0,
  GMT: 0,
  WET: 0,
  CET: 1,
  CEST: 2,
  BST: 1,
  EET: 2,
  EEST: 3,
  IST: 5.5,
  SGT: 8,
  HKT: 8,
  CST: -6,
  EST: -5,
  EDT: -4,
  PST: -8,
  PDT: -7,
  MST: -7,
  AKT: -9,
  AEST: 10,
  AEDT: 11,
  NZST: 12,
};

function offsetFor(zone) {
  if (typeof zone !== "string") return 0;
  const k = zone.trim().toUpperCase();
  return ZONE_OFFSETS[k] ?? 0;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function formatLocal(utcDate, zone) {
  const offsetH = offsetFor(zone);
  const local = new Date(utcDate.getTime() + offsetH * 60 * 60 * 1000);
  return (
    `${local.getUTCFullYear()}-${pad(local.getUTCMonth() + 1)}-${pad(local.getUTCDate())}` +
    `T${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())} ${zone.toUpperCase()}`
  );
}

function isWithinWorkingHours(utcDate, zone) {
  const offsetH = offsetFor(zone);
  const local = new Date(utcDate.getTime() + offsetH * 60 * 60 * 1000);
  const hour = local.getUTCHours();
  const dow = local.getUTCDay(); // 0 Sun ... 6 Sat
  if (dow === 0 || dow === 6) return false;
  return hour >= 9 && hour < 18;
}

// ── Tool 1: schedule ────────────────────────────────────────────────────────

export function proposeSlots({
  duration_minutes = 30,
  attendee_timezones = ["UTC"],
  earliest_iso,
  search_days = 5,
}) {
  const safeDur = Math.min(Math.max(Number.isInteger(duration_minutes) ? duration_minutes : 30, 15), 240);
  const safeDays = Math.min(Math.max(Number.isInteger(search_days) ? search_days : 5, 1), 21);
  const zones = (Array.isArray(attendee_timezones) && attendee_timezones.length > 0
    ? attendee_timezones
    : ["UTC"]
  ).map((z) => z.toUpperCase());

  const now = earliest_iso ? new Date(earliest_iso) : new Date();
  if (Number.isNaN(now.getTime())) {
    throw new Error("earliest_iso is not a valid ISO datetime");
  }

  // Walk forward in 30-minute steps until we have 3 slots that fall in
  // working hours for every zone. Bail after `search_days * 48` steps.
  const proposals = [];
  const fallback = [];
  const stepMs = 30 * 60 * 1000;
  const maxSteps = safeDays * 48;
  let cursor = new Date(now.getTime());

  for (let i = 0; i < maxSteps && proposals.length < 3; i++) {
    cursor = new Date(now.getTime() + i * stepMs);
    const okEverywhere = zones.every((z) => isWithinWorkingHours(cursor, z));
    const okMostly = zones.filter((z) => isWithinWorkingHours(cursor, z)).length >= zones.length - 1;

    if (okEverywhere) {
      proposals.push(buildSlot(cursor, safeDur, zones));
    } else if (okMostly && fallback.length < 1) {
      fallback.push(buildSlot(cursor, safeDur, zones));
    }
  }

  return {
    duration_minutes: safeDur,
    attendee_timezones: zones,
    proposals,
    fallback: fallback[0] || null,
    rule:
      "Working hours assumed 09:00-18:00 local Mon-Fri. DST is ignored — confirm before booking.",
    notes: [
      "Drafts only — Secretary Pro never books on your behalf.",
      "If the fallback is the only option, bring it to the meeting owner before sending invites.",
    ],
  };
}

function buildSlot(utcDate, duration, zones) {
  const end = new Date(utcDate.getTime() + duration * 60 * 1000);
  return {
    start_utc: utcDate.toISOString(),
    end_utc: end.toISOString(),
    per_zone: zones.map((z) => ({
      zone: z,
      start_local: formatLocal(utcDate, z),
      end_local: formatLocal(end, z),
      within_working_hours: isWithinWorkingHours(utcDate, z),
    })),
  };
}

// ── Tool 2: remind ──────────────────────────────────────────────────────────

const URGENCY_BUCKETS = ["now", "today", "this_week", "defer"];

export function draftReminder({
  title,
  due_iso,
  channel = "calendar",
  urgency = "today",
  context,
}) {
  if (!title || typeof title !== "string") throw new Error("title is required");
  if (!due_iso) throw new Error("due_iso is required");
  const due = new Date(due_iso);
  if (Number.isNaN(due.getTime())) throw new Error("due_iso is not a valid ISO datetime");
  if (!URGENCY_BUCKETS.includes(urgency)) {
    throw new Error(`urgency must be one of ${URGENCY_BUCKETS.join(", ")}`);
  }

  const minutesAhead = Math.round((due.getTime() - Date.now()) / 60000);

  return {
    draft: true,
    title: title.slice(0, 200),
    due_iso: due.toISOString(),
    minutes_until_due: minutesAhead,
    channel,
    urgency,
    context: context ? String(context).slice(0, 1000) : null,
    suggested_lead_minutes: urgency === "now" ? 0 : urgency === "today" ? 30 : 120,
    next_step:
      "Drafted only — pass this envelope to your reminder/calendar tool to commit. " +
      "Secretary Pro does not write to external systems.",
  };
}

// ── Tool 3: triage ──────────────────────────────────────────────────────────

const NOW_PATTERNS = [/\burgent\b/i, /\bASAP\b/i, /\bbroken\b/i, /\bdown\b/i, /\boutage\b/i, /\bblocker\b/i];
const TODAY_PATTERNS = [/\btoday\b/i, /\bEOD\b/i, /\beod\b/i, /\bclient\b/i, /\bboard\b/i, /\binvestor\b/i];
const WEEK_PATTERNS = [/\bthis week\b/i, /\bfriday\b/i, /\bnext week\b/i, /\breview\b/i];

function classify(item) {
  const text = `${item.subject || ""} ${item.snippet || ""} ${item.from || ""}`;
  if (NOW_PATTERNS.some((p) => p.test(text))) return "now";
  if (TODAY_PATTERNS.some((p) => p.test(text))) return "today";
  if (WEEK_PATTERNS.some((p) => p.test(text))) return "this_week";
  return "defer";
}

export function triageInbox({ items = [] }) {
  if (!Array.isArray(items)) throw new Error("items must be an array");
  if (items.length > 100) {
    throw new Error("triage capped at 100 items per call");
  }

  const buckets = { now: [], today: [], this_week: [], defer: [] };
  for (const raw of items) {
    if (!raw || typeof raw !== "object") continue;
    const item = {
      id: String(raw.id ?? Math.random().toString(36).slice(2, 8)),
      from: raw.from ? String(raw.from).slice(0, 200) : null,
      subject: raw.subject ? String(raw.subject).slice(0, 280) : "",
      snippet: raw.snippet ? String(raw.snippet).slice(0, 600) : "",
    };
    const bucket = classify(item);
    buckets[bucket].push({
      ...item,
      rationale:
        bucket === "now"
          ? "Contains a stop-the-line keyword (urgent / outage / blocker)."
          : bucket === "today"
            ? "Time-bound or client/board-facing — same-day response."
            : bucket === "this_week"
              ? "Soft deadline this week — schedule rather than react."
              : "No urgency markers — defer to a weekly review.",
    });
  }

  return {
    bucket_definitions: {
      now: "Stop the line. Respond or escalate within minutes.",
      today: "Reply / decide before EOD.",
      this_week: "Schedule for the appropriate day this week.",
      defer: "Park in a weekly review queue.",
    },
    counts: {
      now: buckets.now.length,
      today: buckets.today.length,
      this_week: buckets.this_week.length,
      defer: buckets.defer.length,
    },
    buckets,
    note: "Triage only — no replies were drafted or sent.",
  };
}

export const _internals = { ZONE_OFFSETS, isWithinWorkingHours, classify };
