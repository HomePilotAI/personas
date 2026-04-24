# MCP Server Contract

An **MCP server** is an external service that extends the capabilities of a HomePilot persona.  The HomePilot runtime communicates with an MCP server over HTTP using a simple contract:

* The server must expose a **`/health`** endpoint returning a JSON object indicating the service is alive, typically `{ "status": "ok" }`.
* The server should expose a **`/tools`** endpoint returning metadata about the tools it provides.  Each tool is described by a name and a short description.  Additional metadata such as parameters and argument types may also be returned.
* Tool invocation endpoints are prefixed with the tool name.  For example, a tool named `search_arxiv` could be invoked by sending a POST request to `/search_arxiv` with the appropriate JSON body.

Each server is accompanied by a `server.json` file describing its metadata.  This includes the server name, description, default port, protocol, version and the list of tools it implements.  The `server.json` file makes it possible for the HomePilot runtime to register and connect to the server programmatically.

All MCP servers in this repository are implemented using Node.js and Express for simplicity and consistency.