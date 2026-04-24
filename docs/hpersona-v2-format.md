# hpersona v2 Format

The `.hpersona` package is a zip archive with the following top‑level structure:

- **`manifest.json`** – top‑level metadata about the persona package including versioning, content flags and capability summaries.
- **`blueprint/`** – definitions for the persona agent, appearance and agentic configuration.  These JSON files instruct the HomePilot runtime on how to instantiate and present the persona.
- **`dependencies/`** – declarations of external dependencies.  This can include tools, MCP servers, A2A agents, models and suites.  Dependencies point to other packages or servers that must be available for the persona to function correctly.
- **`assets/`** – binary assets such as avatar images and thumbnails.  Avatars are provided in PNG format and thumbnails in WebP format.
- **`preview/`** – data describing how the persona should be displayed in the community gallery.  This typically includes a small JSON card referencing preview images.

HomePilot currently uses **schema version 2** for persona packages.  All personas in this repository conform to that version.