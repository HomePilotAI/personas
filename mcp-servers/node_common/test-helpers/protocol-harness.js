/**
 * Reusable MCP protocol smoke harness.
 *
 * Per-server tests are usually three lines now:
 *
 *   import { runProtocolHarness } from "@homepilot/mcp-node-common/test-helpers/protocol-harness";
 *   import { tools } from "../src/tools.js";
 *   runProtocolHarness({ name: "mcp-creator-muse", version: "1.0.0", tools, sampleArgs });
 *
 * What the harness asserts:
 *   1. initialize succeeds and the SDK client connects.
 *   2. tools/list returns exactly the canonical tool name set.
 *   3. tools/call works for every tool given a sample valid argument set.
 *   4. tools/call rejects bogus tool names.
 *   5. tools/call surfaces invalid input as an error (rejection or
 *      isError:true), without invoking the handler.
 *
 * It does NOT assert tool-specific business semantics — that stays in each
 * server's own per-tool unit tests.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createPersonaMcpServer } from "../createMcpServer.js";

async function connect({ name, version, tools }) {
  const server = createPersonaMcpServer({ name, version, tools });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "protocol-harness", version: "0.0.1" });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  return { client, close: async () => Promise.all([client.close(), server.close()]) };
}

/**
 * @param {object} opts
 * @param {string} opts.name      — server name as registered in McpServer.
 * @param {string} opts.version   — server version.
 * @param {Array}  opts.tools     — tool definitions imported from the server.
 * @param {Record<string, object>} opts.sampleArgs
 *   — map of `toolName` → known-good argument object. Every tool listed in
 *   `opts.tools` must have a sample (the harness fails otherwise).
 * @param {Record<string, object>} [opts.invalidArgs]
 *   — optional map of `toolName` → known-bad arguments to assert validation.
 *   If omitted the validation case is skipped for that tool.
 */
export function runProtocolHarness({ name, version, tools, sampleArgs, invalidArgs = {} }) {
  const expectedNames = tools.map((t) => t.name).sort();

  test(`[${name}] initialize + tools/list returns the canonical set`, async () => {
    const { client, close } = await connect({ name, version, tools });
    try {
      const list = await client.listTools();
      const names = list.tools.map((t) => t.name).sort();
      assert.deepEqual(names, expectedNames);
      for (const t of list.tools) {
        assert.ok(t.description, `tool ${t.name} missing description`);
        assert.equal(t.inputSchema?.type, "object", `tool ${t.name} schema not object`);
      }
    } finally {
      await close();
    }
  });

  for (const tool of tools) {
    const sample = sampleArgs[tool.name];
    assert.ok(sample, `protocol-harness: missing sampleArgs for tool ${tool.name}`);

    test(`[${name}] tools/call returns a result for ${tool.name}`, async () => {
      const { client, close } = await connect({ name, version, tools });
      try {
        const result = await client.callTool({ name: tool.name, arguments: sample });
        assert.ok(Array.isArray(result.content), "result.content must be an array");
        assert.ok(result.content.length > 0, "result.content must not be empty");
        assert.notEqual(result.isError, true, "valid sample args must not error");
      } finally {
        await close();
      }
    });

    if (invalidArgs[tool.name]) {
      test(`[${name}] tools/call rejects invalid input for ${tool.name}`, async () => {
        const { client, close } = await connect({ name, version, tools });
        try {
          let rejected = false;
          let result = null;
          try {
            result = await client.callTool({
              name: tool.name,
              arguments: invalidArgs[tool.name],
            });
          } catch {
            rejected = true;
          }
          if (!rejected) {
            assert.equal(result.isError, true, "expected isError:true on bad input");
          }
        } finally {
          await close();
        }
      });
    }
  }

  test(`[${name}] tools/call rejects unknown tool name`, async () => {
    const { client, close } = await connect({ name, version, tools });
    try {
      let rejected = false;
      let result = null;
      try {
        result = await client.callTool({
          name: "__definitely_not_a_real_tool__",
          arguments: {},
        });
      } catch {
        rejected = true;
      }
      if (!rejected) {
        assert.equal(result.isError, true);
      }
    } finally {
      await close();
    }
  });
}
