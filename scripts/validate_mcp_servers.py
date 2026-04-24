#!/usr/bin/env python3
"""
validate_mcp_servers.py

This script performs a simple validation on the MCP servers contained in the
`mcp-servers/` directory.  It checks that each server has the expected
files such as `src/index.js` (or .ts) and `server.json`.  If any check
fails the script exits with a non‑zero status.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVERS_DIR = os.path.join(ROOT, 'mcp-servers')

def main() -> None:
    if not os.path.isdir(SERVERS_DIR):
        print(f"MCP servers directory not found: {SERVERS_DIR}")
        sys.exit(1)

    success = True
    for server_dir in sorted(os.listdir(SERVERS_DIR)):
        server_path = os.path.join(SERVERS_DIR, server_dir)
        if not os.path.isdir(server_path):
            continue
        index_js = os.path.join(server_path, 'src', 'index.js')
        index_ts = os.path.join(server_path, 'src', 'index.ts')
        if not (os.path.exists(index_js) or os.path.exists(index_ts)):
            print(f"Missing index.js or index.ts in {server_path}")
            success = False
        server_json = os.path.join(server_path, 'server.json')
        if not os.path.exists(server_json):
            print(f"Missing server.json in {server_path}")
            success = False
    if not success:
        sys.exit(1)
    print("All MCP servers validated successfully.")

if __name__ == '__main__':
    main()