#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
uv build

if command -v appimagetool >/dev/null 2>&1; then
  packaging/appimage/build-appimage.sh
else
  echo "AppImage not built: install appimagetool, then run packaging/appimage/build-appimage.sh"
fi

if command -v dh_virtualenv >/dev/null 2>&1 && command -v dpkg-buildpackage >/dev/null 2>&1; then
  packaging/deb/build-deb.sh
else
  echo "Debian package not built: install dh-virtualenv and dpkg-dev, then run packaging/deb/build-deb.sh"
fi

if command -v flatpak-builder >/dev/null 2>&1; then
  packaging/flatpak/build-flatpak.sh
else
  echo "Flatpak bundle not built: install flatpak-builder, then run packaging/flatpak/build-flatpak.sh"
fi
