"""Unit tests for the red-flag detector and the output filter."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from doctor.safety import (  # noqa: E402
    RED_FLAGS,
    TriageInput,
    detect_red_flags,
    emergency_guidance,
    filter_lines,
    filter_text,
)


# ── Red-flag detection ─────────────────────────────────────────────────────


def test_no_red_flags_for_benign_symptoms() -> None:
    out = detect_red_flags(TriageInput(free_text="mild cold and runny nose", symptoms=("cough",)))
    assert out == []


def test_chest_pain_with_radiating_arm_is_emergency() -> None:
    out = detect_red_flags(
        TriageInput(free_text="I have chest pain radiating to my left arm", symptoms=("chest pain",))
    )
    assert "chest pain" in out
    assert any("radiating" in m for m in out)


def test_stroke_signs_detected() -> None:
    cases = [
        "she has facial droop and one-sided weakness",
        "sudden severe headache, worst headache of my life",
        "I think I'm having a stroke",
    ]
    for text in cases:
        assert detect_red_flags(TriageInput(free_text=text)), f"missed: {text}"


def test_anaphylaxis_overdose_seizure_self_harm() -> None:
    for text in [
        "throat swelling and difficulty breathing — anaphylaxis",
        "I took too many pills this morning",
        "she's seizing",
        "I want to kill myself",
        "cutting myself again tonight",
    ]:
        assert detect_red_flags(TriageInput(free_text=text)), f"missed: {text}"


def test_pregnancy_and_infant_red_flags() -> None:
    for text in [
        "I'm pregnant and having severe bleeding",
        "decreased fetal movement since yesterday",
        "newborn with fever",
        "stiff neck and fever",
    ]:
        assert detect_red_flags(TriageInput(free_text=text)), f"missed: {text}"


def test_red_flag_list_covers_full_policy_table() -> None:
    """Every category in the safety policy must have at least one detector."""
    expected_categories = {
        "chest pain",
        "shortness of breath",
        "stroke",
        "severe bleeding",
        "loss of consciousness",
        "seizure",
        "anaphylaxis",
        "suicid",
        "self-harm",
        "overdose",
        "poison",
        "head injury",
        "headache",
        "vision",
        "abdominal pain",
        "pregnan",
        "fetal",
        "infant",
        "stiff neck",
        "dehydrat",
        "blue lips",
        "worsening",
    }
    labels = " ".join(label for label, _ in RED_FLAGS).lower()
    missing = [cat for cat in expected_categories if cat not in labels]
    assert not missing, f"policy categories without a detector: {missing}"


def test_emergency_guidance_specialises_for_suicidal_overdose_default() -> None:
    g_default, _ = emergency_guidance(["chest pain"])
    g_suicide, _ = emergency_guidance(["suicidal ideation"])
    g_overdose, _ = emergency_guidance(["overdose"])
    assert "988" not in g_default
    assert "988" in g_suicide or "Samaritans" in g_suicide
    assert "poison control" in g_overdose.lower()


# ── Output filter ──────────────────────────────────────────────────────────


def test_filter_strips_diagnosis_language() -> None:
    out = filter_text("Doctor said you have rheumatic fever")
    assert "you have rheumatic fever" not in out.text.lower()
    assert "diagnosis_language" in out.blocked


def test_filter_strips_dosing_instructions() -> None:
    out = filter_text("Take 500 mg of paracetamol every 4 hours")
    assert "500 mg" not in out.text
    assert "medication_dosing" in out.blocked


def test_filter_strips_start_stop_medication_language() -> None:
    out = filter_text("You should stop your medication and start a new one")
    assert "stop your medication" not in out.text.lower()
    assert "start_stop_medication" in out.blocked


def test_filter_strips_clinical_orders() -> None:
    out = filter_text("ECG and troponin now; aspirin if not contraindicated")
    assert "troponin" not in out.text.lower()
    assert "aspirin if not contraindicated" not in out.text.lower()
    assert "clinical_orders" in out.blocked


def test_filter_strips_specialist_attribution() -> None:
    out = filter_text("Cardiology specialist diagnosed acute MI")
    assert "specialist_attribution" in out.blocked or "diagnosis_language" in out.blocked


def test_filter_lines_drops_fully_clinical_lines() -> None:
    cleaned, blocked = filter_lines(
        [
            "Rest and hydrate.",
            "ECG / troponin",
            "Take 500 mg every 4 hours.",
        ]
    )
    assert "Rest and hydrate." in cleaned
    assert all("troponin" not in c.lower() for c in cleaned)
    assert all("500 mg" not in c for c in cleaned)
    assert "clinical_orders" in blocked
    assert "medication_dosing" in blocked
