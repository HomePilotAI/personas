"""FastMCP entry point for the General Doctor safety adapter.

Three canonical tools land here. Each one:

  1. Builds a request_id and a CallTimer (audit).
  2. Runs the adapter's own red-flag detector on user inputs *before* any
     upstream call. If a red flag fires, the adapter short-circuits to an
     emergency envelope and never asks the upstream for help.
  3. Calls the upstream `medical-mcp-toolkit` over HTTP for the data path.
  4. Runs every string through the safety output-filter and tracks blocked
     categories.
  5. Emits a no-PHI audit event.

The adapter refuses to register tools when ``GENERAL_DOCTOR_ADAPTER_ENABLED``
is false (rollback knob); we register a single ``adapter_status`` shape in
that case so MCP clients still get a typed answer.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .audit import AuditEvent, AuditLogger, CallTimer, maybe_hash, safe_input_summary
from .config import DoctorConfig
from .safety import (
    TriageInput,
    detect_red_flags,
    emergency_guidance,
    filter_lines,
    filter_text,
)
from .schemas import (
    AdapterDisabledResult,
    EscalationEnvelope,
    GeneralInfoResult,
    RedFlagsResult,
    SelfCareResult,
)
from .upstream import UpstreamClient, UpstreamResponse

CONFIG = DoctorConfig.from_env()

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("mcp-general-doctor")

mcp = FastMCP("mcp-general-doctor")

_audit = AuditLogger(
    log_path=CONFIG.audit_log_path,
    hash_user_input=CONFIG.audit_hash_user_input,
)

_upstream = UpstreamClient(
    base_url=CONFIG.upstream_url,
    bearer=CONFIG.upstream_bearer,
    timeout_s=CONFIG.upstream_timeout_s,
    offline_fallback=CONFIG.upstream_offline_fallback,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _as_dict(model) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _emit(
    *,
    request_id: str,
    tool: str,
    risk_level: str,
    timer: CallTimer,
    matched: list[str],
    upstream: UpstreamResponse | None,
    blocked: list[str],
    args: dict[str, Any],
    error: str | None = None,
) -> None:
    _audit.emit(
        AuditEvent(
            request_id=request_id,
            timestamp=_audit.now_iso(),
            tool=tool,
            risk_level=risk_level,
            red_flag_detected=bool(matched),
            matched_red_flags=matched,
            upstream_tool=("triageSymptoms" if tool != "doctor_general_info" else "searchMedicalKB"),
            upstream_status=(upstream.status if upstream else None),
            blocked_categories=blocked,
            latency_ms=timer.elapsed_ms(),
            error_type=error,
            user_input_sha256=maybe_hash(
                safe_input_summary(args), enabled=CONFIG.audit_hash_user_input
            ),
        )
    )


def _disabled(tool: str) -> dict[str, Any]:
    return _as_dict(AdapterDisabledResult(tool=tool))


# ── Tool 1: doctor_red_flags ────────────────────────────────────────────────


@mcp.tool()
def doctor_red_flags(
    symptoms: Annotated[
        list[str],
        Field(min_length=1, max_length=20, description="Symptoms reported by the user."),
    ],
    age: Annotated[
        float | None,
        Field(ge=0, le=120, description="Age in years (fractional for under-1s, e.g. 0.5 for 6 months)."),
    ] = None,
    sex: Annotated[
        Literal["female", "male", "intersex", "unknown"] | None,
        Field(description="Sex assigned at birth (or 'unknown')."),
    ] = None,
    free_text: Annotated[
        str | None,
        Field(max_length=2000, description="Any extra context the user typed."),
    ] = None,
    pregnant: Annotated[
        bool | None,
        Field(description="Whether the user is currently pregnant. Triggers structured pregnancy checks."),
    ] = None,
    postpartum: Annotated[
        bool | None,
        Field(description="Whether the user is in the postpartum period. Triggers structured postpartum checks."),
    ] = None,
) -> dict[str, Any]:
    """Screen reported symptoms for emergency red flags.

    Runs three layers in order:
      1. adapter regex on free text + symptoms;
      2. structured pediatric / pregnancy / postpartum thresholds based on
         ``age``, ``pregnant``, ``postpartum`` (catches cases the regex set
         won't catch from free text alone);
      3. only if both adapter layers miss, the upstream toolkit's
         ``triageSymptoms`` is consulted.
    Any layer firing short-circuits the response to the escalation envelope.
    """
    if not CONFIG.adapter_enabled:
        return _disabled("doctor_red_flags")

    request_id = _audit.new_request_id()
    timer = CallTimer()
    args = {
        "symptoms": symptoms,
        "age": age,
        "sex": sex,
        "free_text": free_text,
        "pregnant": pregnant,
        "postpartum": postpartum,
    }

    triage_input = TriageInput(
        free_text=free_text or "",
        symptoms=tuple(s for s in symptoms if isinstance(s, str)),
        age_years=age,
        pregnant=pregnant,
        postpartum=postpartum,
    )
    matched = detect_red_flags(triage_input)

    if matched:
        guidance, next_steps = emergency_guidance(matched)
        env = EscalationEnvelope(
            tool="doctor_red_flags",
            matched_red_flags=matched,
            guidance=guidance,
            safe_next_steps=next_steps,
        )
        _emit(
            request_id=request_id,
            tool="doctor_red_flags",
            risk_level="high",
            timer=timer,
            matched=matched,
            upstream=None,
            blocked=[],
            args=args,
        )
        return _as_dict(env)

    upstream = _upstream.invoke(
        "triageSymptoms",
        {"age": age or 0, "sex": sex or "unknown", "symptoms": symptoms},
    )
    upstream_data: dict[str, Any] = upstream.data if isinstance(upstream.data, dict) else {}
    acuity = str(upstream_data.get("acuity", "routine") or "routine")
    next_steps_raw = list(upstream_data.get("nextSteps", []) or [])
    rules_raw = [str(r) for r in upstream_data.get("rulesMatched", []) or []]
    cleaned_steps, blocked_steps = filter_lines(next_steps_raw)
    cleaned_rules, blocked_rules = filter_lines(rules_raw)
    blocked = sorted(set(blocked_steps + blocked_rules))

    if acuity == "emergency":
        guidance, fallback_steps = emergency_guidance(cleaned_rules or ["upstream-flagged emergency"])
        env = EscalationEnvelope(
            tool="doctor_red_flags",
            matched_red_flags=cleaned_rules or ["upstream-flagged emergency"],
            guidance=guidance,
            safe_next_steps=cleaned_steps or fallback_steps,
            blocked_content=blocked,
        )
        _emit(
            request_id=request_id,
            tool="doctor_red_flags",
            risk_level="high",
            timer=timer,
            matched=cleaned_rules or ["upstream-flagged emergency"],
            upstream=upstream,
            blocked=blocked,
            args=args,
        )
        return _as_dict(env)

    result = RedFlagsResult(
        red_flag_detected=False,
        acuity=("urgent" if acuity == "urgent" else "routine"),
        matched_red_flags=cleaned_rules,
        guidance=(
            "I didn't spot an emergency red flag in what you described, but if "
            "anything changes quickly please reconsider seeking care."
        ),
        safe_next_steps=cleaned_steps
        or [
            "Watch for new or worsening symptoms.",
            "Contact your clinician if symptoms persist or you're unsure.",
        ],
        blocked_content=blocked,
        upstream_status=upstream.status,
    )
    _emit(
        request_id=request_id,
        tool="doctor_red_flags",
        risk_level="medium",
        timer=timer,
        matched=[],
        upstream=upstream,
        blocked=blocked,
        args=args,
    )
    return _as_dict(result)


# ── Tool 2: doctor_general_info ─────────────────────────────────────────────


@mcp.tool()
def doctor_general_info(
    topic: Annotated[
        str,
        Field(min_length=2, max_length=200, description="Health topic to summarise."),
    ],
    audience: Annotated[
        Literal["adult", "parent_of_child", "older_adult", "general"] | None,
        Field(description="Who the explanation is for."),
    ] = "general",
) -> dict[str, Any]:
    """Educational explanation of a health topic via `searchMedicalKB`."""
    if not CONFIG.adapter_enabled:
        return _disabled("doctor_general_info")

    request_id = _audit.new_request_id()
    timer = CallTimer()
    args = {"topic": topic, "audience": audience}

    upstream = _upstream.invoke("searchMedicalKB", {"query": topic, "limit": 3})
    data: dict[str, Any] = upstream.data if isinstance(upstream.data, dict) else {}
    hits = data.get("hits", []) or []

    summary_parts: list[str] = []
    educational_points: list[str] = []
    source_topics: list[str] = []
    blocked_all: list[str] = []
    seen_blocked: set[str] = set()

    for hit in hits:
        title = str(hit.get("title", "") or "").strip()
        snippet = str(hit.get("snippet", "") or "").strip()
        if title:
            source_topics.append(title)
        cleaned = filter_text(snippet)
        for cat in cleaned.blocked:
            if cat not in seen_blocked:
                blocked_all.append(cat)
                seen_blocked.add(cat)
        if cleaned.text:
            educational_points.append(cleaned.text)

    if educational_points:
        summary = " ".join(educational_points[:2])
    else:
        summary = (
            f"I don't have a confident summary on {topic} right now. A clinician or "
            "pharmacist can give a tailored answer."
        )

    when_to_seek_care = [
        "Symptoms worsen or do not improve as expected.",
        "New severe symptoms appear.",
        "You're unsure whether your situation needs urgent care.",
    ]

    result = GeneralInfoResult(
        topic=topic,
        summary=summary,
        educational_points=educational_points,
        when_to_seek_care=when_to_seek_care,
        source_topics=source_topics,
        safety_note="This is general information, not a diagnosis or treatment plan.",
        blocked_content=blocked_all,
        upstream_status=upstream.status,
    )
    _emit(
        request_id=request_id,
        tool="doctor_general_info",
        risk_level="medium",
        timer=timer,
        matched=[],
        upstream=upstream,
        blocked=blocked_all,
        args=args,
    )
    return _as_dict(result)


# ── Tool 3: doctor_self_care ────────────────────────────────────────────────


@mcp.tool()
def doctor_self_care(
    symptoms: Annotated[
        list[str],
        Field(min_length=1, max_length=20, description="Symptoms the user wants to manage."),
    ],
    age: Annotated[
        float | None,
        Field(ge=0, le=120, description="Age in years (fractional for under-1s)."),
    ] = None,
    free_text: Annotated[
        str | None,
        Field(max_length=2000, description="Optional context."),
    ] = None,
    pregnant: Annotated[
        bool | None,
        Field(description="Whether the user is currently pregnant. Triggers structured pregnancy checks."),
    ] = None,
    postpartum: Annotated[
        bool | None,
        Field(description="Whether the user is in the postpartum period. Triggers structured postpartum checks."),
    ] = None,
) -> dict[str, Any]:
    """General self-care guidance, gated on red-flag triage.

    Refuses to give self-care if any red flag is present — adapter regex,
    structured pediatric / pregnancy / postpartum thresholds, or upstream
    ``acuity == "emergency"``. The escalation envelope replaces the
    self-care payload in that case.
    """
    if not CONFIG.adapter_enabled:
        return _disabled("doctor_self_care")

    request_id = _audit.new_request_id()
    timer = CallTimer()
    args = {
        "symptoms": symptoms,
        "age": age,
        "free_text": free_text,
        "pregnant": pregnant,
        "postpartum": postpartum,
    }

    triage_input = TriageInput(
        free_text=free_text or "",
        symptoms=tuple(s for s in symptoms if isinstance(s, str)),
        age_years=age,
        pregnant=pregnant,
        postpartum=postpartum,
    )
    matched = detect_red_flags(triage_input)

    if matched:
        guidance, next_steps = emergency_guidance(matched)
        env = EscalationEnvelope(
            tool="doctor_self_care",
            matched_red_flags=matched,
            guidance=guidance,
            safe_next_steps=next_steps,
            blocked_content=["self_care_blocked_by_red_flag"],
        )
        _emit(
            request_id=request_id,
            tool="doctor_self_care",
            risk_level="high",
            timer=timer,
            matched=matched,
            upstream=None,
            blocked=["self_care_blocked_by_red_flag"],
            args=args,
        )
        return _as_dict(env)

    upstream = _upstream.invoke(
        "triageSymptoms",
        {"age": age or 0, "sex": "unknown", "symptoms": symptoms},
    )
    upstream_data: dict[str, Any] = upstream.data if isinstance(upstream.data, dict) else {}
    acuity = str(upstream_data.get("acuity", "routine") or "routine")

    if acuity == "emergency":
        rules_raw = [str(r) for r in upstream_data.get("rulesMatched", []) or []]
        cleaned_rules, blocked_rules = filter_lines(rules_raw)
        guidance, fallback_steps = emergency_guidance(cleaned_rules or ["upstream-flagged emergency"])
        env = EscalationEnvelope(
            tool="doctor_self_care",
            matched_red_flags=cleaned_rules or ["upstream-flagged emergency"],
            guidance=guidance,
            safe_next_steps=fallback_steps,
            blocked_content=sorted(
                set(blocked_rules + ["self_care_blocked_by_red_flag"])
            ),
        )
        _emit(
            request_id=request_id,
            tool="doctor_self_care",
            risk_level="high",
            timer=timer,
            matched=cleaned_rules,
            upstream=upstream,
            blocked=["self_care_blocked_by_red_flag"],
            args=args,
        )
        return _as_dict(env)

    result = SelfCareResult(
        red_flag_detected=False,
        acuity=("urgent" if acuity == "urgent" else "routine"),
        general_self_care=[
            "Rest as much as you reasonably can.",
            "Stay hydrated unless a clinician has told you to restrict fluids.",
            "Monitor symptoms over the next 24-48 hours.",
            "Avoid pushing through severe pain, dizziness, or new symptoms.",
        ],
        seek_care_if=[
            "Symptoms worsen or persist beyond a few days.",
            "New severe symptoms appear.",
            "You feel unsure whether the situation is urgent.",
        ],
        safety_note=(
            "Self-care guidance is general and may not apply to your individual "
            "situation. A clinician or pharmacist can tailor it to you."
        ),
        upstream_status=upstream.status,
    )
    _emit(
        request_id=request_id,
        tool="doctor_self_care",
        risk_level="medium",
        timer=timer,
        matched=[],
        upstream=upstream,
        blocked=[],
        args=args,
    )
    return _as_dict(result)


# ── Entry point ─────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mcp-general-doctor")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse", "legacy-http", "hybrid"],
        default=CONFIG.transport,
        help=(
            "stdio (Inspector / local), streamable-http (canonical MCP), sse "
            "(legacy MCP transport), legacy-http (REST + /context-forge/call "
            "for older HomePilot deployments), hybrid (FastMCP /mcp + legacy "
            "REST in one process)."
        ),
    )
    parser.add_argument("--host", default=CONFIG.host)
    parser.add_argument("--port", type=int, default=CONFIG.port)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log.info(
        "starting mcp-general-doctor transport=%s host=%s port=%s adapter_enabled=%s upstream=%s",
        args.transport,
        args.host,
        args.port,
        CONFIG.adapter_enabled,
        CONFIG.upstream_url,
    )

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    elif args.transport == "legacy-http":
        from .legacy_http import run_legacy_http

        run_legacy_http(args.host, args.port)
    elif args.transport == "hybrid":
        from .legacy_http import run_hybrid

        run_hybrid(args.host, args.port)
    else:  # streamable-http (canonical)
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    sys.exit(main())
