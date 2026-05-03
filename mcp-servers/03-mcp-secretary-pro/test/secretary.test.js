import assert from "node:assert/strict";
import { test } from "node:test";
import { proposeSlots, draftReminder, triageInbox } from "../src/secretary.js";

test("proposeSlots returns 3 timezone-overlapping proposals when zones agree", () => {
  // CET + UTC overlap fully during European business hours.
  const out = proposeSlots({
    duration_minutes: 45,
    attendee_timezones: ["CET", "UTC"],
    earliest_iso: "2026-06-01T07:00:00Z", // Monday early
    search_days: 3,
  });
  assert.equal(out.duration_minutes, 45);
  assert.equal(out.proposals.length, 3);
  for (const p of out.proposals) {
    for (const z of p.per_zone) {
      assert.equal(z.within_working_hours, true, `${z.zone} not in working hours`);
    }
  }
});

test("proposeSlots offers a fallback when zones don't fully overlap", () => {
  // PST + IST is the classic split-day case; few or no full overlaps.
  const out = proposeSlots({
    duration_minutes: 30,
    attendee_timezones: ["PST", "IST"],
    earliest_iso: "2026-06-01T00:00:00Z",
    search_days: 5,
  });
  if (out.proposals.length === 0) {
    assert.ok(out.fallback, "expected at least a fallback when no full overlap");
  } else {
    // If we did find a clean overlap, fallback may be null — both fine.
    assert.ok(true);
  }
});

test("proposeSlots clamps duration and validates earliest_iso", () => {
  assert.equal(proposeSlots({ duration_minutes: 9999, earliest_iso: "2026-06-01T07:00:00Z" })
    .duration_minutes, 240);
  assert.throws(() => proposeSlots({ earliest_iso: "not-a-date" }), /ISO/);
});

test("draftReminder returns a draft envelope without side effects", () => {
  const out = draftReminder({
    title: "Send weekly status",
    due_iso: "2026-06-05T16:00:00Z",
    urgency: "today",
  });
  assert.equal(out.draft, true);
  assert.match(out.next_step, /Drafted only/i);
  assert.equal(out.urgency, "today");
  assert.ok(out.suggested_lead_minutes > 0);
});

test("draftReminder rejects bad inputs", () => {
  assert.throws(() => draftReminder({}), /title/i);
  assert.throws(
    () => draftReminder({ title: "x", due_iso: "tomorrow" }),
    /ISO/
  );
  assert.throws(
    () => draftReminder({ title: "x", due_iso: "2026-06-01T00:00:00Z", urgency: "soon" }),
    /urgency/
  );
});

test("triageInbox routes items to the right urgency buckets", () => {
  const out = triageInbox({
    items: [
      { id: "1", subject: "URGENT: prod outage" },
      { id: "2", subject: "Client review today at 4pm" },
      { id: "3", subject: "Q3 planning review next week" },
      { id: "4", subject: "Newsletter from someone" },
    ],
  });
  assert.equal(out.counts.now, 1);
  assert.equal(out.counts.today, 1);
  assert.equal(out.counts.this_week, 1);
  assert.equal(out.counts.defer, 1);
  for (const arr of Object.values(out.buckets)) {
    for (const it of arr) assert.ok(it.rationale);
  }
});

test("triageInbox caps at 100 items per call", () => {
  const items = Array.from({ length: 101 }, (_, i) => ({ id: i, subject: `note ${i}` }));
  assert.throws(() => triageInbox({ items }), /100/);
});
