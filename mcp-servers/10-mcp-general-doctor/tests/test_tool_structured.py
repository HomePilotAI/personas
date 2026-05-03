"""End-to-end tests that the structured fields flow through the FastMCP tools."""

from __future__ import annotations


def test_red_flags_via_age_and_pregnant_short_circuits(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_red_flags",
        symptoms=["bleeding"],
        age=28,
        free_text="some bleeding today",
        pregnant=True,
    )
    assert out["escalated"] is True
    assert any("pregnancy" in m or "fetal" in m for m in out["matched_red_flags"])
    # No upstream call when the structured layer fires.
    assert fake_upstream.calls == []


def test_self_care_refuses_for_pregnant_user_with_bleeding(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_self_care",
        symptoms=["bleeding"],
        free_text="some bleeding",
        pregnant=True,
    )
    assert out["escalated"] is True
    assert "self_care_blocked_by_red_flag" in out["blocked_content"]
    assert fake_upstream.calls == []


def test_red_flags_for_under_3mo_with_fever_escalates(fake_upstream, call_tool) -> None:
    # Under 3 months: any fever is an ER trigger per AAP guidance, even without
    # the word "infant" anywhere. Caller passed age=0.2 (≈ 2.4 months).
    out = call_tool(
        "doctor_red_flags",
        symptoms=["fever"],
        age=0.2,
        free_text="my child has fever 38.5C",
    )
    assert out["escalated"] is True
    assert any("infant fever" in m for m in out["matched_red_flags"])


def test_red_flags_for_3yo_high_fever_104f_escalates(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_red_flags",
        symptoms=["fever"],
        age=3,
        free_text="temperature reading 104 F",
    )
    assert out["escalated"] is True
    assert any("high fever" in m for m in out["matched_red_flags"])


def test_red_flags_for_postpartum_heavy_bleeding(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_red_flags",
        symptoms=["bleeding"],
        free_text="I'm soaking through pads every hour",
        postpartum=True,
    )
    assert out["escalated"] is True
    assert any("postpartum" in m for m in out["matched_red_flags"])


def test_red_flags_default_emergency_mentions_112_and_911(fake_upstream, call_tool) -> None:
    out = call_tool(
        "doctor_red_flags",
        symptoms=["chest pain"],
        free_text="severe chest pain radiating to my arm",
    )
    assert out["escalated"] is True
    guidance = out["guidance"]
    for n in ["112", "911", "999"]:
        assert n in guidance
