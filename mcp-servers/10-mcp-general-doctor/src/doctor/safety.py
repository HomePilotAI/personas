"""Safety gateway for the General Doctor adapter.

Two responsibilities:

1. **Red-flag detection** — the adapter's own emergency screen runs on user
   text **before** any upstream call. It is intentionally broader than
   `medical-mcp-toolkit`'s built-in `triageSymptoms` rule set so we never
   miss an emergency due to upstream miss/silence (see
   ``docs/medical/medical-ai-safety-policy.md`` §3).

2. **Output filtering** — every upstream response is rewritten before it
   leaves the adapter. We strip diagnostic language, medication dosing,
   start/stop instructions, and clinical-order tokens
   (``ECG``, ``troponin``, ``aspirin if not contraindicated`` …) and
   return them as ``blocked_content`` so the caller can audit what the
   filter refused to surface (policy §4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# ── Red-flag patterns ───────────────────────────────────────────────────────
#
# Each entry is (label, compiled regex). Labels appear in
# ``matched_red_flags`` so the user-facing guidance can be specific without
# echoing the user's exact text. Patterns err toward false positives.

_RAW_RED_FLAGS: list[tuple[str, str]] = [
    ("chest pain", r"\bchest pain\b"),
    ("chest pressure / tightness", r"\bchest (pressure|tightness)\b"),
    ("pain radiating to arm or jaw", r"\bpain (radiating|spreading) (to|down)[^.]{0,30}\b(arm|jaw|shoulder)\b"),
    ("shortness of breath", r"\bshort(ness)? of breath\b"),
    ("can't breathe", r"\b(can'?t|cannot) breathe\b"),
    ("stroke symptoms", r"\b(stroke|brain attack)\b"),
    ("facial droop", r"\bfac(e|ial) droop"),
    ("one-sided weakness", r"\b(one[- ]sided|left[- ]sided|right[- ]sided) (weak(ness)?|numb(ness)?)\b"),
    ("sudden confusion", r"\bsudden(ly)? (confused|disoriented)\b"),
    ("severe bleeding", r"\bsevere (bleeding|hemorrhage|haemorrhage)\b"),
    ("uncontrolled bleeding", r"\b(can'?t|cannot|won'?t) stop bleeding\b"),
    ("loss of consciousness", r"\b(lost consciousness|passed out|fainted|black(ed)? out)\b"),
    ("seizure", r"\bseiz(ure|ing)\b"),
    ("anaphylaxis", r"\b(anaphyla(xis|ctic)|throat (swelling|closing))\b"),
    ("severe allergic reaction", r"\bsevere allergic reaction\b"),
    ("suicidal ideation", r"\b(suicid(e|al)|kill (myself|me)|end my life|ending it all)\b"),
    ("self-harm intent", r"\b(self[- ]harm|cutting myself|hurt myself)\b"),
    ("overdose", r"\b(over[- ]?dose|too many pills|swallowed too many)\b"),
    ("poisoning", r"\b(poison(ed|ing)|swallowed (chemical|bleach|cleaner))\b"),
    ("severe head injury", r"\b(severe head (injury|trauma)|head injury.*(unconscious|vomiting|seizure))\b"),
    ("suspected concussion", r"\b(concussion|hit my head and (vomit|confused))\b"),
    ("worst headache of my life", r"\b(worst|sudden(ly)? severe) headache\b"),
    ("sudden vision loss", r"\bsudden(ly)? (lost|losing) (my )?(vision|sight)\b"),
    ("severe abdominal pain", r"\bsevere (abdominal|stomach|belly) pain\b"),
    ("pregnancy bleeding", r"\b(pregnan(t|cy)|while pregnant).*(bleed(ing)?|spotting)"),
    ("severe pregnancy pain", r"\b(pregnan(t|cy)|while pregnant).*(severe|sharp) (pain|cramp)\b"),
    ("decreased fetal movement", r"\b(no|decreased|reduced) (fetal|baby) (movement|kicking)\b"),
    ("infant fever", r"\b(infant|baby|newborn).*\b(fever|temperature)\b"),
    ("infant high fever", r"\b(baby|infant|newborn).*\b(40|41|104|105) ?(°|deg|c|f)\b"),
    ("stiff neck with fever", r"\bstiff neck\b.*\bfever\b"),
    ("severe dehydration", r"\bsevere(ly)? dehydrat(ed|ion)\b"),
    ("blue lips / cyanosis", r"\b(blue lips|cyanosis|turning blue)\b"),
    ("rapidly worsening", r"\b(rapidly|quickly) (worsening|getting worse)\b"),
]

RED_FLAGS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pat, re.IGNORECASE)) for label, pat in _RAW_RED_FLAGS
]


@dataclass(frozen=True)
class TriageInput:
    """Lightweight container for inputs the adapter sweeps for red flags.

    Free text + symptoms are the primary signal. The structured fields
    (`age_years`, `pregnant`, `postpartum`) let downstream callers escalate
    based on context the regex set wouldn't catch on its own — e.g. an
    8-month-old with "fever" without the word "infant" anywhere, or a
    pregnant user reporting bleeding without writing "while pregnant".
    """

    free_text: str = ""
    symptoms: tuple[str, ...] = ()
    age_years: float | None = None
    pregnant: bool | None = None
    postpartum: bool | None = None


# ── Structured pediatric / pregnancy signal ──────────────────────────────────

_FEVER_PATTERN = re.compile(r"\b(fever|temperature|febrile)\b", re.IGNORECASE)
_TEMP_PATTERN = re.compile(r"(\d{2,3}(?:[\.,]\d+)?)\s*°?\s*([CF])\b", re.IGNORECASE)
_BREATHING_PATTERN = re.compile(
    r"\b(difficulty breathing|labou?red breath|breathing trouble|wheez|grunt|retraction)",
    re.IGNORECASE,
)
_LETHARGY_PATTERN = re.compile(
    r"\b(lethargy|lethargic|won'?t wake|unresponsive|listless|floppy|unrousable)",
    re.IGNORECASE,
)
_CYANOSIS_PATTERN = re.compile(
    r"\b(blue lips|blue around (the )?(mouth|lips)|cyanosis|turning blue|lips (look|are|seem) blue)",
    re.IGNORECASE,
)
_DEHYDRATION_PATTERN = re.compile(
    r"\b(severe(ly)? dehydrat|sunken eyes|no wet diaper|no tears when crying|dry mouth and lethargic)",
    re.IGNORECASE,
)
_BLEEDING_PATTERN = re.compile(r"\b(bleed(ing)?|spotting|hemorrhag|haemorrhag|soaking through)", re.IGNORECASE)
_SEVERE_PAIN_PATTERN = re.compile(r"\b(severe|sharp|excruciating|10/10) (pain|cramp|abdominal|back)", re.IGNORECASE)
_NO_MOVEMENT_PATTERN = re.compile(
    r"\b(no|decreased|reduced|less|fewer) (fetal |baby )?(movement|kick(ing|s)?)",
    re.IGNORECASE,
)
_HEAVY_BLEEDING_PATTERN = re.compile(
    r"\b(heavy|soaking|gushing) bleed|hemorrhag|haemorrhag",
    re.IGNORECASE,
)


def _extract_temperature_celsius(text: str) -> float | None:
    """Best-effort: pull the first temperature out of ``text``, return °C.

    Accepts forms like ``39°C``, ``104 F``, ``38.5C``, ``40 deg C``. Numbers
    without a unit are ignored — we do not assume the unit. Returns ``None``
    if no temperature is present.
    """
    if not text:
        return None
    for m in _TEMP_PATTERN.finditer(text):
        try:
            value = float(m.group(1))
            unit = m.group(2).upper()
        except (ValueError, IndexError, AttributeError):
            continue
        # Body-temperature sanity: clinical range 30-45°C, 86-113°F.
        # Anything outside is probably not a temperature ("100 mg" etc.).
        if unit == "C" and 30 <= value <= 45:
            return value
        if unit == "F" and 86 <= value <= 113:
            return (value - 32) * 5.0 / 9.0
    return None


def _structured_red_flags(payload: TriageInput) -> list[str]:
    """Detect emergencies that the regex set won't catch from free text alone.

    Each return label is a human-readable category; downstream code routes on
    presence/absence, not on exact wording. False positives are acceptable.
    """
    haystack = " ".join(
        [str(payload.free_text or "").strip(), *(s for s in payload.symptoms if isinstance(s, str))]
    )
    if not haystack and payload.pregnant is None and payload.postpartum is None:
        return []

    matched: list[str] = []

    age = payload.age_years
    fever_word = bool(_FEVER_PATTERN.search(haystack))
    temp_c = _extract_temperature_celsius(haystack)

    # Pediatrics —
    # Under 3 months: any fever is an ER trigger per AAP guidance.
    if age is not None and age < 0.25:  # ≈ < 3 months
        if fever_word or (temp_c is not None and temp_c >= 38.0):
            matched.append("infant fever (age <3 months)")
    # Under 5 years with high fever: ≥ 39°C escalates per common pediatric
    # guidance for unwell-appearing children. We err toward over-escalation.
    if age is not None and 0 <= age < 5:
        if temp_c is not None and temp_c >= 39.0:
            matched.append("high fever in young child")
    # Under 5 years with concerning systemic symptoms.
    if age is not None and age < 5:
        if _BREATHING_PATTERN.search(haystack):
            matched.append("breathing difficulty in young child")
        if _LETHARGY_PATTERN.search(haystack):
            matched.append("lethargy in young child")
        if _CYANOSIS_PATTERN.search(haystack):
            matched.append("cyanosis in young child")
        if _DEHYDRATION_PATTERN.search(haystack):
            matched.append("severe dehydration in young child")

    # Pregnancy — escalate on bleeding, severe pain, or decreased movement
    # regardless of how the user phrased it in free text.
    if payload.pregnant:
        if _BLEEDING_PATTERN.search(haystack):
            matched.append("pregnancy bleeding (structured)")
        if _SEVERE_PAIN_PATTERN.search(haystack):
            matched.append("severe pregnancy pain (structured)")
        if _NO_MOVEMENT_PATTERN.search(haystack):
            matched.append("decreased fetal movement (structured)")

    # Postpartum — heavy bleeding, severe headache, leg swelling, chest
    # symptoms are flagged categories regardless of free-text phrasing.
    if payload.postpartum:
        if _HEAVY_BLEEDING_PATTERN.search(haystack) or "soaking" in haystack.lower():
            matched.append("postpartum hemorrhage (structured)")
        if _SEVERE_PAIN_PATTERN.search(haystack) or "swollen leg" in haystack.lower():
            matched.append("postpartum severe pain or swelling (structured)")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for m in matched:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def detect_red_flags(payload: TriageInput) -> list[str]:
    """Return the list of matched red-flag labels (deduplicated).

    Runs both the regex set (free-text patterns) and the structured-signal
    detector (age / pregnant / postpartum thresholds). The structured layer
    catches the cases the review flagged as gaps: infant fever without the
    word "infant", pregnant + bleeding without "while pregnant", etc.
    """
    haystacks: list[str] = []
    if payload.free_text:
        haystacks.append(payload.free_text)
    haystacks.extend(s for s in payload.symptoms if isinstance(s, str))
    matched: list[str] = []
    seen: set[str] = set()
    for label, pattern in RED_FLAGS:
        for hay in haystacks:
            if hay and pattern.search(hay):
                if label not in seen:
                    matched.append(label)
                    seen.add(label)
                break
    for label in _structured_red_flags(payload):
        if label not in seen:
            matched.append(label)
            seen.add(label)
    return matched


def emergency_guidance(matched: Iterable[str]) -> tuple[str, list[str]]:
    """Return (guidance, safe_next_steps) for an emergency envelope.

    Deliberately generic. We do **not** instruct the user on first-aid steps
    or medications (that is clinical territory). The only escalation is
    "call emergency services / get to emergency care now."
    """
    matched_list = list(matched)
    suicidal = any("suicid" in m or "self-harm" in m for m in matched_list)
    overdose = any("overdose" in m or "poison" in m for m in matched_list)
    if suicidal:
        guidance = (
            "What you're describing needs a real human right now — please call "
            "your local emergency number or a crisis line (US: dial or text 988; "
            "UK/IE: Samaritans 116 123; AU: Lifeline 13 11 14; international: "
            "findahelpline.com)."
        )
        next_steps = [
            "Call your local emergency number or a crisis line now.",
            "If you are in immediate danger, contact emergency services.",
            "If you can, stay with someone you trust until help arrives.",
        ]
    elif overdose:
        guidance = (
            "This is a poisoning emergency — please call your local poison "
            "control centre or emergency number now. Do not wait to see if "
            "symptoms worsen."
        )
        next_steps = [
            "Call your local poison control or emergency number immediately.",
            "If the person is unconscious or not breathing, call emergency services.",
            "Bring the bottle / packaging / substance with you to the hospital if possible.",
        ]
    else:
        guidance = (
            "Seek emergency care now. Call your local emergency number — "
            "for example 112 (EU), 911 (US/Canada), 999 (UK/Ireland), 000 "
            "(Australia), 119 (Korea/Japan), or your country's equivalent. "
            "Do not wait to see if symptoms worsen."
        )
        next_steps = [
            "Call your local emergency number now (112 / 911 / 999 / 000 / your country's equivalent).",
            "Do not drive yourself if symptoms are severe — ask someone or call an ambulance.",
            "If symptoms change suddenly while you wait, tell the dispatcher.",
        ]
    return guidance, next_steps


# ── Output filter ───────────────────────────────────────────────────────────
#
# Patterns to scrub from upstream responses before they reach the user. Each
# entry is (category, regex, replacement). The ``category`` strings are
# returned in ``blocked_content`` so callers can audit.

_DISALLOWED: list[tuple[str, re.Pattern[str], str]] = [
    (
        "diagnosis_language",
        re.compile(r"\b(you (have|have got|definitely have)|it'?s)\s+([a-z][a-z \-]{2,40})", re.IGNORECASE),
        "Possible causes can include this, but only a clinician can diagnose.",
    ),
    (
        "medication_dosing",
        re.compile(r"\b(take|give|administer)\s+([0-9]+(\.[0-9]+)?\s*(mg|mcg|μg|g|ml|tablet|pill|capsule)s?)\b", re.IGNORECASE),
        "Ask a clinician or pharmacist about appropriate medication use.",
    ),
    (
        "medication_dosing",
        re.compile(r"\b[0-9]+(\.[0-9]+)?\s*(mg|mcg|μg|g|ml)\b\s+(of|every|q\d|po|iv|im|sc)?", re.IGNORECASE),
        "Ask a clinician or pharmacist about appropriate medication use.",
    ),
    (
        "start_stop_medication",
        re.compile(r"\b(start|stop|switch|substitute|increase|decrease|double|halve)\s+(your|the)?\s*(medication|prescription|dose|pill|tablet|drug)\b", re.IGNORECASE),
        "Do not start or stop medication without professional guidance.",
    ),
    (
        "clinical_orders",
        re.compile(r"\b(ecg|ekg|troponin|aspirin if not contraindicated|give\s+aspirin|iv\s+(fluids|access)|imaging now|stat\s+(ct|mri|xray|x-ray))\b", re.IGNORECASE),
        "Emergency clinicians may evaluate with tests and treatments as appropriate.",
    ),
    (
        "specialist_attribution",
        re.compile(r"\b(cardiology|pediatric(s)?|oncology|endocrinology|hepatology|obstetrics?)\s+(specialist|agent)\s+(diagnosed|recommended|prescribed)\b", re.IGNORECASE),
        "A clinician can evaluate this further.",
    ),
]


@dataclass
class FilterOutcome:
    text: str
    blocked: list[str]


def filter_text(text: str | None) -> FilterOutcome:
    """Run the output filter over a single string."""
    if not text:
        return FilterOutcome(text=text or "", blocked=[])
    blocked: list[str] = []
    seen: set[str] = set()
    out = text
    for category, pat, repl in _DISALLOWED:
        if pat.search(out):
            if category not in seen:
                blocked.append(category)
                seen.add(category)
            out = pat.sub(repl, out)
    return FilterOutcome(text=out, blocked=blocked)


def filter_lines(items: Iterable[str]) -> tuple[list[str], list[str]]:
    """Filter a list of strings (e.g. KB snippets / next-step bullets).

    Returns ``(cleaned_items, blocked_categories)``. Items whose entire
    content would be blocked are dropped rather than rewritten in place.
    """
    cleaned: list[str] = []
    blocked: list[str] = []
    seen: set[str] = set()
    for item in items:
        outcome = filter_text(item)
        for cat in outcome.blocked:
            if cat not in seen:
                blocked.append(cat)
                seen.add(cat)
        if outcome.text and outcome.text.strip():
            cleaned.append(outcome.text.strip())
    return cleaned, blocked
