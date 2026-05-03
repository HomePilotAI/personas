"""Source allow-list / deny-list policy for the enterprise Researcher MCP.

The persona MUST refuse to fetch from:

  * known paywall-bypass / pirated mirrors (Sci-Hub, Library Genesis, …);
  * any non-http(s) scheme (file://, ftp://, javascript:, data:, …);
  * loopback / link-local / RFC1918 private networks (SSRF protection);
  * unknown PDF mirrors when ``allow_arbitrary_pdf_urls`` is false.

This module is the single source of truth for those checks; every connector
and PDF-ingest path imports from here. Tests exercise both the allow side
and the deny side.

References:

  * arXiv terms of use — legal source allowed.
    https://info.arxiv.org/help/api/tou.html
  * OpenAlex / Crossref / NCBI / NASA ADS / DOE OSTI — added to the allow
    list as the multi-source connectors land in later sprints.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse

# ── Hard deny ───────────────────────────────────────────────────────────────
# Substring match on the hostname; intentionally generous so a typo'd subdomain
# still blocks. Adding a host here is a one-line policy change.
BLOCKED_HOST_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "sci-hub",
        "scihub",
        "libgen",
        "library-genesis",
        "z-library",
        "zlib",
    }
)

# ── Allow list of legal scholarly sources ───────────────────────────────────
# Hosts the adapter is willing to fetch metadata or content from.
ALLOWED_METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "arxiv.org",
        "export.arxiv.org",
        "api.openalex.org",
        "api.crossref.org",
        "api.semanticscholar.org",
        "eutils.ncbi.nlm.nih.gov",
        "www.ncbi.nlm.nih.gov",
        "europepmc.org",
        "www.europepmc.org",
        "api.adsabs.harvard.edu",
        "api.nasa.gov",
        "www.osti.gov",
        "www.osti.doe.gov",
        "clinicaltrials.gov",
        "www.clinicaltrials.gov",
        "www.uniprot.org",
        "rest.uniprot.org",
        "www.rcsb.org",
        "data.rcsb.org",
        "files.rcsb.org",
        "pubchem.ncbi.nlm.nih.gov",
        "www.ebi.ac.uk",
    }
)

# Hosts the adapter will download a *PDF* from (a strict subset of metadata).
ALLOWED_PDF_HOSTS: frozenset[str] = frozenset(
    {
        "arxiv.org",
        "export.arxiv.org",
        "europepmc.org",
        "www.europepmc.org",
        "ftp.ncbi.nlm.nih.gov",
        "www.ncbi.nlm.nih.gov",  # PMC PDF redirects
        "files.rcsb.org",
        "www.osti.gov",
        "www.osti.doe.gov",
    }
)


@dataclass(frozen=True)
class SourceDecision:
    allowed: bool
    reason: str  # "allowed" | "blocked_scheme" | "blocked_private_network" | …
    host: str | None


def _is_private_or_loopback(host: str) -> bool:
    """Return True for any host that points at the local machine or RFC1918."""
    if not host:
        return True
    if host in {"localhost", "ip6-localhost", "ip6-loopback", "0.0.0.0"}:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False  # not an IP literal — treat as public; DNS-based SSRF is
        # an L7 concern handled by network egress policy in production.
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def classify(url: str) -> SourceDecision:
    """Classify a URL against the deny rules. Used by every fetcher."""
    if not url or not isinstance(url, str):
        return SourceDecision(False, "blocked_empty_url", None)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme not in {"http", "https"}:
        return SourceDecision(False, "blocked_scheme", host or None)
    if not host:
        return SourceDecision(False, "blocked_no_host", None)
    if _is_private_or_loopback(host):
        return SourceDecision(False, "blocked_private_network", host)
    for token in BLOCKED_HOST_SUBSTRINGS:
        if token in host:
            return SourceDecision(False, "blocked_pirated_mirror", host)
    return SourceDecision(True, "allowed", host)


def is_blocked_source(url: str) -> bool:
    """Backwards-compatible boolean wrapper around :func:`classify`."""
    return not classify(url).allowed


def is_allowed_metadata_source(url: str, *, allow_arbitrary: bool = False) -> bool:
    """Check a URL against the metadata-API allow list.

    When ``allow_arbitrary`` is true (developer mode) we still apply the
    deny rules — pirated mirrors and SSRF targets are never reachable.
    """
    decision = classify(url)
    if not decision.allowed:
        return False
    if allow_arbitrary:
        return True
    return decision.host in ALLOWED_METADATA_HOSTS


def is_allowed_pdf_source(url: str, *, allow_arbitrary: bool = False) -> bool:
    """Check a URL against the PDF-download allow list (stricter than metadata)."""
    decision = classify(url)
    if not decision.allowed:
        return False
    if allow_arbitrary:
        return True
    return decision.host in ALLOWED_PDF_HOSTS


__all__ = [
    "SourceDecision",
    "classify",
    "is_blocked_source",
    "is_allowed_metadata_source",
    "is_allowed_pdf_source",
    "ALLOWED_METADATA_HOSTS",
    "ALLOWED_PDF_HOSTS",
    "BLOCKED_HOST_SUBSTRINGS",
]
