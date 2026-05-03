"""No-PHI / no-raw-text audit logging for the Researcher MCP.

Mirrors the General Doctor audit pattern: one JSON line per tool call,
written to stderr (default) or to ``RESEARCHER_AUDIT_LOG_PATH``. Raw user
queries / abstracts / paper text NEVER appear in the log; the input is
hashed (SHA-256, first 32 chars) when ``hash_user_input`` is true.

Fields per event:

  request_id          — opaque correlation id
  timestamp           — ISO 8601 UTC
  tool                — MCP tool name
  domain              — best-effort domain classification (nuclear / aerospace
                        / robotics / biomedical / chemistry / general)
  sources_consulted   — list of SourceTag values
  papers_examined     — count
  blocked_categories  — dual-use refusal categories that fired
  blocked_sources     — count of source-policy refusals
  rate_limit_wait_ms  — total time spent waiting on rate limiters
  latency_ms          — wall time of the call
  error_type          — exception class name on failure
  user_input_sha256   — only when audit_hash_user_input=true
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

log = logging.getLogger("mcp-researcher.audit")


def hash_input(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AuditEvent:
    request_id: str
    timestamp: str
    tool: str
    domain: str = "general"
    sources_consulted: list[str] = field(default_factory=list)
    papers_examined: int = 0
    blocked_categories: list[str] = field(default_factory=list)
    blocked_sources: int = 0
    rate_limit_wait_ms: float = 0.0
    latency_ms: float = 0.0
    error_type: str | None = None
    user_input_sha256: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "request_id": self.request_id,
                "timestamp": self.timestamp,
                "tool": self.tool,
                "domain": self.domain,
                "sources_consulted": self.sources_consulted,
                "papers_examined": self.papers_examined,
                "blocked_categories": self.blocked_categories,
                "blocked_sources": self.blocked_sources,
                "rate_limit_wait_ms": round(self.rate_limit_wait_ms, 2),
                "latency_ms": round(self.latency_ms, 2),
                "error_type": self.error_type,
                "user_input_sha256": self.user_input_sha256,
            },
            ensure_ascii=False,
        )


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

    Numeric / structured fields are deliberately excluded — they would
    weaken the digest without adding signal.
    """
    parts: list[str] = []
    for key in ("query", "topic", "context", "free_text"):
        v = args.get(key)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif isinstance(v, str):
            parts.append(v)
    return "\n".join(parts)
