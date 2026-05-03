"""Pydantic response shapes returned by every adapter tool.

Every output starts with the same disclaimer string, includes a ``tool``
field, and lists ``blocked_content`` so the caller can verify what the
safety gateway refused to surface.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = (
    "I can share general information, but please consult a healthcare "
    "professional for personal medical advice."
)

Acuity = Literal["routine", "urgent", "emergency", "unknown"]


class RedFlagsResult(BaseModel):
    disclaimer: str = DISCLAIMER
    tool: Literal["doctor_red_flags"] = "doctor_red_flags"
    red_flag_detected: bool
    acuity: Acuity
    matched_red_flags: list[str] = Field(default_factory=list)
    guidance: str
    safe_next_steps: list[str] = Field(default_factory=list)
    blocked_content: list[str] = Field(default_factory=list)
    upstream_status: Literal["live", "offline_fallback", "error"] = "live"


class GeneralInfoResult(BaseModel):
    disclaimer: str = DISCLAIMER
    tool: Literal["doctor_general_info"] = "doctor_general_info"
    topic: str
    summary: str
    educational_points: list[str] = Field(default_factory=list)
    when_to_seek_care: list[str] = Field(default_factory=list)
    source_topics: list[str] = Field(default_factory=list)
    safety_note: str
    blocked_content: list[str] = Field(default_factory=list)
    upstream_status: Literal["live", "offline_fallback", "error"] = "live"


class SelfCareResult(BaseModel):
    disclaimer: str = DISCLAIMER
    tool: Literal["doctor_self_care"] = "doctor_self_care"
    red_flag_detected: bool
    acuity: Acuity
    general_self_care: list[str] = Field(default_factory=list)
    seek_care_if: list[str] = Field(default_factory=list)
    safety_note: str
    blocked_content: list[str] = Field(default_factory=list)
    upstream_status: Literal["live", "offline_fallback", "error"] = "live"


class EscalationEnvelope(BaseModel):
    """Returned in place of any other shape when an emergency is detected.

    Keeping it as a sibling type rather than a flag means a caller that wants
    to short-circuit the rest of a session can branch on the ``escalated``
    field without parsing the inner result type.
    """

    disclaimer: str = DISCLAIMER
    tool: str
    escalated: Literal[True] = True
    acuity: Literal["emergency"] = "emergency"
    red_flag_detected: Literal[True] = True
    matched_red_flags: list[str]
    guidance: str
    safe_next_steps: list[str]
    blocked_content: list[str] = Field(default_factory=list)


class AdapterDisabledResult(BaseModel):
    disclaimer: str = DISCLAIMER
    tool: str
    adapter_enabled: Literal[False] = False
    message: str = (
        "The General Doctor adapter is currently disabled "
        "(GENERAL_DOCTOR_ADAPTER_ENABLED=false). Please contact a healthcare "
        "professional for any health concerns; this companion is offline."
    )
