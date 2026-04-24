# Gallery Publishing

Once persona packages have been built, they can be published to the HomePilot Community Gallery.  The build process creates the following artifacts:

- **`dist/packages/<persona-id>/<version>/persona.hpersona`** – the zipped persona package ready to be installed.
- **`dist/previews/<persona-id>/<version>/preview.webp`** – a WebP image used by the gallery for the persona preview card.
- **`dist/previews/<persona-id>/<version>/card.json`** – a JSON object containing metadata displayed on the gallery card (title, description and preview image reference).

The `registry/` directory contains metadata describing each persona and MCP server.  `registry.json` lists all available packages and their versions, while `registry/personas/<persona-id>.json` and `registry/mcp-servers/<server-id>.json` provide detailed entries.  These files are consumed by the gallery when indexing new submissions.

To publish to the gallery you would typically upload the contents of `dist/` and `registry/` to the appropriate storage backend used by the HomePilot gallery.  This repository does not automate publishing; it provides the structure necessary to prepare packages for distribution.