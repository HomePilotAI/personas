# mcp-general-doctor — Python FastMCP safety adapter
# Mirrors the mcp-researcher Dockerfile pattern (3.12-slim, non-root,
# /mcp healthcheck) since both are Python FastMCP servers.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# pyproject.toml declares `readme = "README.md"` and the package layout
# under src/. Both must be present before `pip install .` runs, otherwise
# setuptools fails with "readme file not found" / "no packages found".
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip \
 && pip install . \
 && pip cache purge || true

RUN useradd --create-home --uid 10001 doctor \
 && mkdir -p /app/.cache \
 && chown -R doctor:doctor /app
USER doctor

ENV DOCTOR_MCP_TRANSPORT=streamable-http \
    DOCTOR_MCP_HOST=0.0.0.0 \
    DOCTOR_MCP_PORT=9110 \
    PYTHONPATH=/app/src

EXPOSE 9110

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent --show-error \
        "http://127.0.0.1:${DOCTOR_MCP_PORT}/mcp" \
        -H "Accept: text/event-stream" \
        -X POST -d '{}' >/dev/null || exit 1

CMD ["python", "-m", "doctor.server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9110"]
