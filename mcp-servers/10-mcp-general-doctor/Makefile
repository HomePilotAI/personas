.PHONY: help install test test-syntax pytest

help: ## Show available targets
	@echo "MCP server: $(notdir $(CURDIR))"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the adapter (editable) + dev extras (pytest, ruff)
	python3 -m pip install -e ".[dev]"

test: pytest ## Alias for `make pytest` (preferred CI target)

test-syntax: ## Lightweight syntax check (legacy; kept for parity with other servers)
	@if [ -f src/index.py ]; then python3 -m py_compile src/index.py && echo "Python syntax check passed"; else echo "No src/index.py found"; fi

pytest: ## Run the full pytest suite (unit + adversarial + protocol)
	cd $(CURDIR) && python3 -m pytest -q tests/
