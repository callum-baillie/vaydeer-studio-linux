#!/usr/bin/env bash
set -euo pipefail

required=(README.md ATTRIBUTION.md docs/installation.md docs/user-guide.md docs/troubleshooting.md docs/protocol.md docs/bindings.md docs/research/overview.md docs/research/sources.md)
for file in "${required[@]}"; do
  test -s "$file"
done
echo "Documentation checks passed."
