"""Runtime configuration loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ResearcherConfig:
    transport: str
    host: str
    port: int
    log_level: str

    # ── arXiv ──────────────────────────────────────────────────────
    arxiv_max_results: int
    arxiv_default_sort: str
    arxiv_request_timeout_s: int
    arxiv_min_seconds_between_requests: float

    # ── PDF ingestion guards ──────────────────────────────────────
    paper_cache_dir: Path
    enable_pdf_download: bool
    max_pdf_mb: int
    max_pdf_pages: int
    max_pdf_text_chars: int
    pdf_download_timeout_s: int
    allow_arbitrary_pdf_urls: bool

    # ── Knowledge store / RAG ─────────────────────────────────────
    vector_db_dir: Path
    max_chunks_per_query: int
    max_papers_per_request: int

    # ── WatsonX (sprint-3 RAG) ────────────────────────────────────
    watsonx_api_key: str | None
    watsonx_url: str | None
    watsonx_project_id: str | None
    watsonx_model_id: str

    # ── Enterprise gateway (Sprint E) ─────────────────────────────
    require_bearer_auth: bool
    bearer_token: str | None
    audit_log_path: str | None
    audit_hash_user_input: bool
    enable_dual_use_safety: bool

    @classmethod
    def from_env(cls) -> "ResearcherConfig":
        return cls(
            transport=os.getenv("MCP_RESEARCHER_TRANSPORT", "stdio"),
            host=os.getenv("MCP_RESEARCHER_HOST", "127.0.0.1"),
            port=_get_int("MCP_RESEARCHER_PORT", 9104),
            log_level=os.getenv("MCP_RESEARCHER_LOG_LEVEL", "INFO"),
            arxiv_max_results=_get_int("ARXIV_MAX_RESULTS", 8),
            arxiv_default_sort=os.getenv("ARXIV_DEFAULT_SORT", "relevance"),
            arxiv_request_timeout_s=_get_int("ARXIV_REQUEST_TIMEOUT_S", 30),
            arxiv_min_seconds_between_requests=_get_float(
                # arXiv terms of use cap legacy API users at 1 request per
                # 3 seconds globally. We default to 3.0; operators can raise
                # but we refuse to lower this below 3.0 in production.
                "ARXIV_MIN_SECONDS_BETWEEN_REQUESTS",
                3.0,
            ),
            paper_cache_dir=Path(os.getenv("PAPER_CACHE_DIR", ".cache/papers")),
            enable_pdf_download=_get_bool("ENABLE_PDF_DOWNLOAD", True),
            max_pdf_mb=_get_int("MAX_PDF_MB", 50),
            max_pdf_pages=_get_int("MAX_PDF_PAGES", 250),
            max_pdf_text_chars=_get_int("MAX_PDF_TEXT_CHARS", 500_000),
            pdf_download_timeout_s=_get_int("PDF_DOWNLOAD_TIMEOUT_S", 60),
            allow_arbitrary_pdf_urls=_get_bool("ALLOW_ARBITRARY_PDF_URLS", False),
            vector_db_dir=Path(os.getenv("VECTOR_DB_DIR", ".cache/chroma")),
            max_chunks_per_query=_get_int("MAX_CHUNKS_PER_QUERY", 12),
            max_papers_per_request=_get_int("MAX_PAPERS_PER_REQUEST", 10),
            watsonx_api_key=os.getenv("WATSONX_APIKEY") or None,
            watsonx_url=os.getenv("WATSONX_URL") or None,
            watsonx_project_id=os.getenv("WATSONX_PROJECT_ID") or None,
            watsonx_model_id=os.getenv(
                "WATSONX_MODEL_ID", "meta-llama/llama-3-70b-instruct"
            ),
            require_bearer_auth=_get_bool("MCP_RESEARCHER_REQUIRE_BEARER", False),
            bearer_token=os.getenv("MCP_RESEARCHER_BEARER_TOKEN") or None,
            audit_log_path=os.getenv("RESEARCHER_AUDIT_LOG_PATH") or None,
            audit_hash_user_input=_get_bool("RESEARCHER_AUDIT_HASH_USER_INPUT", True),
            enable_dual_use_safety=_get_bool("ENABLE_DUAL_USE_SAFETY", True),
        )
