.PHONY: help install test

help: ## Show available targets
	@echo "MCP server: $(notdir $(CURDIR))"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install JS and Python dependencies required for this server
	@if [ -f package.json ]; then npm install; else echo "No package.json found, skipping npm install"; fi
	@if [ -f ../python_common/requirements.txt ]; then python3 -m pip install -r ../python_common/requirements.txt; else echo "No Python requirements found, skipping pip install"; fi

test: ## Run lightweight server checks
	@if [ -f src/index.py ]; then python3 -m py_compile src/index.py && echo "Python syntax check passed"; else echo "No src/index.py found"; fi
	@if [ -f src/index.js ]; then node --check src/index.js && echo "JavaScript syntax check passed"; else echo "No src/index.js found"; fi
