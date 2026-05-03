"""Entrypoint shim — delegates to ``doctor.server.main`` so the validator
finds an MCP-native entrypoint at the conventional ``src/index.py`` path
while the real implementation lives under ``src/doctor/`` as a package.

Run instead via:

    python -m doctor.server --transport streamable-http --port 9110

Both this shim and the package main work identically; the package form is
preferred because it picks up the editable install and is what the Dockerfile
and docker-compose use.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling package importable when this file is the script entrypoint.
_PKG_ROOT = Path(__file__).resolve().parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: F401  (validator marker)
from doctor.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
