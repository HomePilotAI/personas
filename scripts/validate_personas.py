#!/usr/bin/env python3
"""
validate_personas.py

This script performs a simple validation on the personas contained in the
`personas/` directory.  It checks that each persona has a `hpersona/`
directory with the expected subfolders and files.  If any check fails
the script will exit with a non‑zero status.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_DIR = os.path.join(ROOT, 'personas')

def main() -> None:
    if not os.path.isdir(PERSONAS_DIR):
        print(f"Personas directory not found: {PERSONAS_DIR}")
        sys.exit(1)

    success = True
    for persona_dir in sorted(os.listdir(PERSONAS_DIR)):
        persona_path = os.path.join(PERSONAS_DIR, persona_dir)
        if not os.path.isdir(persona_path):
            continue
        hpersona_path = os.path.join(persona_path, 'hpersona')
        required_items = ['manifest.json', 'blueprint', 'dependencies', 'assets', 'preview']
        for item in required_items:
            p = os.path.join(hpersona_path, item)
            if not os.path.exists(p):
                print(f"Missing {item} in {hpersona_path}")
                success = False
        # Ensure blueprint and dependencies are directories
        for subdir in ['blueprint', 'dependencies', 'assets', 'preview']:
            p = os.path.join(hpersona_path, subdir)
            if not os.path.isdir(p):
                print(f"Expected directory missing or not a directory: {p}")
                success = False
    if not success:
        sys.exit(1)
    print("All personas validated successfully.")

if __name__ == '__main__':
    main()