# MCP Inspector configurations

[MCP Inspector](https://ibm.github.io/mcp-context-forge/using/clients/mcp-inspector/)
is the easiest way to validate that a server speaks real MCP. These configs
point Inspector at this repo's persona servers in either transport.

## Files

| File | Purpose |
|---|---|
| `all-stdio.json` | Every migrated server in `stdio` mode. Useful when you have nothing running yet. |
| `all-http.json` | Every migrated server reachable over Streamable HTTP at `http://localhost:<port>/mcp`. Bring the stack up with `docker compose -f docker-compose.mcp.yml up` first. |
| `<server>.json` | Single-server configs for fast iteration on one persona. |

## Usage

```bash
# stdio (no servers need to be running — Inspector spawns them)
npx @modelcontextprotocol/inspector --config configs/inspector/all-stdio.json

# Streamable HTTP (servers must already be running)
npx @modelcontextprotocol/inspector --config configs/inspector/all-http.json
```

Inspector connects, lists every tool, and lets you call them with the
declared input schema. If a server is missing here it has not yet been
migrated to real MCP — see `docs/migration/mcp-migration-tracker.md`.
