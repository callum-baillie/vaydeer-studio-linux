#!/usr/bin/env bash
set -euo pipefail

keep_udev=false
while (($#)); do
  case "$1" in
    --keep-udev) keep_udev=true ;;
    -h|--help)
      echo "Usage: ./scripts/uninstall.sh [--keep-udev]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
unit_path="$config_home/systemd/user/vaydeer-studio.service"
had_unit=false

if [[ -e "$unit_path" ]] && command -v systemctl >/dev/null 2>&1; then
  had_unit=true
  systemctl --user disable --now vaydeer-studio.service 2>/dev/null || true
fi
rm -f \
  "$data_home/applications/io.github.callumbaillie.vaydeer-studio.desktop" \
  "$data_home/applications/vaydeer-studio.desktop"
rm -f "$data_home/icons/hicolor/scalable/apps/vaydeer-studio.svg"
rm -f "$data_home/mime/packages/vaydeer-studio-profile.xml"
rm -f "$unit_path"
if [[ "$had_unit" == true ]] && command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload 2>/dev/null || true
fi
if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database "$data_home/mime" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$data_home/applications" >/dev/null 2>&1 || true
fi
if command -v uv >/dev/null 2>&1; then
  uv tool uninstall vaydeer-studio 2>/dev/null || true
else
  rm -f "$HOME/.local/bin/vaydeer-studio" "$HOME/.local/bin/vaydeer-studio-cli" \
    "$HOME/.local/bin/vaydeer-studiod"
  echo "uv was not found; remove its Vaydeer Studio tool environment manually if it remains." >&2
fi

if [[ "$keep_udev" != true && -e /etc/udev/rules.d/99-vaydeer-studio.rules ]]; then
  command -v sudo >/dev/null 2>&1 || { echo "sudo is required to remove the udev rule." >&2; exit 1; }
  sudo rm -f /etc/udev/rules.d/99-vaydeer-studio.rules
  if command -v udevadm >/dev/null 2>&1; then
    sudo udevadm control --reload-rules
  fi
fi

echo "Removed Vaydeer Studio integration. Profiles, backups, and diagnostics were retained."
