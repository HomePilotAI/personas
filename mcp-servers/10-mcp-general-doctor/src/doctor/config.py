"""Runtime configuration for the General Doctor adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class DoctorConfig:
    transport: str
    host: str
    port: int
    log_level: str
    adapter_enabled: bool
    upstream_url: str
    upstream_bearer: str | None
    upstream_timeout_s: int
    upstream_offline_fallback: bool
    enable_patient_tools: bool
    enable_drug_alternatives: bool
    enable_appointment_scheduling: bool
    audit_log_path: str | None
    audit_hash_user_input: bool

    @classmethod
    def from_env(cls) -> "DoctorConfig":
        return cls(
            transport=os.getenv("DOCTOR_MCP_TRANSPORT", "stdio"),
            host=os.getenv("DOCTOR_MCP_HOST", "127.0.0.1"),
            port=_int("DOCTOR_MCP_PORT", 9110),
            log_level=os.getenv("DOCTOR_LOG_LEVEL", "INFO"),
            adapter_enabled=_bool("GENERAL_DOCTOR_ADAPTER_ENABLED", True),
            upstream_url=os.getenv("MEDICAL_MCP_URL", "http://localhost:9090").rstrip("/"),
            upstream_bearer=os.getenv("MEDICAL_MCP_BEARER_TOKEN") or None,
            upstream_timeout_s=_int("MEDICAL_MCP_TIMEOUT_S", 10),
            upstream_offline_fallback=_bool("MEDICAL_MCP_OFFLINE_FALLBACK", True),
            enable_patient_tools=_bool("ENABLE_PATIENT_TOOLS", False),
            enable_drug_alternatives=_bool("ENABLE_DRUG_ALTERNATIVES", False),
            enable_appointment_scheduling=_bool("ENABLE_APPOINTMENT_SCHEDULING", False),
            audit_log_path=os.getenv("DOCTOR_AUDIT_LOG_PATH") or None,
            audit_hash_user_input=_bool("DOCTOR_AUDIT_HASH_USER_INPUT", True),
        )
