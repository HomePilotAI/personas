"""Tests for the process-global rate limiter."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from researcher import rate_limit  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_limiter():
    rate_limit._reset_for_tests()
    yield
    rate_limit._reset_for_tests()


def test_unconfigured_source_does_not_block() -> None:
    waited = rate_limit.acquire("unconfigured")
    assert waited == 0.0
    stats = rate_limit.stats()
    assert stats["total_acquires"] >= 1
    assert stats["total_waits_seconds"] == 0.0


def test_configured_source_blocks_until_min_interval_passes() -> None:
    # 0.2s interval to keep the test fast.
    rate_limit.configure("arxiv", 0.2)
    rate_limit.acquire("arxiv")  # primes the bucket
    start = time.monotonic()
    waited = rate_limit.acquire("arxiv")
    elapsed = time.monotonic() - start
    assert waited > 0.0
    assert elapsed >= 0.18  # allow ~10% jitter
    assert rate_limit.stats()["total_waits_seconds"] >= waited - 0.01


def test_concurrent_acquires_serialize_correctly() -> None:
    """Two threads racing must not both fire inside the min interval."""
    rate_limit.configure("arxiv", 0.15)
    rate_limit.acquire("arxiv")  # prime
    timings: list[float] = []
    barrier = threading.Barrier(2)

    def worker() -> None:
        barrier.wait()
        rate_limit.acquire("arxiv")
        timings.append(time.monotonic())

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    timings.sort()
    delta = timings[1] - timings[0]
    assert delta >= 0.13, f"two threads fired within {delta:.3f}s of each other"


def test_configure_clamps_negative_to_zero() -> None:
    rate_limit.configure("arxiv", -5.0)
    waited = rate_limit.acquire("arxiv")
    assert waited == 0.0
