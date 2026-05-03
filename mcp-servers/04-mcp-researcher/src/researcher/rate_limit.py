"""Process-global rate limiter for outbound source-API calls.

The arXiv terms of use cap legacy API users at **one request per three
seconds, single-connection**. We enforce that globally inside the
process — every `arxiv_client.search()` call (and any future arXiv read
path) goes through ``acquire("arxiv")``. Multiple FastMCP workers in the
same process share the same lock; multiple processes need an external
limiter (Redis token bucket) which is out of scope for this server today.

Other connectors will register their own min-interval here as they land
(OpenAlex, Crossref, NCBI E-utilities, NASA ADS, OSTI). The default
(0.0 s) is "no rate limit" so unregistered connectors don't sleep.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

log = logging.getLogger("mcp-researcher.rate_limit")


@dataclass
class _Bucket:
    min_seconds_between: float
    last_call_at: float = 0.0
    lock: threading.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.lock is None:
            self.lock = threading.Lock()


class GlobalRateLimiter:
    """Process-wide per-source rate limiter (single-instance only)."""

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._registry_lock = threading.Lock()
        self.total_waits_seconds: float = 0.0
        self.total_acquires: int = 0

    def configure(self, source: str, min_seconds_between: float) -> None:
        """Register or update a source's minimum interval."""
        with self._registry_lock:
            if source in self._buckets:
                self._buckets[source].min_seconds_between = max(
                    0.0, float(min_seconds_between)
                )
            else:
                self._buckets[source] = _Bucket(
                    min_seconds_between=max(0.0, float(min_seconds_between))
                )

    def acquire(self, source: str) -> float:
        """Block until ``source`` is allowed to fire again. Returns waited seconds."""
        bucket = self._buckets.get(source)
        if bucket is None or bucket.min_seconds_between <= 0:
            self.total_acquires += 1
            return 0.0
        with bucket.lock:
            now = time.monotonic()
            elapsed = now - bucket.last_call_at
            wait = bucket.min_seconds_between - elapsed
            if wait > 0:
                log.debug("rate_limit %s sleeping %.3fs", source, wait)
                time.sleep(wait)
                self.total_waits_seconds += wait
                bucket.last_call_at = time.monotonic()
            else:
                bucket.last_call_at = now
            self.total_acquires += 1
            return max(0.0, wait)

    def stats(self) -> dict[str, float]:
        return {
            "total_acquires": float(self.total_acquires),
            "total_waits_seconds": round(self.total_waits_seconds, 3),
            "registered_sources": float(len(self._buckets)),
        }


# Module-level singleton — every call site uses the same limiter.
_LIMITER = GlobalRateLimiter()


def configure(source: str, min_seconds_between: float) -> None:
    _LIMITER.configure(source, min_seconds_between)


def acquire(source: str) -> float:
    return _LIMITER.acquire(source)


def stats() -> dict[str, float]:
    return _LIMITER.stats()


def _reset_for_tests() -> None:
    """Wipe the global state. Tests only — never call from production code."""
    global _LIMITER
    _LIMITER = GlobalRateLimiter()
