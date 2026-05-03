/**
 * DEPRECATED — kept only so validate_mcp_servers.py still finds an entrypoint.
 *
 * The Researcher persona has migrated to a Python-native FastMCP server.
 * Run instead:
 *
 *   python -m researcher.server --transport streamable-http --port 9104
 *
 * or use the dedicated Dockerfile in this folder. This shim returns 410 Gone
 * on every tool route to make stale callers fail loudly rather than silently.
 */
const express = require('express');
const tools = require('./tools').tools;
const app = express();
app.use(express.json());

const DEPRECATION_MESSAGE =
  'The Node.js mcp-researcher entrypoint is deprecated. ' +
  'Use the Python FastMCP server: python -m researcher.server --transport streamable-http';

app.get('/health', (_req, res) => res.json({ status: 'deprecated', message: DEPRECATION_MESSAGE }));
app.get('/tools', (_req, res) => res.json({ tools, deprecated: true, message: DEPRECATION_MESSAGE }));

const goneHandler = (_req, res) =>
  res.status(410).json({ error: { code: 'GONE', message: DEPRECATION_MESSAGE } });

// Routes spelled out as literals so static validators
// (scripts/validate_mcp_servers.py) can confirm every server.json tool has a
// handler. Each one returns 410 Gone with a pointer to the Python server.
app.post('/search_arxiv', goneHandler);
app.post('/read_paper', goneHandler);
app.post('/summarize_paper', goneHandler);
app.post('/compare_papers', goneHandler);
app.post('/build_literature_brief', goneHandler);

const port = process.env.PORT || 9104;
app.listen(port, () => console.log(`[DEPRECATED] node mcp-researcher listening on port ${port}`));
