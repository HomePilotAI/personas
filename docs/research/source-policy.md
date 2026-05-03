# Researcher MCP — Source Policy

The enterprise Researcher will only fetch from sources we can defend in
production review. This document is the policy that
`mcp-servers/04-mcp-researcher/src/researcher/source_policy.py` implements
in code; if the code and this doc disagree, the code is authoritative
and the doc must be updated to match.

## 1. Allowed metadata sources

| Source | Host(s) | Notes |
|---|---|---|
| arXiv | `arxiv.org`, `export.arxiv.org` | Legacy API; 1 request / 3 seconds globally. |
| OpenAlex | `api.openalex.org` | Cross-domain scholarly graph. |
| Crossref | `api.crossref.org` | DOI metadata. |
| Semantic Scholar | `api.semanticscholar.org` | Citation graph + abstracts. |
| NCBI E-utilities | `eutils.ncbi.nlm.nih.gov`, `www.ncbi.nlm.nih.gov` | PubMed / PMC. |
| EuropePMC | `europepmc.org`, `www.europepmc.org` | PMC mirror + preprints. |
| NASA ADS | `api.adsabs.harvard.edu` | Astro / aerospace literature. |
| NASA APIs | `api.nasa.gov` | Mission / dataset metadata. |
| DOE OSTI | `www.osti.gov`, `www.osti.doe.gov` | Nuclear / energy R&D. |
| ClinicalTrials.gov | `clinicaltrials.gov`, `www.clinicaltrials.gov` | Trials registry. |
| UniProt | `www.uniprot.org`, `rest.uniprot.org` | Protein metadata. |
| RCSB / PDB | `www.rcsb.org`, `data.rcsb.org`, `files.rcsb.org` | Protein structures. |
| PubChem | `pubchem.ncbi.nlm.nih.gov` | Chemistry. |
| EBI | `www.ebi.ac.uk` | Bioinformatics. |

## 2. Allowed PDF hosts

A strict subset of metadata. PDF download is more dangerous than
metadata fetch (parser bugs, larger blast radius), so the allow list is
tighter:

```
arxiv.org
export.arxiv.org
europepmc.org
www.europepmc.org
ftp.ncbi.nlm.nih.gov
www.ncbi.nlm.nih.gov     # PMC redirects
files.rcsb.org
www.osti.gov
www.osti.doe.gov
```

Any other host needs `ALLOW_ARBITRARY_PDF_URLS=true` (developer mode
only). The deny rules below still apply even with that flag set.

## 3. Hard-deny categories

Substring match on the hostname, intentionally generous so a typo'd
subdomain still blocks:

- `sci-hub` / `scihub`
- `libgen` / `library-genesis`
- `z-library` / `zlib`

Plus, scheme / network / address-level deny:

- non-`http(s)` schemes (`file://`, `ftp://`, `javascript:`, `data:`).
- loopback (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`).
- RFC1918 private ranges (`10/8`, `172.16/12`, `192.168/16`).
- link-local + multicast + reserved + unspecified IPs.
- AWS / GCP / Azure metadata endpoints (`169.254.169.254`).

## 4. User-uploaded documents

User-uploaded PDFs are exempt from the host allow-list because the user
owns the document. They still pass through every PDF guard (size,
page count, magic bytes, text cap) and contribute their hash to the
provenance bag. Future Phase F: dataset uploads (`ingest_dataset_metadata`)
go through the same chain.

## 5. Adding a new source

1. Open a PR adding the host to `ALLOWED_METADATA_HOSTS` and / or
   `ALLOWED_PDF_HOSTS` in `source_policy.py`.
2. Add a row to §1 / §2 of this doc with the connector's notes.
3. Add a test in `tests/test_source_policy.py` asserting the new host
   is allowed for metadata and (if applicable) PDF.
4. If the new source has a published rate-limit policy, configure the
   global limiter at server startup
   (`rate_limit.configure("<source>", min_seconds_between)`).
5. Update `evaluation-suite.md` §3 with the dashboard rows for the
   new source.

## 6. Removing a source

If a source goes off-policy (license change, deprecation, security
issue), remove it from the allow-list in the same commit that updates
this doc and add a regression test. Connector code can stay in the
repo as a deprecated module — the policy gate keeps users safe.
