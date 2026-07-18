#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"

rm -rf dist
uv build
wheel="$(find dist -maxdepth 1 -type f -name 'vaydeer_studio-*.whl' -print -quit)"
sdist="$(find dist -maxdepth 1 -type f -name 'vaydeer_studio-*.tar.gz' -print -quit)"
[[ -n "$wheel" && -n "$sdist" ]] || { echo "Expected wheel and source archive were not built." >&2; exit 1; }
install -m 0755 scripts/bootstrap.sh dist/install.sh

uv tool run --from "$wheel" vaydeer-studio-cli --version
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  uv tool run --from "$wheel" vaydeer-studio --mock jp1011 --smoke
./scripts/generate-checksums.sh

echo "Validated release artifacts:"
printf '  %s\n' "$wheel" "$sdist" "dist/install.sh" "dist/SHA256SUMS"
echo "Run 'make appimage' to add the portable x86_64 bundle."
