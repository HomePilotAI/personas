.PHONY: install test build assets metadata package validate clean all

# Install Node and Python dependencies.
install:
	npm install
	pip install -r requirements.txt

# End-to-end pipeline: assets + metadata + packaging + validation.
all: assets metadata package validate

# Generate avatar PNGs, gallery WebP previews and thumbnails.
assets:
	python3 scripts/generate_assets.py

# Regenerate enriched card.json, blueprints, manifests, registry entries.
metadata:
	python3 scripts/generate_metadata.py

# Build .hpersona zip packages and dist/previews into dist/.
package:
	python3 scripts/build_hpersona.py

# Validate persona structure and gallery readiness.
validate:
	python3 scripts/validate_personas.py
	python3 scripts/validate_mcp_servers.py

# Backwards-compatible aliases.
test: validate
build: package

# Clean built artifacts.
clean:
	rm -rf dist
