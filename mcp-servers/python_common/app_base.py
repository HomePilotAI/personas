from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("mcp-python")


class ToolInfo(BaseModel):
    name: str
    description: str


class HealthResponse(BaseModel):
    status: str = "ok"
    server: str
    timestamp: str


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]


class ResultResponse(BaseModel):
    result: Any


class ErrorEnvelope(BaseModel):
    error: dict[str, Any]


class ContextForgeCallRequest(BaseModel):
    tool: str = Field(description="Tool name as declared by /tools")
    arguments: dict[str, Any] = Field(default_factory=dict)


class ContextForgeCallResponse(BaseModel):
    tool: str
    result: Any


def create_base_app(server_name: str, tools: list[dict[str, str]]) -> FastAPI:
    app = FastAPI(title=server_name, version="1.0.0")

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "unhandled_error",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "latency_ms": latency_ms,
                },
            )
            body = ErrorEnvelope(
                error={
                    "code": "INTERNAL_ERROR",
                    "message": "Unhandled server error",
                    "request_id": request_id,
                }
            )
            return JSONResponse(status_code=500, content=body.model_dump())

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["x-request-id"] = request_id
        response.headers["x-latency-ms"] = str(latency_ms)
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response

    @app.get("/health", response_model=HealthResponse)
    async def health() -> dict[str, str]:
        from datetime import datetime, timezone

        return {
            "status": "ok",
            "server": server_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/tools", response_model=ToolsResponse)
    async def list_tools() -> dict[str, list[dict[str, str]]]:
        return {"tools": tools}

    return app


def attach_context_forge_routes(
    app: FastAPI,
    tools: list[dict[str, str]],
    tool_runner: Callable[[str, dict[str, Any]], Any],
) -> None:
    @app.get("/context-forge/tools", response_model=ToolsResponse)
    async def context_forge_tools() -> dict[str, list[dict[str, str]]]:
        return {"tools": tools}

    @app.post("/context-forge/call", response_model=ContextForgeCallResponse)
    async def context_forge_call(payload: ContextForgeCallRequest):
        try:
            result = tool_runner(payload.tool, payload.arguments)
        except ValueError as exc:
            return JSONResponse(status_code=400, content=fallback_error(str(exc), code="INVALID_TOOL").model_dump())
        return {"tool": payload.tool, "result": result}


def fallback_error(message: str, request_id: str | None = None, code: str = "BAD_REQUEST") -> ErrorEnvelope:
    return ErrorEnvelope(
        error={"code": code, "message": message, **({"request_id": request_id} if request_id else {})}
    )
