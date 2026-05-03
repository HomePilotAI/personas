"""Audit-logging tests — no PHI escapes, hash digest is stable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doctor.audit import (  # noqa: E402
    AuditEvent,
    AuditLogger,
    CallTimer,
    hash_input,
    maybe_hash,
    safe_input_summary,
)


def test_hash_input_is_stable_and_one_way() -> None:
    a = hash_input("chest pain")
    b = hash_input("chest pain")
    c = hash_input("chest pain ")
    assert a == b
    assert a != c
    assert len(a) == 64  # sha256 hex


def test_maybe_hash_respects_flag() -> None:
    assert maybe_hash("hello", enabled=False) is None
    assert maybe_hash("hello", enabled=True) is not None


def test_safe_input_summary_only_pulls_known_text_fields() -> None:
    s = safe_input_summary({"symptoms": ["chest pain"], "age": 55, "sex": "male", "topic": "x"})
    assert "chest pain" in s
    assert "x" in s
    # Numeric/enum fields aren't in the digest.
    assert "55" not in s
    assert "male" not in s


def test_audit_event_serialises_to_json_without_raw_text(tmp_path) -> None:
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path=str(log_path), hash_user_input=True)
    timer = CallTimer()
    event = AuditEvent(
        request_id="abc123",
        timestamp=logger.now_iso(),
        tool="doctor_red_flags",
        risk_level="high",
        red_flag_detected=True,
        matched_red_flags=["chest pain"],
        upstream_tool="triageSymptoms",
        upstream_status="live",
        blocked_categories=["clinical_orders"],
        latency_ms=timer.elapsed_ms(),
        user_input_sha256=hash_input("chest pain radiating to arm"),
    )
    logger.emit(event)
    line = log_path.read_text().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["tool"] == "doctor_red_flags"
    assert payload["red_flag_detected"] is True
    assert payload["matched_red_flags"] == ["chest pain"]
    # PHI / raw text never appears.
    assert "chest pain radiating" not in line
    assert payload["user_input_sha256"] and len(payload["user_input_sha256"]) == 64
