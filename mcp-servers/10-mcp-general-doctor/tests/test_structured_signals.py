"""Tests for the structured pediatric / pregnancy / postpartum red-flag layer.

These cases catch the gaps the external review flagged: an 8-month-old with
"fever" but without the word "infant" anywhere; a pregnant user reporting
bleeding without writing "while pregnant"; etc.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doctor.safety import (  # noqa: E402
    TriageInput,
    _extract_temperature_celsius,
    detect_red_flags,
    emergency_guidance,
)


# ── Pediatric ──────────────────────────────────────────────────────────────


def test_under_3mo_with_fever_word_escalates_without_infant_text() -> None:
    out = detect_red_flags(
        TriageInput(free_text="my child has fever today", symptoms=("fever",), age_years=0.1)
    )
    assert any("infant fever (age <3 months)" in m for m in out)


def test_under_3mo_with_explicit_temperature_38c_escalates() -> None:
    out = detect_red_flags(
        TriageInput(
            free_text="temperature is 38.2 C and they seem warm",
            symptoms=(),
            age_years=0.15,
        )
    )
    assert any("infant fever" in m for m in out)


def test_18mo_with_temp_39c_high_fever_in_young_child() -> None:
    out = detect_red_flags(
        TriageInput(free_text="temp 39.5C since this morning", age_years=1.5)
    )
    assert any("high fever in young child" in m for m in out)


def test_18mo_with_104f_high_fever_in_young_child() -> None:
    out = detect_red_flags(
        TriageInput(free_text="temperature reading 104 F", age_years=1.5)
    )
    assert any("high fever in young child" in m for m in out)


def test_3yo_with_breathing_difficulty() -> None:
    out = detect_red_flags(
        TriageInput(
            free_text="he has had difficulty breathing and is wheezing",
            age_years=3,
        )
    )
    assert any("breathing difficulty in young child" in m for m in out)


def test_3yo_lethargic_or_unresponsive() -> None:
    for txt in ["she is lethargic and won't wake up", "child is unresponsive"]:
        out = detect_red_flags(TriageInput(free_text=txt, age_years=3))
        assert any("lethargy in young child" in m for m in out), f"missed: {txt}"


def test_2yo_with_blue_lips_cyanosis() -> None:
    out = detect_red_flags(
        TriageInput(free_text="lips look blue around the mouth", age_years=2)
    )
    assert any("cyanosis in young child" in m for m in out)


def test_adult_with_temp_39c_does_not_trigger_pediatric() -> None:
    out = detect_red_flags(TriageInput(free_text="I have a fever 39C", age_years=35))
    pediatric_hits = [m for m in out if "young child" in m or "infant" in m]
    assert pediatric_hits == []


def test_extract_temperature_handles_common_formats() -> None:
    cases = [
        ("temp 38.5 C", 38.5),
        ("temperature is 39C this morning", 39.0),
        ("104 F", (104 - 32) * 5 / 9),
        ("temp 40°C", 40.0),
    ]
    for text, expected in cases:
        got = _extract_temperature_celsius(text)
        assert got is not None and abs(got - expected) < 0.05, (text, got, expected)


def test_extract_temperature_ignores_dose_strings() -> None:
    # "100 mg" should NOT be read as 100°.
    assert _extract_temperature_celsius("Take 100 mg every 4h") is None
    assert _extract_temperature_celsius("100 mg") is None


# ── Pregnancy ──────────────────────────────────────────────────────────────


def test_pregnant_true_with_bleeding_word_escalates() -> None:
    out = detect_red_flags(
        TriageInput(free_text="I have some bleeding today", pregnant=True)
    )
    assert any("pregnancy bleeding (structured)" in m for m in out)


def test_pregnant_true_with_severe_pain_escalates() -> None:
    out = detect_red_flags(
        TriageInput(free_text="severe abdominal pain since this morning", pregnant=True)
    )
    assert any("severe pregnancy pain (structured)" in m for m in out)


def test_pregnant_true_with_decreased_movement_escalates() -> None:
    for text in [
        "fewer kicks than usual today",
        "no fetal movement since last night",
        "decreased movement",
    ]:
        out = detect_red_flags(TriageInput(free_text=text, pregnant=True))
        assert any("decreased fetal movement (structured)" in m for m in out), text


def test_pregnant_false_with_bleeding_does_not_escalate_pregnancy() -> None:
    out = detect_red_flags(
        TriageInput(free_text="minor bleeding from a paper cut", pregnant=False)
    )
    pregnancy_hits = [m for m in out if "pregnancy" in m or "fetal" in m]
    assert pregnancy_hits == []


def test_pregnant_unset_falls_back_to_regex_only() -> None:
    # The free-text regex still catches "while pregnant ... bleeding".
    out_regex = detect_red_flags(
        TriageInput(free_text="while pregnant I have bleeding")
    )
    assert any("pregnancy bleeding" in m for m in out_regex)
    # But without the trigger word and without pregnant=True, no escalation.
    out_none = detect_red_flags(TriageInput(free_text="some bleeding"))
    assert all("pregnancy" not in m for m in out_none)


# ── Postpartum ─────────────────────────────────────────────────────────────


def test_postpartum_true_with_heavy_bleeding_escalates() -> None:
    for text in [
        "soaking through pads every hour",
        "heavy bleeding two weeks after delivery",
        "haemorrhage postpartum",
    ]:
        out = detect_red_flags(TriageInput(free_text=text, postpartum=True))
        assert any("postpartum hemorrhage (structured)" in m for m in out), text


def test_postpartum_true_with_swollen_leg_escalates() -> None:
    out = detect_red_flags(
        TriageInput(free_text="swollen leg and severe pain", postpartum=True)
    )
    assert any("postpartum severe pain or swelling (structured)" in m for m in out)


# ── Emergency wording ─────────────────────────────────────────────────────


def test_default_emergency_guidance_lists_concrete_numbers() -> None:
    guidance, steps = emergency_guidance(["chest pain"])
    # Every default-branch escalation should mention multiple numbers so users
    # outside the operator's home country still get something useful.
    for n in ["112", "911", "999", "000"]:
        assert n in guidance, f"missing {n} in guidance: {guidance}"
    assert any("112" in s for s in steps)


def test_suicidal_guidance_keeps_crisis_line_first() -> None:
    guidance, _ = emergency_guidance(["suicidal ideation"])
    assert "988" in guidance or "Samaritans" in guidance


def test_overdose_guidance_keeps_poison_control_first() -> None:
    guidance, _ = emergency_guidance(["overdose"])
    assert "poison control" in guidance.lower()
