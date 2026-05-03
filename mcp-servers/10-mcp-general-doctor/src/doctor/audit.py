"""No-PHI audit logging for the General Doctor adapter.

Logs structured event records (one JSON object per line) covering tool name,
risk level, red-flag detection, blocked-content categories, upstream status,
latency, and any error type. **Raw user health text never goes through this
module unhashed**; if `hash_user_input` is on, callers pass a SHA-256 of the
input and we log the digest — not the input.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("mcp-general-doctor.audit")


def hash_input(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AuditEvent:
    request_id: str
    timestamp: str
    tool: str
    risk_level: str
    red_flag_detected: bool
    matched_red_flags: list[str] = field(default_factory=list)
    upstream_tool: str | None = None
    upstream_status: str | None = None
    blocked_categories: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error_type: str | None = None
    user_input_sha256: str | None = None

    def to_json(self) -> str:
        payload = {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "tool": self.tool,
            "risk_level": self.risk_level,
            "red_flag_detected": self.red_flag_detected,
            "matched_red_flags": self.matched_red_flags,
            "upstream_tool": self.upstream_tool,
            "upstream_status": self.upstream_status,
            "blocked_categories": self.blocked_categories,
            "latency_ms": round(self.latency_ms, 2),
            "error_type": self.error_type,
            "user_input_sha256": self.user_input_sha256,
        }
        return json.dumps(payload, ensure_ascii=False)


class AuditLogger:
    def __init__(self, *, log_path: str | None, hash_user_input: bool) -> None:
        self.log_path: Path | None = Path(log_path) if log_path else None
        self.hash_user_input = hash_user_input

    def new_request_id(self) -> str:
        return uuid.uuid4().hex[:16]

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def emit(self, event: AuditEvent) -> None:
        line = event.to_json()
        if self.log_path is None:
            # Default: stderr so stdout (MCP transport) stays clean.
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:  # pragma: no cover
            log.warning("failed to write audit log to %s: %s", self.log_path, exc)


@dataclass
class CallTimer:
    started_at: float = field(default_factory=time.perf_counter)

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.started_at) * 1000.0


def maybe_hash(value: str | None, *, enabled: bool) -> str | None:
    if not enabled:
        return None
    return hash_input(value)


def safe_input_summary(args: dict[str, Any]) -> str:
    """Concatenate user-facing free-text fields for a single hash digest.

    We deliberately do NOT include numeric / structured fields (age, sex,
    enums) which would weaken the hash without adding signal.
    """
    parts: list[str] = []
    for key in ("symptoms", "topic", "context", "free_text"):
        v = args.get(key)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)
