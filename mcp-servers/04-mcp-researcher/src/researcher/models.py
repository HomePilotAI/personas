"""Typed result models returned by the MCP tools.

Every public response carries:

  * ``source``  — which scholarly source the data came from (arxiv,
    openalex, crossref, pubmed, nasa_ads, osti, user_upload, …).
  * ``provenance`` — free-form key/value bag for ops + audit, never
    surfaced to end users verbatim.
  * ``rate_limit_policy`` — declared rate-limit window the call respected
    (e.g. ``"arxiv_1_request_per_3_seconds"``). Required so downstream
    services can detect drift if a connector regresses.

Citation-bearing tools additionally carry:

  * ``citations`` — a list of :class:`Citation`, one per non-trivial claim.
  * ``evidence_level`` — graded E0..E6 per the safety policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SortBy = Literal["relevance", "submittedDate", "lastUpdatedDate"]
SummaryStyle = Literal["short", "technical", "executive"]
BriefStyle = Literal["academic", "executive", "technical"]

SourceTag = Literal[
    "arxiv",
    "openalex",
    "crossref",
    "semantic_scholar",
    "pubmed",
    "europepmc",
    "nasa_ads",
    "osti",
    "doe_pages",
    "clinical_trials",
    "pubchem",
    "chembl",
    "uniprot",
    "pdb",
    "user_upload",
    "cache",
    "internal",
]

PeerReviewStatus = Literal[
    "preprint",
    "peer_reviewed",
    "unknown_or_preprint",
    "internal_report",
    "user_provided",
]

# ── Evidence grading per docs/medical/medical-ai-evaluation-suite.md
# pattern, extended for scientific research:
#   E0 = unsupported (no source attached)
#   E1 = abstract-only
#   E2 = full-text preprint
#   E3 = peer-reviewed paper
#   E4 = replicated across multiple peer-reviewed papers
#   E5 = systematic review / meta-analysis / authoritative dataset
#   E6 = validated clinical or engineering standard
EvidenceLevel = Literal["E0", "E1", "E2", "E3", "E4", "E5", "E6"]


class PaperRef(BaseModel):
    """Lightweight reference to a scholarly paper from any source."""

    paper_id: str = Field(description="Canonical paper ID (arXiv, DOI, PMID, ADS bibcode, …).")
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    published: datetime | None = None
    updated: datetime | None = None
    primary_category: str | None = None
    categories: list[str] = Field(default_factory=list)
    pdf_url: str | None = None
    abs_url: str | None = None
    doi: str | None = None
    journal_ref: str | None = None
    source: SourceTag = "arxiv"
    peer_review_status: PeerReviewStatus = "unknown_or_preprint"
    license: str | None = Field(default=None, description="e.g. CC-BY-4.0, arXiv-1.0, OA-publisher.")


class Citation(BaseModel):
    """A single citation pointing at a chunk / page / section of a paper.

    Citations are the only legitimate way for a tool to support a claim.
    Tools that emit a claim without a matching :class:`Citation` MUST mark
    the claim as ``E0``.
    """

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    source: SourceTag = "arxiv"
    section: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    url: str | None = None
    doi: str | None = None
    confidence: Literal["low", "medium", "high"] = "medium"


class Claim(BaseModel):
    """A single claim with its supporting citation(s) and limitations."""

    claim: str = Field(description="The claim in plain language.")
    evidence_level: EvidenceLevel = "E0"
    citations: list[Citation] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    limitations: list[str] = Field(default_factory=list)


class Provenance(BaseModel):
    """Provenance bag attached to every public response.

    Free-form by design — ops + audit teams add new fields without breaking
    callers. Sensitive content (raw user input, bearer tokens) MUST NOT
    appear here; use the audit log instead.
    """

    request_id: str | None = None
    tool: str | None = None
    sources_consulted: list[SourceTag] = Field(default_factory=list)
    cache_hit: bool = False
    cache_ttl_seconds: int | None = None
    notes: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    query: str
    sort_by: SortBy = "relevance"
    total: int
    results: list[PaperRef]
    source: SourceTag = "arxiv"
    rate_limit_policy: str = "arxiv_1_request_per_3_seconds"
    provenance: Provenance = Field(default_factory=Provenance)


class PaperContent(BaseModel):
    paper: PaperRef
    full_text: str | None = None
    full_text_chars: int = 0
    full_text_truncated: bool = False
    source: Literal[
        "arxiv-pdf",
        "arxiv-abstract",
        "openalex",
        "pubmed",
        "europepmc",
        "user_upload",
        "cache",
    ] = "arxiv-abstract"
    provenance: Provenance = Field(default_factory=Provenance)


class ToolNotImplemented(BaseModel):
    """Stable error envelope used for stub tools so MCP clients see typed payloads."""

    tool: str
    status: Literal["not_implemented"] = "not_implemented"
    sprint: str
    message: str


class ToolBlocked(BaseModel):
    """Returned when a request is refused by the source-policy or dual-use gate."""

    tool: str
    status: Literal["blocked"] = "blocked"
    reason: str = Field(description="Stable category: blocked_pirated_mirror | blocked_private_network | dual_use_refused | …")
    matched: list[str] = Field(default_factory=list, description="Optional human-readable hints for the audit log.")
    message: str = Field(description="Non-shaming, plain-language refusal text safe to surface to the user.")
    safe_alternatives: list[str] = Field(
        default_factory=list,
        description="Suggested benign / safety-oriented framings the user can pivot to.",
    )
    provenance: Provenance = Field(default_factory=Provenance)
