"""Dual-use safety gate for the enterprise Researcher.

The persona supports legitimate scientific research across nuclear physics,
aerospace, robotics, biomedical discovery, and chemistry. It MUST refuse to
help with operational weaponisation, harmful autonomous-system optimisation,
pathogen enhancement, unsafe wet-lab execution, illicit paywall bypass, or
medical-treatment prescription.

This module implements the classifier + refusal envelope. It is regex-based
on purpose — it is the cheapest, most auditable layer, runs on every tool
call before any upstream fetch, and never depends on the upstream LLM. False
positives are acceptable; false negatives on the categories below are
blocking.

All categories return a structured ``ToolBlocked`` envelope with
``safe_alternatives`` so the persona can pivot the conversation toward a
benign framing instead of just refusing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

log = logging.getLogger("mcp-researcher.safety")


@dataclass(frozen=True)
class _Pattern:
    category: str
    label: str
    pattern: re.Pattern[str]


# ── Hard-deny categories ────────────────────────────────────────────────────
#
# Each entry is (category_code, human_label, regex). Categories are reused
# across patterns — multiple patterns can map to the same category.

_PATTERNS: list[_Pattern] = [
    # Nuclear / radiological weapons
    _Pattern(
        "weapons_nuclear",
        "nuclear weapon design",
        re.compile(r"\b(nuclear|atomic) (weapon|bomb|warhead|device)\b", re.IGNORECASE),
    ),
    _Pattern(
        "weapons_nuclear",
        "weapons-grade enrichment",
        re.compile(
            r"\b(weapons[- ]grade|HEU|highly[- ]enriched uranium)\b.*\b(produce|enrich|optimi[sz]e)\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "weapons_nuclear",
        "radiological dispersal device",
        re.compile(r"\b(dirty bomb|radiological dispersal|RDD)\b", re.IGNORECASE),
    ),
    _Pattern(
        "weapons_nuclear",
        "fissile assembly",
        re.compile(
            r"\b(implosion|gun[- ]?type|critical mass)\b.*\b(assembly|design|construct)\b",
            re.IGNORECASE,
        ),
    ),
    # Aerospace / autonomous weapons
    _Pattern(
        "weapons_aerospace",
        "missile targeting / guidance",
        re.compile(
            r"\b(missile|warhead|cruise|ballistic|kinetic kill)\b.*\b(target(ing)?|guidance|navigation|seeker)\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "weapons_aerospace",
        "loitering munition / kamikaze drone",
        re.compile(r"\bloitering munition|kamikaze drone\b", re.IGNORECASE),
    ),
    _Pattern(
        "weapons_aerospace",
        "evade air defence",
        re.compile(r"\bevad(e|ing|ed) (air defen[cs]e|radar|detection)", re.IGNORECASE),
    ),
    # Robotics — autonomous lethal systems
    _Pattern(
        "weapons_robotics",
        "autonomous weapon system",
        re.compile(
            r"\b(autonomous (weapon|kill|targeting)|lethal autonomous|killer robot)\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "weapons_robotics",
        "robot weaponisation",
        re.compile(
            r"\b(weapon[i s]e|arm) (a |the |my )?(robot|drone|UAV|UGV)\b", re.IGNORECASE
        ),
    ),
    # Biomedical — pathogens / toxins / enhancement
    _Pattern(
        "biothreat_pathogen",
        "pathogen enhancement / gain-of-function",
        re.compile(
            r"\b(gain of function|enhanc(e|ing) (pathogen|virus|virulence|transmission))\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "biothreat_pathogen",
        "select-agent synthesis",
        re.compile(
            r"\b(synthesi[sz]e|produce|make|construct).*\b(smallpox|variola|anthrax|ebola|marburg|nipah|SARS|botulinum)\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "biothreat_toxin",
        "toxin optimisation",
        re.compile(
            r"\b(optimi[sz]e|maximi[sz]e|enhance) (toxicity|lethality|potency) of\b",
            re.IGNORECASE,
        ),
    ),
    # Chemistry — CW agents
    _Pattern(
        "weapons_chemical",
        "chemical-warfare agent synthesis",
        re.compile(
            r"\b(synthesi[sz]e|produce|make|cook).*\b(sarin|VX|tabun|soman|novichok|mustard gas|chlorine gas weapon)\b",
            re.IGNORECASE,
        ),
    ),
    # Medical — operational prescribing / unverified cure claim
    _Pattern(
        "unsafe_medical",
        "treatment prescription request",
        re.compile(
            r"\b(prescribe|recommend (a |the )?(dose|dosage)|tell me what to take)\b",
            re.IGNORECASE,
        ),
    ),
    _Pattern(
        "unsafe_medical",
        "unverified cure claim",
        re.compile(
            r"\b(guaranteed cure|miracle cure|definitive cure|cures? (cancer|HIV|AIDS|alzheimer|diabetes))\b",
            re.IGNORECASE,
        ),
    ),
    # Illicit-source bypass
    _Pattern(
        "illicit_source",
        "paywall bypass / Sci-Hub",
        re.compile(r"\b(sci[- ]?hub|libgen|library genesis|z[- ]?library|paywall bypass)\b", re.IGNORECASE),
    ),
]


# ── Domain classification ──────────────────────────────────────────────────

_DOMAIN_HINTS: list[tuple[str, re.Pattern[str]]] = [
    (
        "nuclear",
        re.compile(
            r"\b(fusion|fission|plasma|reactor|tokamak|stellarator|isotop|cross[- ]section|"
            r"radiation shielding|criticality|MHD|gyrokinetic)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "aerospace",
        re.compile(
            r"\b(orbit|propulsion|spacecraft|satellite|reentry|GNC|guidance navigation control|"
            r"thermal protection|astrodynamic|aerodynamic|lift coefficient)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "robotics",
        re.compile(
            r"\b(robot|manipulator|gripper|reinforcement learning policy|SLAM|kinematic|"
            r"sim2real|model predictive control|MPC)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "biomedical",
        re.compile(
            r"\b(clinical trial|protein|gene|RNA|DNA|tumour|tumor|cancer|pathogen|"
            r"pharmacokinetic|IC50|EC50|in vitro|in vivo|biomarker)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chemistry",
        re.compile(
            r"\b(catalyst|reaction mechanism|synthesis|spectroscop|DFT|molecular orbital|"
            r"molecule|ligand|chemical (synthesis|reaction))\b",
            re.IGNORECASE,
        ),
    ),
]


def classify_domain(text: str) -> str:
    """Best-effort domain tag for the audit log. Returns 'general' on miss."""
    if not text:
        return "general"
    for domain, pattern in _DOMAIN_HINTS:
        if pattern.search(text):
            return domain
    return "general"


# ── Refusal copy per category ──────────────────────────────────────────────

_REFUSAL_COPY: dict[str, tuple[str, list[str]]] = {
    "weapons_nuclear": (
        "I can help with public literature on reactor physics, fusion research, "
        "radiation shielding, materials science, and reactor safety — but I won't "
        "help design or optimise nuclear weapons or radiological devices.",
        [
            "Compare published reactor-safety analyses for a chosen design.",
            "Build a literature brief on fusion plasma confinement.",
            "Survey radiation-shielding materials for medical or industrial use.",
        ],
    ),
    "weapons_aerospace": (
        "I can help with public literature on orbital mechanics, spacecraft GNC, "
        "propulsion, thermal design, reliability, and benign autonomous flight — "
        "but I won't help with missile targeting, weapon guidance, or evading "
        "defensive systems.",
        [
            "Build a literature brief on small-satellite GNC algorithms.",
            "Compare reentry thermal-protection materials.",
            "Survey published failure modes for a class of orbital propulsion.",
        ],
    ),
    "weapons_robotics": (
        "I can help with public literature on robot perception, control, "
        "manipulation, simulation-to-real transfer, and safety constraints — "
        "but I won't help design autonomous lethal systems or weaponise "
        "platforms.",
        [
            "Compare published RL policies for safe robot navigation.",
            "Build a brief on collision-avoidance benchmarks.",
            "Survey safety-constraint formulations for human-robot interaction.",
        ],
    ),
    "biothreat_pathogen": (
        "I can help with public literature on pathogen biology, immunology, "
        "vaccine research, surveillance, and clinical trials — but I won't help "
        "enhance pathogen virulence or transmissibility, or synthesise select agents.",
        [
            "Survey published immune-correlate-of-protection studies for a target.",
            "Build a brief on existing vaccine-platform comparisons.",
            "Compare published surveillance methods for emerging pathogens.",
        ],
    ),
    "biothreat_toxin": (
        "I can help with literature on toxinology, mechanism of action, and "
        "antidote research — but I won't help optimise lethality or potency.",
        [
            "Survey published antidote / countermeasure research for a toxin family.",
            "Compare known mechanisms of action across structurally similar molecules.",
        ],
    ),
    "weapons_chemical": (
        "I can help with public literature on chemistry, catalysis, materials, and "
        "safety — but I won't help with chemical-warfare agents or related synthesis.",
        [
            "Survey published catalysis research on a target reaction.",
            "Compare scrubbing / detoxification approaches for industrial chemicals.",
        ],
    ),
    "unsafe_medical": (
        "I'm not a clinician — I won't prescribe, recommend a dose, or claim a "
        "cure. I can help you find peer-reviewed literature on a condition or a "
        "molecule and draft questions to bring to a clinician.",
        [
            "Build a literature brief on the current treatment-evidence landscape.",
            "Compare published clinical-trial outcomes for a target intervention.",
            "Draft a list of questions to ask your clinician or pharmacist.",
        ],
    ),
    "illicit_source": (
        "I won't fetch from Sci-Hub, Library Genesis, or any pirated mirror. I'll "
        "use legal open-access sources (arXiv, OpenAlex, PubMed Central, NASA "
        "ADS, DOE OSTI) and any documents you upload yourself.",
        [
            "Search arXiv / OpenAlex / PubMed for the same paper via its DOI.",
            "Try the publisher's open-access version or your institution's library.",
            "Upload the PDF if you legally have it.",
        ],
    ),
}


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    matched: list[str]
    categories: list[str]
    domain: str

    @property
    def primary_category(self) -> str | None:
        return self.categories[0] if self.categories else None


def evaluate(*texts: str | None) -> SafetyDecision:
    """Run the dual-use classifier over one or more free-text fields.

    Concatenates the inputs and sweeps every pattern. Returns ``allowed=True``
    if no category fires; otherwise ``allowed=False`` with the matched labels
    + the set of distinct category codes that triggered.
    """
    blob = " ".join(t for t in texts if t)
    if not blob:
        return SafetyDecision(allowed=True, matched=[], categories=[], domain="general")
    matched_labels: list[str] = []
    matched_categories: list[str] = []
    seen_cat: set[str] = set()
    for entry in _PATTERNS:
        if entry.pattern.search(blob):
            matched_labels.append(entry.label)
            if entry.category not in seen_cat:
                matched_categories.append(entry.category)
                seen_cat.add(entry.category)
    return SafetyDecision(
        allowed=not matched_labels,
        matched=matched_labels,
        categories=matched_categories,
        domain=classify_domain(blob),
    )


def refusal_for(category: str) -> tuple[str, list[str]]:
    """Return ``(message, safe_alternatives)`` for a refusal category."""
    return _REFUSAL_COPY.get(
        category,
        (
            "I can't help with that request. I'm happy to support benign research, "
            "literature review, or safety-oriented analysis on the same topic.",
            [
                "Reframe as a literature review or safety / ethics survey.",
                "Restrict to public, peer-reviewed sources.",
            ],
        ),
    )


def categories() -> Iterable[str]:
    """Iterate the distinct refusal categories the gate supports."""
    seen: set[str] = set()
    for entry in _PATTERNS:
        if entry.category not in seen:
            seen.add(entry.category)
            yield entry.category


__all__ = [
    "SafetyDecision",
    "classify_domain",
    "evaluate",
    "refusal_for",
    "categories",
]
