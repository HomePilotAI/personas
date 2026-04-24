# MCP Server Verification for High-Virality Persona Portfolio

Date: 2026-04-24

## What was verified

This verification checks each MCP server for:

1. Baseline MCP contract support (`/health`, `/tools`, tool POST routes).
2. Context Forge compatibility (`/context-forge/tools`, `/context-forge/call` via shared attach function).
3. Presence of each declared `server.json` tool in both endpoint and runner dispatch paths.
4. Heuristic capability signals aligned to the persona wave strategy (A/B/C).

Script: `scripts/verify_mcp_portfolio.py`

## Result summary

- **Contract compatibility**: all 10 servers pass baseline checks.
- **Context Forge compatibility**: all 10 servers pass (shared route attachment present).
- **Tool coverage**: all declared tools are wired in endpoint+runner checks.
- **Production-depth readiness**: mixed — several personas still provide lightweight logic and need deeper integrations for full virality outcomes.

## Readiness by wave

### Wave A (showpiece virality)

- Creator Muse: baseline-ready, needs richer media/export pipeline integration.
- Style Muse: baseline-ready, needs stronger image-edit/variant workflows.
- Secretary Pro: baseline-ready, needs external communication escalation integrations.
- Researcher: baseline-ready, needs live citation retrieval/grounding and ingestion pipeline hardening.
- Personal Trainer: baseline-ready, needs reminders/streak/accountability loop integrations.

### Wave B (utility + shareable artifacts)

- Room Stylist: baseline-ready, needs true photo transform and before/after generation flow.
- Storyteller: most complete of current implementations; still needs end-to-end render/export integration for production rollout.
- Exam Coach: baseline-ready, needs document-ingestion and adaptive weak-topic memory.

### Wave C (retention/trust-heavy)

- Mindfulness Coach: baseline-ready, should keep strict self-help framing + escalation copy.
- General Doctor: baseline-ready at contract level, but requires stricter red-flag triage, safety policy enforcement, and compliance review before public launch.

## One-by-one compatibility statement

All MCP servers are **compatible at interface level** for AI-agent orchestration in HomePilot:

- consistent endpoint contract,
- discoverable tool metadata,
- context-forge call surface,
- per-tool dispatch wiring.

They are **not all yet equivalent at production capability depth** for the full virality portfolio roadmap.

