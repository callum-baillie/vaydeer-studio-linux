#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

export HOME="$test_root/home"
export XDG_DATA_HOME="$test_root/data"
export XDG_CONFIG_HOME="$test_root/config"
export UV_TOOL_DIR="$test_root/tools"
export UV_TOOL_BIN_DIR="$test_root/bin"
export UV_LINK_MODE=copy
mkdir -p "$HOME"

"$root/scripts/install.sh" --no-udev --no-service
test -x "$UV_TOOL_BIN_DIR/vaydeer-studio"
test -x "$UV_TOOL_BIN_DIR/vaydeer-studio-cli"
test -x "$UV_TOOL_BIN_DIR/vaydeer-studiod"
grep -F "Exec=\"$UV_TOOL_BIN_DIR/vaydeer-studio\"" \
  "$XDG_DATA_HOME/applications/io.github.callumbaillie.vaydeer-studio.desktop" >/dev/null
"$UV_TOOL_BIN_DIR/vaydeer-studio-cli" --version
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  "$UV_TOOL_BIN_DIR/vaydeer-studio" --mock jp1011 --smoke
"$root/scripts/uninstall.sh" --keep-udev
test ! -e "$UV_TOOL_BIN_DIR/vaydeer-studio"

echo "Isolated user installation smoke test passed."
