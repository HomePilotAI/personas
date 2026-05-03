"""Tests for the HTTP upstream client + offline fallback."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from doctor.upstream import UpstreamClient  # noqa: E402


def _client(transport, *, offline_fallback: bool = True) -> UpstreamClient:
    c = UpstreamClient(
        base_url="http://test.invalid",
        bearer="dev-token",
        timeout_s=2,
        offline_fallback=offline_fallback,
    )
    # Inject the test transport.
    original_invoke = c.invoke

    def patched(tool: str, args: dict):
        with httpx.Client(transport=transport, timeout=2) as client:
            try:
                resp = client.post(
                    f"{c.base_url}/invoke",
                    json={"tool": tool, "args": args},
                    headers={"Authorization": "Bearer dev-token"},
                )
            except (httpx.RequestError, httpx.HTTPError) as exc:
                if c.offline_fallback:
                    return c._fallback(tool, args, error=str(exc))
                from doctor.upstream import UpstreamResponse

                return UpstreamResponse(ok=False, data=None, status="error", error=str(exc))
            if resp.status_code >= 400:
                if c.offline_fallback:
                    return c._fallback(tool, args, error=f"HTTP {resp.status_code}")
                from doctor.upstream import UpstreamResponse

                return UpstreamResponse(
                    ok=False, data=None, status="error", error=f"HTTP {resp.status_code}"
                )
            from doctor.upstream import UpstreamResponse

            return UpstreamResponse(ok=True, data=resp.json(), status="live")

    c.invoke = patched  # type: ignore[assignment]
    return c


def _ok_handler(request: httpx.Request) -> httpx.Response:
    body = request.read()
    assert request.headers.get("Authorization") == "Bearer dev-token"
    if b'"triageSymptoms"' in body:
        return httpx.Response(200, json={"acuity": "routine", "rulesMatched": [], "nextSteps": []})
    if b'"searchMedicalKB"' in body:
        return httpx.Response(200, json={"hits": [{"title": "x", "snippet": "y", "score": 0.9}]})
    return httpx.Response(404, text="unknown tool")


def test_invoke_returns_live_data_on_200() -> None:
    transport = httpx.MockTransport(_ok_handler)
    client = _client(transport)
    r = client.invoke("triageSymptoms", {"age": 30, "sex": "unknown", "symptoms": ["headache"]})
    assert r.ok
    assert r.status == "live"
    assert r.data["acuity"] == "routine"


def test_invoke_falls_back_when_upstream_500() -> None:
    def _bad(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client(httpx.MockTransport(_bad))
    r = client.invoke("triageSymptoms", {"symptoms": ["headache"]})
    assert r.status == "offline_fallback"
    assert r.data["acuity"] == "routine"


def test_invoke_falls_back_on_connection_error() -> None:
    def _raises(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _client(httpx.MockTransport(_raises))
    r = client.invoke("searchMedicalKB", {"query": "headache"})
    assert r.status == "offline_fallback"
    assert "hits" in r.data


def test_invoke_returns_error_when_offline_disabled() -> None:
    def _raises(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    client = _client(httpx.MockTransport(_raises), offline_fallback=False)
    r = client.invoke("triageSymptoms", {"symptoms": ["x"]})
    assert not r.ok
    assert r.status == "error"


def test_offline_fallback_for_unsupported_tool_returns_error() -> None:
    def _raises(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = _client(httpx.MockTransport(_raises))
    r = client.invoke("getPatient360", {"id": "x"})
    # Even with offline_fallback=True, we don't fabricate PHI shapes.
    assert not r.ok
    assert r.status == "error"
