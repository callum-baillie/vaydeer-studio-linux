#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/" >&2
  exit 1
fi

cd "$root"
uv sync --extra dev
install -d "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps" "$HOME/.local/share/mime/packages" "$HOME/.config/systemd/user"
ln -sfn "$root/.venv/bin/vaydeer-studio" "$HOME/.local/bin/vaydeer-studio"
ln -sfn "$root/.venv/bin/vaydeer-studiod" "$HOME/.local/bin/vaydeer-studiod"
install -m 0644 packaging/desktop/vaydeer-studio.desktop "$HOME/.local/share/applications/vaydeer-studio.desktop"
install -m 0644 packaging/desktop/vaydeer-studio.svg "$HOME/.local/share/icons/hicolor/scalable/apps/vaydeer-studio.svg"
install -m 0644 packaging/desktop/vaydeer-studio-profile.xml "$HOME/.local/share/mime/packages/vaydeer-studio-profile.xml"
install -m 0644 packaging/systemd/vaydeer-studio.service "$HOME/.config/systemd/user/vaydeer-studio.service"

update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
systemctl --user daemon-reload
sudo install -Dm0644 packaging/udev/99-vaydeer-studio.rules /etc/udev/rules.d/99-vaydeer-studio.rules
sudo udevadm control --reload-rules
systemctl --user enable --now vaydeer-studio.service

echo "Installed Vaydeer Studio and started the user keepalive service."
echo "Reconnect the keypad so the udev rule is applied to its current hidraw nodes, then run:"
echo "  vaydeer-studio-cli doctor"
echo "  vaydeer-studio"
