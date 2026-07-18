#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
install_udev=true
install_service=true

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [--no-udev] [--no-service]

Installs Vaydeer Studio into an isolated uv tool environment and adds the
current user's desktop integration. The default installation also adds the
scoped udev rule and enables the per-user Background service.

  --no-udev    Do not install or reload the root-owned device permission rule.
  --no-service Do not install, enable, or start the systemd user service.
EOF
}

while (($#)); do
  case "$1" in
    --no-udev) install_udev=false ;;
    --no-service) install_service=false ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Vaydeer Studio's host integration is supported on Linux only." >&2
  exit 1
fi
if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Run this installer as your desktop user, not as root." >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi
if [[ "$install_service" == true ]]; then
  command -v systemctl >/dev/null 2>&1 || {
    echo "systemctl is required for the Background service; use --no-service to install Studio only." >&2
    exit 1
  }
  systemctl --user show-environment >/dev/null 2>&1 || {
    echo "The current session has no usable systemd user manager; use --no-service to install Studio only." >&2
    exit 1
  }
fi
if [[ "$install_udev" == true ]]; then
  command -v sudo >/dev/null 2>&1 || {
    echo "sudo is required only for the udev rule; use --no-udev to skip that step." >&2
    exit 1
  }
  command -v udevadm >/dev/null 2>&1 || {
    echo "udevadm is required to install device permissions; use --no-udev to skip that step." >&2
    exit 1
  }
  sudo -v
fi

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
applications_dir="$data_home/applications"
icons_dir="$data_home/icons/hicolor/scalable/apps"
mime_dir="$data_home/mime/packages"
unit_dir="$config_home/systemd/user"

cd "$root"
echo "Installing the application environment..."
uv tool install --force "$root"
tool_bin="$(uv tool dir --bin)"
studio_exec="$tool_bin/vaydeer-studio"
daemon_exec="$tool_bin/vaydeer-studiod"
cli_exec="$tool_bin/vaydeer-studio-cli"
for executable in "$studio_exec" "$daemon_exec" "$cli_exec"; do
  [[ -x "$executable" ]] || { echo "Expected installed executable is missing: $executable" >&2; exit 1; }
done

install -d "$applications_dir" "$icons_dir" "$mime_dir"
desktop_tmp="$(mktemp)"
service_tmp="$(mktemp)"
trap 'rm -f "$desktop_tmp" "$service_tmp"' EXIT
escaped_studio="$(printf '%s' "$studio_exec" | sed 's/[\/&]/\\&/g')"
desktop_id="io.github.callumbaillie.vaydeer-studio"
sed "s/^Exec=.*/Exec=\"$escaped_studio\"/" "packaging/desktop/$desktop_id.desktop" >"$desktop_tmp"
rm -f "$applications_dir/vaydeer-studio.desktop"
install -m 0644 "$desktop_tmp" "$applications_dir/$desktop_id.desktop"
install -m 0644 src/vaydeer_studio/resources/icons/vaydeer-studio.svg "$icons_dir/vaydeer-studio.svg"
install -m 0644 packaging/desktop/vaydeer-studio-profile.xml "$mime_dir/vaydeer-studio-profile.xml"

if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database "$data_home/mime" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q "$data_home/icons/hicolor" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$applications_dir" >/dev/null 2>&1 || true
fi

if [[ "$install_service" == true ]]; then
  install -d "$unit_dir"
  escaped_daemon="$(printf '%s' "$daemon_exec" | sed 's/[\/&]/\\&/g')"
  sed "s/^ExecStart=.*/ExecStart=\"$escaped_daemon\" --log-level info/" \
    packaging/systemd/vaydeer-studio.service >"$service_tmp"
  install -m 0644 "$service_tmp" "$unit_dir/vaydeer-studio.service"
  systemctl --user daemon-reload
  systemctl --user enable vaydeer-studio.service
  systemctl --user restart vaydeer-studio.service
fi

if [[ "$install_udev" == true ]]; then
  sudo install -Dm0644 packaging/udev/99-vaydeer-studio.rules \
    /etc/udev/rules.d/99-vaydeer-studio.rules
  sudo udevadm control --reload-rules
fi

echo
"$cli_exec" --version
echo "Installed Vaydeer Studio."
if [[ "$install_service" == true ]]; then
  echo "Background service: enabled and started or restarted for this user."
else
  echo "Background service: skipped. Linux actions and the automatic keepalive are unavailable."
fi
if [[ "$install_udev" == true ]]; then
  echo "Device permissions: installed. Reconnect the keypad before running diagnostics."
else
  echo "Device permissions: skipped. Install the udev rule before using physical hardware."
fi
echo "Launch: $studio_exec"
echo "Verify: $cli_exec doctor"
