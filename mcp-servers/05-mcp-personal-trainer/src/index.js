#!/usr/bin/env node
import { runServer } from "@homepilot/mcp-node-common/run";
import { tools } from "./tools.js";

await runServer({
  name: "mcp-personal-trainer",
  version: "1.0.0",
  tools,
  port: 9105,
});
