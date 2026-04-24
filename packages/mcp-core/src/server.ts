export function createServer() {
  // Simple Express server factory used by MCP services.
  const express = require('express');
  const app = express();
  app.get('/health', (_req: any, res: any) => {
    res.json({ status: 'ok' });
  });
  return app;
}