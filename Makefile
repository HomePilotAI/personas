.PHONY: install test build clean

# Install Node dependencies for the root and workspace packages
install:
	npm install

# Run validation scripts to ensure personas and MCP servers are present
test:
	npm test

# Dummy build step – extend with real packaging logic as needed
build:
	echo "No build step defined."

# Clean built artifacts
clean:
	rm -rf dist