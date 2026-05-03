#!/usr/bin/env node
import { runServer } from "@homepilot/mcp-node-common/run";
import { tools } from "./tools.js";

await runServer({
  name: "mcp-style-muse",
  version: "1.0.0",
  tools,
  port: 9102,
});
