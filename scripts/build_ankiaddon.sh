#!/usr/bin/env bash
set -euo pipefail

output_path="${1:-dist/web_embed_tools.ankiaddon}"
mkdir -p "$(dirname "$output_path")"

python3 -m zipfile -c "$output_path" \
  manifest.json \
  __init__.py \
  wikipedia_embed_core.py

printf 'Built %s\n' "$output_path"
