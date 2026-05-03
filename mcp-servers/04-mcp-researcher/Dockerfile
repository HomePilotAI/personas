# mcp-researcher — Python FastMCP server
# Multi-stage build: install deps as root, run as a non-root user.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OS deps for pypdf / httpx (minimal — no compilers needed at runtime).
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

# Cache + non-root user.
RUN useradd --create-home --uid 10001 researcher \
 && mkdir -p /app/.cache/papers /app/.cache/chroma \
 && chown -R researcher:researcher /app
USER researcher

ENV MCP_RESEARCHER_TRANSPORT=streamable-http \
    MCP_RESEARCHER_HOST=0.0.0.0 \
    MCP_RESEARCHER_PORT=9104 \
    PAPER_CACHE_DIR=/app/.cache/papers \
    VECTOR_DB_DIR=/app/.cache/chroma \
    PYTHONPATH=/app/src

EXPOSE 9104

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent --show-error \
        "http://127.0.0.1:${MCP_RESEARCHER_PORT}/mcp" \
        -H "Accept: text/event-stream" \
        -X POST -d '{}' >/dev/null || exit 1

CMD ["python", "-m", "researcher.server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9104"]
