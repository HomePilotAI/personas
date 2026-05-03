/**
 * Factory for persona MCP servers.
 *
 * Each persona MCP server provides:
 *   { name, version, tools: [{ name, description, schema, handler }, ...] }
 *
 * `schema` is a zod-shape object (NOT a wrapped z.object) — the SDK's
 * `server.tool()` accepts the shape directly and synthesises the JSON
 * Schema for MCP `inputSchema`. `handler(args, ctx)` returns either a
 * pre-built MCP result, a string, or a plain object — the factory wraps
 * non-result values via `jsonResult` automatically.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { jsonResult, textResult } from "./responses.js";
import { errorResult, fromZodError, ToolError } from "./errors.js";

function isMcpResult(value) {
  return (
    value &&
    typeof value === "object" &&
    Array.isArray(value.content) &&
    value.content.every((c) => c && typeof c.type === "string")
  );
}

function wrapResult(value) {
  if (isMcpResult(value)) return value;
  if (typeof value === "string") return textResult(value);
  return jsonResult(value);
}

export function createPersonaMcpServer({ name, version, tools }) {
  if (!name || !version) {
    throw new Error("createPersonaMcpServer requires { name, version }");
  }
  if (!Array.isArray(tools) || tools.length === 0) {
    throw new Error(
      `createPersonaMcpServer for ${name} requires at least one tool`
    );
  }

  const server = new McpServer({ name, version });

  for (const tool of tools) {
    if (!tool?.name || !tool?.description || !tool?.handler) {
      throw new Error(
        `tool definition for ${name} missing name/description/handler: ${JSON.stringify(tool)}`
      );
    }
    const schemaShape = tool.schema || {};

    server.tool(
      tool.name,
      tool.description,
      schemaShape,
      async (args, ctx) => {
        try {
          const result = await tool.handler(args, ctx);
          return wrapResult(result);
        } catch (err) {
          // ZodError is thrown when the SDK parsed schema fails — we wrap it
          // for callers but the SDK already validates before reaching here.
          if (err?.issues) return errorResult(fromZodError(err, tool.name));
          if (err instanceof ToolError) return errorResult(err);
          throw err;
        }
      }
    );
  }

  return server;
}
