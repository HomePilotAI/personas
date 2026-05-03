/**
 * Typed error helpers for MCP tool handlers.
 *
 * MCP tool handlers can either throw (the SDK turns the throw into a
 * protocol-level error response) or return a result with `isError: true`
 * which the model sees as a structured tool error. We use both:
 *
 *   - `ToolError` for "the tool understood the request but the call cannot
 *     be served" (e.g. paper not found, safety guardrail tripped).
 *   - `fromZodError` for input validation failures: callers see field-level
 *     issues instead of a generic 400.
 */

export class ToolError extends Error {
  constructor(code, message, details = undefined) {
    super(message);
    this.name = "ToolError";
    this.code = code;
    this.details = details;
  }
}

/** Convert a ZodError into a structured ToolError. */
export function fromZodError(zodError, toolName) {
  const issues = (zodError?.issues || []).map((i) => ({
    path: i.path?.join(".") || "(root)",
    message: i.message,
    code: i.code,
  }));
  return new ToolError(
    "INVALID_INPUT",
    `Invalid input for ${toolName}`,
    { issues }
  );
}

/** Render an error as an MCP error result block (visible to the model). */
export function errorResult(err) {
  if (err instanceof ToolError) {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: JSON.stringify(
            { error: { code: err.code, message: err.message, details: err.details } },
            null,
            2
          ),
        },
      ],
    };
  }
  return {
    isError: true,
    content: [
      {
        type: "text",
        text: JSON.stringify(
          { error: { code: "INTERNAL_ERROR", message: String(err?.message || err) } },
          null,
          2
        ),
      },
    ],
  };
}
