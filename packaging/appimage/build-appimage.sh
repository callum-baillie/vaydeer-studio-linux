#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$root"
command -v appimagetool >/dev/null || { echo "Install appimagetool first." >&2; exit 2; }
echo "The staging manifest is ready, but a portable Python/Qt runtime is required."
echo "Use appimage-builder with Python 3.11+, PySide6, and hidapi bundled before invoking appimagetool."
echo "No incomplete AppImage is produced by this script."
