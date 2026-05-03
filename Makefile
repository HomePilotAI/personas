.PHONY: install test build assets assets-placeholder metadata package validate clean all worker-export personas-worker-export worker-bundle

# Install Node and Python dependencies.
install:
	npm install
	pip install -r requirements.txt

# End-to-end pipeline: assets + metadata + packaging + validation.
all: assets metadata package validate

# Generate avatar PNGs, gallery WebP previews and thumbnails.
# Uses the realistic generator (HomePilot avatar-service quickface chain):
#   1. local StyleGAN2 if STYLEGAN_ENABLED + weights reachable
#   2. thispersondoesnotexist.com when ENABLE_WEB_FACES=true (or
#      pre-cached at .cache/faces/<id>.jpg from a prior run)
#   3. branded gradient + glyph placeholder
# This keeps cached realistic faces under .cache/faces/ from being
# silently overwritten by the placeholder pipeline. CI without the
# cache still produces clean placeholder assets.
assets:
	python3 scripts/generate_avatars_realistic.py

# Placeholder-only assets (legacy entrypoint). Run this when you want
# to force every persona back to the gradient+glyph composition.
assets-placeholder:
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

# ── Cloudflare Worker export (homepilot-persona-gallery) ───────────────
# Mirrors the persona pack into the Worker URL shape (/p/<id>/<v>,
# /v/<id>/<v>, /c/<id>/<v>) so the maintainer of the live gallery can
# ingest a single bundle into R2 in one paste / curl.

# Rewrite paths and stage every artefact under dist/worker/. Default mode
# is 'merge' so the bundled registry already contains both the live
# community personas + our 10 additive ones (total: 24). Run with
# WORKER_MODE=additive to publish only our entries.
WORKER_MODE ?= merge
worker-export: package  ## Stage dist/worker/ (registry + binaries) for the Worker R2 bucket
	python3 scripts/export_for_worker.py --mode=$(WORKER_MODE)

personas-worker-export: worker-export worker-bundle  ## Alias: stage + tarball

# Single tarball the maintainer downloads from CI and unpacks into R2.
worker-bundle: ## Tar dist/worker into dist/worker-bundle.tar.gz
	@if [ ! -d dist/worker ]; then echo "(run 'make worker-export' first)"; exit 1; fi
	tar -czf dist/worker-bundle.tar.gz -C dist worker
	@printf "wrote: %s (%s bytes)\n" \
	  dist/worker-bundle.tar.gz "$$(stat -c%s dist/worker-bundle.tar.gz 2>/dev/null || stat -f%z dist/worker-bundle.tar.gz)"
