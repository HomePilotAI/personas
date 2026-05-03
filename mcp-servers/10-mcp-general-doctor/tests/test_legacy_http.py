"""Tests for the legacy HTTP / Context Forge compatibility surface."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def legacy_client(fake_upstream):  # noqa: ARG001  - fixture wires the upstream
    """Boot the legacy FastAPI app and return a TestClient against it."""
    pytest.importorskip("fastapi")
    pytest.importorskip("starlette")
    from fastapi.testclient import TestClient

    from doctor.legacy_http import build_legacy_app

    app = build_legacy_app()
    return TestClient(app)


def test_health_endpoint(legacy_client) -> None:
    r = legacy_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["server"] == "mcp-general-doctor"


def test_tools_endpoint_lists_canonical_three(legacy_client) -> None:
    r = legacy_client.get("/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert names == {"doctor_red_flags", "doctor_general_info", "doctor_self_care"}


def test_post_red_flags_short_circuits(legacy_client) -> None:
    r = legacy_client.post(
        "/doctor_red_flags",
        json={
            "symptoms": ["chest pain", "sweating"],
            "age": 55,
            "free_text": "severe chest pain radiating to my arm",
        },
    )
    assert r.status_code == 200
    payload = r.json()["result"]
    assert payload["escalated"] is True
    assert any("chest pain" in m for m in payload["matched_red_flags"])


def test_post_general_info_filters_clinical_orders(legacy_client, fake_upstream) -> None:
    fake_upstream.responses["searchMedicalKB"] = {
        "hits": [
            {"title": "headache", "snippet": "Take 500 mg of paracetamol every 4 hours."},
            {"title": "rest", "snippet": "Most headaches resolve with rest and hydration."},
        ]
    }
    r = legacy_client.post("/doctor_general_info", json={"topic": "headache"})
    assert r.status_code == 200
    payload = r.json()["result"]
    assert all("500 mg" not in p for p in payload["educational_points"])
    assert "medication_dosing" in payload["blocked_content"]


def test_post_self_care_refuses_on_red_flag(legacy_client) -> None:
    r = legacy_client.post(
        "/doctor_self_care",
        json={"symptoms": ["fatigue"], "free_text": "I want to end my life"},
    )
    payload = r.json()["result"]
    assert payload["escalated"] is True
    assert "self_care_blocked_by_red_flag" in payload["blocked_content"]


def test_legacy_post_silently_drops_unknown_fields(legacy_client) -> None:
    """Legacy callers sometimes attach session ids / metadata; we ignore them."""
    r = legacy_client.post(
        "/doctor_red_flags",
        json={
            "symptoms": ["headache"],
            "session_id": "abc-123",  # not a tool field
            "extra_metadata": {"source": "legacy-client"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "result" in body
    # Whatever the inner shape is, it must NOT echo the session id back.
    assert "abc-123" not in r.text


def test_context_forge_tools_endpoint(legacy_client) -> None:
    r = legacy_client.get("/context-forge/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert names == {"doctor_red_flags", "doctor_general_info", "doctor_self_care"}


def test_context_forge_call_dispatches_to_red_flags(legacy_client) -> None:
    r = legacy_client.post(
        "/context-forge/call",
        json={
            "tool": "doctor_red_flags",
            "arguments": {"symptoms": ["chest pain", "sweating"], "free_text": "chest pain radiating to arm"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tool"] == "doctor_red_flags"
    assert body["result"]["escalated"] is True


def test_context_forge_call_rejects_unknown_tool(legacy_client) -> None:
    r = legacy_client.post(
        "/context-forge/call",
        json={"tool": "doctor_secret_admin_tool", "arguments": {}},
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "INVALID_TOOL"
