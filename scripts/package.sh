#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"

rm -rf dist
uv build
wheel="$(find dist -maxdepth 1 -type f -name 'vaydeer_studio-*.whl' -print -quit)"
sdist="$(find dist -maxdepth 1 -type f -name 'vaydeer_studio-*.tar.gz' -print -quit)"
[[ -n "$wheel" && -n "$sdist" ]] || { echo "Expected wheel and source archive were not built." >&2; exit 1; }
wheel_name="${wheel##*/}"
sdist_name="${sdist##*/}"
(cd dist && sha256sum "$wheel_name" "$sdist_name" >SHA256SUMS)

uv tool run --from "$wheel" vaydeer-studio-cli --version
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  uv tool run --from "$wheel" vaydeer-studio --mock jp1011 --smoke

echo "Validated release artifacts:"
printf '  %s\n' "$wheel" "$sdist" "dist/SHA256SUMS"
echo "Native AppImage, Debian, and Flatpak bundles are not part of the supported v1 release."
echo "See packaging/README.md for the integration constraints."
