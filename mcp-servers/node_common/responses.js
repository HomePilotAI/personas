/**
 * Build MCP-compatible tool results out of plain Node values.
 *
 * Every MCP tool result must be `{ content: [...content blocks] }`. We give
 * tool authors three small helpers so they don't have to remember the shape.
 */

/** Stringify a value as a `text` content block. */
export function textResult(text) {
  const body = typeof text === "string" ? text : JSON.stringify(text, null, 2);
  return { content: [{ type: "text", text: body }] };
}

/**
 * Wrap a structured object as a single JSON-stringified text block.
 * Tool authors should prefer this for any non-trivial payload so MCP
 * clients receive a parseable JSON document.
 */
export function jsonResult(obj) {
  return {
    content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
  };
}

/**
 * Build a result with a human-readable summary first followed by the full
 * structured payload as JSON. Useful for tools where the model benefits from
 * a one-line synopsis before the data.
 */
export function mixedResult(summary, payload) {
  return {
    content: [
      { type: "text", text: String(summary) },
      { type: "text", text: JSON.stringify(payload, null, 2) },
    ],
  };
}
