# mcp-researcher (Python, FastMCP)

Python-native MCP server backing the **Researcher** persona. Exposes academic-
research tools (arXiv search, paper reading, summaries, comparisons,
literature briefs) over the Model Context Protocol so it can be driven by
MCP Inspector and federated by [MCP Context Forge](https://ibm.github.io/mcp-context-forge/).

## Tools (canonical contract)

| Name | Status | Description |
|---|---|---|
| `search_arxiv` | sprint-1 (stubbed → real in batch 3) | Search arXiv and return normalized paper metadata. |
| `read_paper` | sprint-2 | Fetch metadata and optionally extract the full PDF text. |
| `summarize_paper` | sprint-2 / sprint-3 | Abstract-only summary first, then full-text RAG via WatsonX. |
| `compare_papers` | sprint-3 | Side-by-side compare on method, dataset, result, limitation. |
| `build_literature_brief` | sprint-4 | Citation-backed literature brief grouped by themes/gaps. |

Stubbed tools return a typed `ToolNotImplemented` envelope so Inspector still
lists their JSON schemas.

## Quickstart

```bash
cd mcp-servers/04-mcp-researcher
cp .env.example .env
pip install -e .          # or: uv pip install -e .
```

### Run over stdio (local Inspector)

```bash
python -m researcher.server --transport stdio
```

MCP Inspector config snippet:

```json
{
  "mcpServers": {
    "mcp-researcher": {
      "command": "python",
      "args": ["-m", "researcher.server", "--transport", "stdio"],
      "cwd": "mcp-servers/04-mcp-researcher"
    }
  }
}
```

### Run over Streamable HTTP (Context Forge / Docker)

```bash
python -m researcher.server --transport streamable-http --host 0.0.0.0 --port 9104
```

The MCP endpoint is then reachable at `http://<host>:9104/mcp`.

## Configuration

All knobs are environment variables. See [`.env.example`](./.env.example).
Key ones:

| Var | Default | Purpose |
|---|---|---|
| `MCP_RESEARCHER_TRANSPORT` | `stdio` | `stdio` \| `streamable-http` \| `sse` |
| `MCP_RESEARCHER_PORT` | `9104` | HTTP transport port |
| `ARXIV_MAX_RESULTS` | `8` | Hard cap on `search_arxiv` results |
| `MAX_PAPERS_PER_REQUEST` | `10` | Safety cap across tools |
| `WATSONX_APIKEY` / `WATSONX_URL` / `WATSONX_PROJECT_ID` | — | Used in sprint 3 |

## Layout

```
mcp-servers/04-mcp-researcher/
├── pyproject.toml
├── .env.example
├── README.md
├── server.json           # MCP server registry metadata
├── src/researcher/
│   ├── __init__.py
│   ├── config.py         # env-driven runtime config
│   ├── models.py         # pydantic result models
│   ├── arxiv_client.py   # arXiv search (sprint-1 batch 3)
│   ├── paper_reader.py   # PDF reader (sprint-2)
│   ├── chunking.py       # (sprint-3)
│   ├── embeddings.py     # (sprint-3)
│   ├── vector_store.py   # (sprint-3)
│   ├── watsonx_client.py # (sprint-3)
│   ├── citations.py      # (sprint-4)
│   ├── brief_builder.py  # (sprint-4)
│   └── server.py         # FastMCP entry point
└── tests/
```

The legacy `src/index.js` and `src/index.py` are kept for one release as a
compatibility shim while consumers cut over to the Python MCP transport;
they will be removed once Context Forge points at the FastMCP endpoint.

## Roadmap

- **Sprint 1** — FastMCP scaffold, `search_arxiv` real impl, contract cleanup. ◀ *current*
- **Sprint 2** — `read_paper` + abstract-based `summarize_paper`, PDF cache.
- **Sprint 3** — Chunking, ChromaDB vector store, WatsonX RAG, `compare_papers`.
- **Sprint 4** — `build_literature_brief`, citations, Context Forge federation.

## License

Apache-2.0 (matches the parent repo).
