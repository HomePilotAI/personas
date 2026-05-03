import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
import { tools } from "../src/tools.js";

runProtocolHarness({
  name: "mcp-secretary-pro",
  version: "1.0.0",
  tools,
  sampleArgs: {
    secretary_schedule: {
      duration_minutes: 30,
      attendee_timezones: ["UTC", "CET"],
      earliest_iso: "2026-06-01T07:00:00Z",
    },
    secretary_remind: {
      title: "Send Q2 summary",
      due_iso: "2026-06-05T16:00:00Z",
      urgency: "today",
    },
    secretary_triage: {
      items: [
        { id: 1, subject: "URGENT: outage" },
        { id: 2, subject: "Newsletter" },
      ],
    },
  },
  invalidArgs: {
    secretary_schedule: { duration_minutes: 1 }, // below min(15)
    secretary_remind: { title: "" }, // missing due_iso + empty title
    secretary_triage: { items: "not-an-array" },
  },
});
