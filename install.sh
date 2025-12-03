#!/bin/bash
set -e
rm -rf ./build ./dist
uv sync
uv run pyinstaller ted.py --onefile
chmod +x ./dist/ted
sudo cp -r ./dist/ted ~/.local/bin
mkdir -p ~/.ted

