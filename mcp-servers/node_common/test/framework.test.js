/**
 * Smoke tests for the node_common framework: in-memory MCP roundtrip.
 *
 * Uses an in-memory transport pair so the test stays hermetic — no stdio
 * spawn, no HTTP socket. If these pass, persona servers built on top of
 * createPersonaMcpServer / runServer are wiring through the SDK correctly.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { z } from "zod";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createPersonaMcpServer } from "../createMcpServer.js";
import { textResult, jsonResult } from "../responses.js";
import { ToolError } from "../errors.js";

async function makeConnectedClient(server) {
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test-client", version: "0.0.1" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  return { client, close: async () => Promise.all([client.close(), server.close()]) };
}

test("createPersonaMcpServer registers tools and tools/list returns them", async () => {
  const server = createPersonaMcpServer({
    name: "test-server",
    version: "1.0.0",
    tools: [
      {
        name: "echo",
        description: "Echo a topic back as text.",
        schema: { topic: z.string().min(1) },
        handler: ({ topic }) => textResult(`echo: ${topic}`),
      },
      {
        name: "info",
        description: "Return a structured info object.",
        schema: { who: z.string().min(1) },
        handler: ({ who }) => jsonResult({ hello: who, version: 1 }),
      },
    ],
  });
  const { client, close } = await makeConnectedClient(server);
  try {
    const list = await client.listTools();
    const names = list.tools.map((t) => t.name).sort();
    assert.deepEqual(names, ["echo", "info"]);
    assert.equal(list.tools.find((t) => t.name === "echo").inputSchema.type, "object");
  } finally {
    await close();
  }
});

test("tools/call returns content blocks from the handler", async () => {
  const server = createPersonaMcpServer({
    name: "test-server",
    version: "1.0.0",
    tools: [
      {
        name: "echo",
        description: "Echo a topic back as text.",
        schema: { topic: z.string().min(1) },
        handler: ({ topic }) => textResult(`echo: ${topic}`),
      },
    ],
  });
  const { client, close } = await makeConnectedClient(server);
  try {
    const result = await client.callTool({ name: "echo", arguments: { topic: "hi" } });
    assert.equal(result.content[0].type, "text");
    assert.equal(result.content[0].text, "echo: hi");
    assert.notEqual(result.isError, true);
  } finally {
    await close();
  }
});

test("invalid input is surfaced as a tool error result", async () => {
  // The SDK validates tool args against the zod shape and either rejects the
  // call (older SDKs) or returns isError:true (current SDK). Either is fine
  // — the framework just needs to surface the failure to the caller.
  let handlerCalled = false;
  const server = createPersonaMcpServer({
    name: "test-server",
    version: "1.0.0",
    tools: [
      {
        name: "echo",
        description: "Echo.",
        schema: { topic: z.string().min(1) },
        handler: ({ topic }) => {
          handlerCalled = true;
          return textResult(topic);
        },
      },
    ],
  });
  const { client, close } = await makeConnectedClient(server);
  try {
    let rejected = false;
    let errorResult = null;
    try {
      errorResult = await client.callTool({ name: "echo", arguments: { topic: "" } });
    } catch (err) {
      rejected = true;
      assert.match(String(err.message || ""), /topic|invalid|validation/i);
    }
    if (!rejected) {
      assert.equal(errorResult.isError, true, "expected isError:true result");
    }
    assert.equal(handlerCalled, false, "handler must not run when input is invalid");
  } finally {
    await close();
  }
});

test("ToolError is surfaced as an isError result block", async () => {
  const server = createPersonaMcpServer({
    name: "test-server",
    version: "1.0.0",
    tools: [
      {
        name: "boom",
        description: "Always fails.",
        schema: { x: z.string() },
        handler: () => {
          throw new ToolError("NOT_FOUND", "no such thing");
        },
      },
    ],
  });
  const { client, close } = await makeConnectedClient(server);
  try {
    const result = await client.callTool({ name: "boom", arguments: { x: "y" } });
    assert.equal(result.isError, true);
    const payload = JSON.parse(result.content[0].text);
    assert.equal(payload.error.code, "NOT_FOUND");
    assert.match(payload.error.message, /no such thing/);
  } finally {
    await close();
  }
});

test("plain object handler return is auto-wrapped via jsonResult", async () => {
  const server = createPersonaMcpServer({
    name: "test-server",
    version: "1.0.0",
    tools: [
      {
        name: "raw",
        description: "Returns a plain object.",
        schema: { who: z.string() },
        handler: ({ who }) => ({ hello: who, n: 42 }),
      },
    ],
  });
  const { client, close } = await makeConnectedClient(server);
  try {
    const result = await client.callTool({ name: "raw", arguments: { who: "world" } });
    const decoded = JSON.parse(result.content[0].text);
    assert.deepEqual(decoded, { hello: "world", n: 42 });
  } finally {
    await close();
  }
});

test("createPersonaMcpServer rejects empty tool list", () => {
  assert.throws(
    () =>
      createPersonaMcpServer({
        name: "x",
        version: "1.0.0",
        tools: [],
      }),
    /at least one tool/i
  );
});
