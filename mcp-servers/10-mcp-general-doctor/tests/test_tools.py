"""End-to-end tests for the three canonical tools using a fake upstream."""

from __future__ import annotations


def test_red_flags_short_circuits_without_upstream_call(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_red_flags",
        symptoms=["chest pain", "sweating"],
        age=55,
        free_text="severe chest pain radiating to my arm, very sweaty",
    )
    assert out["escalated"] is True
    assert out["acuity"] == "emergency"
    assert any("chest pain" in m for m in out["matched_red_flags"])
    assert "Seek emergency care" in out["guidance"] or "emergency number" in out["guidance"]
    # No upstream call when adapter detects the emergency.
    assert fake_upstream.calls == []


def test_red_flags_routine_path_calls_upstream_and_filters_clinical_orders(
    fake_upstream, call_tool
) -> None:
    fake_upstream.responses["triageSymptoms"] = {
        "acuity": "routine",
        "rulesMatched": [],
        "nextSteps": ["ECG / troponin", "Stay hydrated and rest"],
    }
    out = call_tool("doctor_red_flags", symptoms=["headache"], age=30)
    assert out["red_flag_detected"] is False
    assert out["acuity"] in {"routine", "urgent"}
    # The clinical-order line is rewritten; the benign one survives.
    assert all("troponin" not in s.lower() for s in out["safe_next_steps"])
    assert any("hydrated" in s.lower() for s in out["safe_next_steps"])
    assert "clinical_orders" in out["blocked_content"]
    assert ("triageSymptoms", {"age": 30, "sex": "unknown", "symptoms": ["headache"]}) in fake_upstream.calls


def test_red_flags_upstream_emergency_promotes_to_escalation(fake_upstream, call_tool) -> None:
    fake_upstream.responses["triageSymptoms"] = {
        "acuity": "emergency",
        "rulesMatched": ["chest pain", "diaphoresis"],
        "nextSteps": ["ECG", "troponin", "aspirin if not contraindicated"],
    }
    # Adapter regex misses (we phrase the user input deliberately benign).
    out = call_tool("doctor_red_flags", symptoms=["pressure feeling"], age=60)
    assert out["escalated"] is True
    assert "clinical_orders" in out["blocked_content"]


def test_general_info_strips_diagnostic_and_dosing_snippets(fake_upstream, call_tool) -> None:
    fake_upstream.responses["searchMedicalKB"] = {
        "hits": [
            {"title": "Headache overview", "snippet": "Take 500 mg of paracetamol every 4 hours.", "score": 0.9},
            {"title": "When to seek care", "snippet": "Most headaches resolve with rest and hydration.", "score": 0.8},
        ]
    }
    out = call_tool("doctor_general_info", topic="headache")
    assert out["topic"] == "headache"
    assert "Headache overview" in out["source_topics"]
    assert all("500 mg" not in p for p in out["educational_points"])
    assert "medication_dosing" in out["blocked_content"]
    assert any("rest" in p.lower() for p in out["educational_points"])


def test_general_info_handles_empty_kb_gracefully(fake_upstream, call_tool) -> None:
    fake_upstream.responses["searchMedicalKB"] = {"hits": []}
    out = call_tool("doctor_general_info", topic="rare-thing-no-kb")
    assert "rare-thing-no-kb" in out["summary"]
    assert out["educational_points"] == []
    assert out["safety_note"]


def test_self_care_refuses_when_red_flag_in_user_text(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_self_care",
        symptoms=["fatigue"],
        free_text="my partner just passed out and isn't responding",
    )
    assert out["escalated"] is True
    assert "self_care_blocked_by_red_flag" in out["blocked_content"]
    assert fake_upstream.calls == []  # never went upstream


def test_self_care_returns_safe_guidance_when_no_red_flags(fake_upstream, call_tool) -> None:
    fake_upstream.responses["triageSymptoms"] = {
        "acuity": "routine",
        "rulesMatched": [],
        "nextSteps": [],
    }
    out = call_tool("doctor_self_care", symptoms=["mild headache"], age=30)
    assert out["red_flag_detected"] is False
    assert any("rest" in s.lower() for s in out["general_self_care"])
    assert any("hydrated" in s.lower() for s in out["general_self_care"])
    assert any("worsen" in s.lower() for s in out["seek_care_if"])
    assert "blocked_content" in out


def test_self_care_promoted_to_escalation_on_upstream_emergency(fake_upstream, call_tool) -> None:
    fake_upstream.responses["triageSymptoms"] = {
        "acuity": "emergency",
        "rulesMatched": ["something_clinical"],
        "nextSteps": ["ECG", "troponin"],
    }
    out = call_tool("doctor_self_care", symptoms=["odd pressure feeling"], age=70)
    assert out["escalated"] is True
    assert "self_care_blocked_by_red_flag" in out["blocked_content"]


def test_disclaimer_present_on_every_response_shape(fake_upstream, call_tool) -> None:
    fake_upstream.responses["triageSymptoms"] = {"acuity": "routine", "rulesMatched": [], "nextSteps": []}
    fake_upstream.responses["searchMedicalKB"] = {"hits": []}
    expected = "consult a healthcare professional"
    for tool, kwargs in [
        ("doctor_red_flags", {"symptoms": ["headache"]}),
        ("doctor_general_info", {"topic": "headache"}),
        ("doctor_self_care", {"symptoms": ["mild fatigue"]}),
    ]:
        out = call_tool(tool, **kwargs)
        assert expected in out["disclaimer"]


def test_adapter_disabled_returns_typed_envelope(monkeypatch, call_tool) -> None:
    import dataclasses

    import doctor.server as srv

    # Flip the runtime flag to simulate rollback. CONFIG is a frozen
    # dataclass, so we replace it with a copy carrying adapter_enabled=False.
    monkeypatch.setattr(srv, "CONFIG", dataclasses.replace(srv.CONFIG, adapter_enabled=False))
    out = call_tool("doctor_red_flags", symptoms=["headache"])
    assert out["adapter_enabled"] is False
    assert "currently disabled" in out["message"].lower()
