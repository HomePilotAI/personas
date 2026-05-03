# Researcher MCP — Citation & Evidence Policy

The Researcher persona is the only place in the persona pack where we
make scientific claims on a user's behalf. This doc names the rules
those claims must obey, the evidence-grading scale, and the citation
shape every tool response carries.

## 1. Hard rules (release blockers)

The following are non-negotiable — any of them appearing in production
output is a P1 incident:

- **No fabricated citations.** Every citation MUST resolve to a real
  paper at one of the allowed sources. Tools that can't verify a
  citation MUST mark the claim `E0` and surface the limitation.
- **No fabricated DOIs / authors / venues / years / page numbers.**
- **No claims without an evidence marker.** A response that contains
  a non-trivial scientific assertion MUST include either a `Citation`
  or an `evidence_level: "E0"` tag explaining why no citation is
  attached.
- **No "cure" claims** without supporting clinical evidence at `E5+`.
- **No simulation conclusion** without the simulation's stated
  assumptions in the same response.
- **No prescription / dose** in any tool output (covered by the
  General Doctor adapter; the Researcher MUST refuse to generate that
  language even when the user explicitly asks).

## 2. Evidence levels

Pydantic literal `EvidenceLevel` in `models.py`. Levels are mutually
exclusive — a claim has exactly one level.

| Level | Meaning |
|---|---|
| `E0` | Unsupported. No source attached, or the cited source does not back the claim. |
| `E1` | Abstract-only. Claim derives from an abstract / metadata, not the full paper. |
| `E2` | Full-text preprint. Single non-peer-reviewed source. |
| `E3` | Peer-reviewed paper. Single source. |
| `E4` | Replicated. ≥ 2 peer-reviewed sources agreeing. |
| `E5` | Systematic review / meta-analysis / authoritative dataset. |
| `E6` | Validated clinical or engineering standard. |

A `build_literature_brief` claim that bundles three E3 sources may be
upgraded to E4 only if the brief actually demonstrates replication —
not just three papers on the same topic. Tools that auto-grade MUST
default to the lowest applicable level.

## 3. Citation shape

`models.py::Citation`:

```python
{
  "paper_id":  "arxiv:1706.03762v5",
  "title":     "Attention Is All You Need",
  "authors":   ["Ashish Vaswani", "Noam Shazeer", ...],
  "year":      2017,
  "source":    "arxiv",
  "section":   "Results",
  "page":      7,
  "chunk_id":  "1706.03762v5#sec:results#chunk-3",
  "url":       "https://arxiv.org/abs/1706.03762v5",
  "doi":       "10.48550/arXiv.1706.03762",
  "confidence": "high"
}
```

For PDF-derived claims `section`, `page`, and `chunk_id` MUST be
populated when the tool has them. Abstract-only claims may omit page /
chunk_id; the level downgrades to `E1` automatically.

## 4. Claim shape

`models.py::Claim`:

```python
{
  "claim":           "Paper X reports improved confinement under Y assumptions.",
  "evidence_level":  "E2",
  "citations":       [<Citation>, ...],
  "confidence":      "medium",
  "limitations":     ["preprint", "simulation-only", "not experimentally validated"]
}
```

Tools that produce structured output (`build_literature_brief`,
`compare_papers`, `summarize_paper`, `build_evidence_map`) emit a list
of `Claim` rather than free text wherever possible.

## 5. Limitations the persona MUST surface

When the underlying source is one of:

- preprint → `"preprint"`
- simulation only → `"simulation-only"` + the simulation parameters
  the tool extracted
- abstract only → `"abstract-only"`
- non-peer-reviewed (preprint server, blog, internal report) →
  `"not peer reviewed"`
- contradicted by other sources → `"contradicted by <paper_id>"`
- single small-n study → `"low statistical power"`
- animal / in-vitro only → `"preclinical only — not validated in humans"`

The list goes into `Claim.limitations`. The persona prompt MUST
verbalise these limitations next to the claim — never bury them in a
footnote.

## 6. Production gating signal

The evaluation suite (`evaluation-suite.md`) tracks:

- **`fabricated_citation_rate`** — must be **0** in production.
- **`claims_without_evidence_rate`** — must be **0**.
- **`unverified_cure_claim_rate`** — must be **0**.
- **`abstract_only_claim_rate`** — informational; no target. A spike
  often means the upstream PDF pipeline is failing.

Any non-zero on the first three is a rollback trigger
(`incident-response.md`).
