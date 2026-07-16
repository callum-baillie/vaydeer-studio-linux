#!/usr/bin/env bash
set -euo pipefail

systemctl --user disable --now vaydeer-studio.service 2>/dev/null || true
rm -f "$HOME/.local/bin/vaydeer-studio" "$HOME/.local/bin/vaydeer-studiod"
rm -f "$HOME/.local/share/applications/vaydeer-studio.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/vaydeer-studio.svg"
rm -f "$HOME/.local/share/mime/packages/vaydeer-studio-profile.xml"
rm -f "$HOME/.config/systemd/user/vaydeer-studio.service"
update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
systemctl --user daemon-reload

if [[ "${1:-}" == "--udev" ]]; then
  sudo rm -f /etc/udev/rules.d/99-vaydeer-studio.rules
  sudo udevadm control --reload-rules
fi

echo "Removed user integration. Backups remain in the XDG data directory."
