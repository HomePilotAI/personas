"""HTTP client for the upstream `medical-mcp-toolkit`.

Talks to ``POST {base_url}/invoke`` with the toolkit's bearer-auth contract.
If the upstream is unreachable and ``offline_fallback`` is true, falls back
to a deterministic local fake so red-flag screening keeps working — emergency
detection happens *before* this client in the request path, but the
educational path (`searchMedicalKB`) needs *some* response to render.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("mcp-general-doctor.upstream")


@dataclass
class UpstreamResponse:
    ok: bool
    data: Any
    status: str  # "live" | "offline_fallback" | "error"
    error: str | None = None


class UpstreamClient:
    def __init__(
        self,
        *,
        base_url: str,
        bearer: str | None,
        timeout_s: int,
        offline_fallback: bool,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer = bearer
        self.timeout_s = timeout_s
        self.offline_fallback = offline_fallback

    def _headers(self) -> dict[str, str]:
        if self.bearer:
            return {"Authorization": f"Bearer {self.bearer}"}
        return {}

    def invoke(self, tool: str, args: dict[str, Any]) -> UpstreamResponse:
        url = f"{self.base_url}/invoke"
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(
                    url,
                    json={"tool": tool, "args": args},
                    headers=self._headers(),
                )
            if resp.status_code >= 400:
                log.warning(
                    "upstream %s returned %d: %s",
                    tool,
                    resp.status_code,
                    resp.text[:200],
                )
                if self.offline_fallback:
                    return self._fallback(tool, args, error=f"HTTP {resp.status_code}")
                return UpstreamResponse(
                    ok=False, data=None, status="error", error=f"HTTP {resp.status_code}"
                )
            return UpstreamResponse(ok=True, data=resp.json(), status="live")
        except (httpx.RequestError, httpx.HTTPError) as exc:
            log.warning("upstream %s unreachable: %s", tool, exc)
            if self.offline_fallback:
                return self._fallback(tool, args, error=str(exc))
            return UpstreamResponse(ok=False, data=None, status="error", error=str(exc))

    # ── Offline fallback fakes ────────────────────────────────────────
    #
    # Mirror the *shape* of upstream responses so downstream code is
    # transport-agnostic. We deliberately do NOT include any clinical-order
    # language ("ECG / troponin / aspirin ...") here so the safety filter is
    # not the only thing standing between offline mode and a clinical leak.

    def _fallback(self, tool: str, args: dict[str, Any], *, error: str) -> UpstreamResponse:
        if tool == "triageSymptoms":
            data = {
                "acuity": "routine",
                "advice": "self-care",
                "rulesMatched": [],
                "nextSteps": [],
                "_offline": True,
            }
            return UpstreamResponse(ok=True, data=data, status="offline_fallback", error=error)
        if tool == "searchMedicalKB":
            query = str(args.get("query", "")).strip() or "general health"
            data = {
                "hits": [
                    {
                        "title": f"General information about {query}",
                        "url": "",
                        "score": 0.5,
                        "snippet": (
                            f"Educational overview of {query}. Common causes vary; a "
                            "clinician can evaluate the specifics in your situation."
                        ),
                    }
                ],
                "_offline": True,
            }
            return UpstreamResponse(ok=True, data=data, status="offline_fallback", error=error)
        # Any other tool: the adapter shouldn't have asked for it. Surface
        # an explicit error rather than fabricating data.
        return UpstreamResponse(
            ok=False,
            data=None,
            status="error",
            error=f"offline fallback has no response for {tool}: {error}",
        )
