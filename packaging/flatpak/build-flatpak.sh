#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$root"
command -v flatpak-builder >/dev/null || { echo "Install flatpak-builder first." >&2; exit 2; }
command -v flatpak >/dev/null || { echo "Install flatpak first." >&2; exit 2; }

build_dir="packaging/flatpak/build"
repository="packaging/flatpak/repo"
bundle="dist/VaydeerStudio.flatpak"
flatpak-builder --force-clean "$build_dir" packaging/flatpak/org.vaydeer.VaydeerStudio.yml
flatpak build-export "$repository" "$build_dir"
flatpak build-bundle "$repository" "$bundle" org.vaydeer.VaydeerStudio
echo "Built $bundle"
