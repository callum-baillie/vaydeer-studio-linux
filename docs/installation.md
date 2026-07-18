# Installation

Vaydeer Studio uses `uv tool` for an isolated per-user application environment.
It does not install packages into the system Python, and downloaded installation
sources are removed after a successful install.

## Requirements

- A Linux graphical desktop using Wayland or X11.
- udev and logind `uaccess` ACL support for physical keypad access.
- A systemd user manager for the Background service.
- EGL/GL, X11 compatibility, and hidapi system libraries.
- `curl` with HTTPS support.

## Recommended Install

Run the latest release installer as your normal desktop user, not with `sudo`:

```bash
curl -fsSL https://github.com/callum-baillie/vaydeer-studio-linux/releases/latest/download/install.sh | bash
```

The installer prints its detected distribution, exact package commands, app
version, udev choice, and Background service choice before asking to continue.
It reads confirmation from the terminal even though the script arrives on
standard input. It supports automatic dependency installation on:

- Ubuntu 22.04+, Debian 12+, Linux Mint, and compatible derivatives.
- Fedora and compatible derivatives.
- Arch Linux and compatible derivatives.

### Review and verify first

To inspect the installer and verify it against the release manifest:

```bash
(
  set -e
  directory="$(mktemp -d)"
  trap 'rm -rf "$directory"' EXIT
  base=https://github.com/callum-baillie/vaydeer-studio-linux/releases/latest/download
  curl -fsSL "$base/install.sh" -o "$directory/install.sh"
  curl -fsSL "$base/SHA256SUMS" -o "$directory/SHA256SUMS"
  (cd "$directory" && grep '  install.sh$' SHA256SUMS | sha256sum --check -)
  less "$directory/install.sh"
  bash "$directory/install.sh"
)
```

For unattended use, add `bash -s -- --yes` only after reviewing the plan and
script. A pinned release uses
`https://github.com/callum-baillie/vaydeer-studio-linux/releases/download/v1.1.0/install.sh`.

### What the bootstrap does

1. Refuses root execution and non-Linux hosts.
2. Reads `/etc/os-release` and selects a supported package manager.
3. Checks that the requested systemd user manager and udev tools are available.
4. Shows all planned system changes and asks for confirmation.
5. Installs the distribution's HID and Qt runtime libraries.
6. Uses an existing `uv`, or downloads pinned `uv 0.11.29` and verifies its
   embedded SHA-256 checksum before execution.
7. Downloads the pinned Vaydeer Studio source archive and verifies it against
   the release's `SHA256SUMS` file.
8. Installs the application, desktop integration, scoped udev rule, and
   per-user Background service through `scripts/install.sh`.
9. Deletes temporary installer and source files.

The script uses HTTPS-only redirects, fails on HTTP errors, retries transient
downloads, never uses `eval`, and executes package-manager commands as argument
arrays. `sudo` is limited to system packages and the udev rule. The application,
CLI, and Background service run as the desktop user.

## Installer Options

Pass options after `bash -s --` when piping:

```bash
curl -fsSL \
  https://github.com/callum-baillie/vaydeer-studio-linux/releases/latest/download/install.sh \
  | bash -s -- --no-service
```

| Option | Effect |
| --- | --- |
| `--yes` | Accept the displayed plan without an interactive prompt. |
| `--no-deps` | Skip distribution package installation. Required on unsupported distributions after installing dependencies manually. |
| `--no-udev` | Skip the root-owned device permission rule. Physical hardware access may fail. |
| `--no-service` | Skip the Background service. Linux actions and automatic keepalive are unavailable after Studio closes. |
| `--print-plan` | Detect the host and print the plan without downloading or changing anything. |

Options can be combined. Use `--no-service` for a non-systemd desktop session
and `--no-udev` where device permissions are centrally administered.

## Build and Install from Source

Install distribution libraries:

```bash
# Ubuntu 22.04+, Debian 12+, Linux Mint
sudo apt-get update
sudo apt-get install -y ca-certificates curl fontconfig libdbus-1-3 libglib2.0-0 libhidapi-hidraw0 libegl1 libgl1 \
  libxcb-cursor0 libxkbcommon-x11-0

# Fedora
sudo dnf install -y ca-certificates curl dbus-libs fontconfig glib2 hidapi libglvnd-egl libglvnd-glx \
  xcb-util-cursor libxkbcommon-x11

# Arch Linux
sudo pacman -S --needed ca-certificates curl dbus fontconfig glib2 hidapi mesa libglvnd \
  xcb-util-cursor libxkbcommon-x11
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then clone,
test, and run the application without touching host integration:

```bash
git clone https://github.com/callum-baillie/vaydeer-studio-linux.git
cd vaydeer-studio-linux
uv sync --extra dev
make lint typecheck test
uv run vaydeer-studio --mock jp1011
```

Install the tested checkout for the current user:

```bash
./scripts/install.sh
```

The installer:

1. Builds and installs Vaydeer Studio in uv's persistent tool directory.
2. Exposes `vaydeer-studio`, `vaydeer-studio-cli`, and `vaydeer-studiod` in
   uv's user executable directory, normally `~/.local/bin`.
3. Installs the desktop entry, icon, and profile MIME metadata under the XDG
   user data directory.
4. Generates a systemd user unit with the actual installed daemon path, then
   enables and starts or restarts it.
5. Uses `sudo` only to install the scoped udev rule and reload udev.

The application and service must not run as root.

## First Hardware Check

Reconnect the keypad once so the new udev rule applies, then run:

```bash
~/.local/bin/vaydeer-studio-cli doctor
systemctl --user status vaydeer-studio.service
~/.local/bin/vaydeer-studio
```

`doctor` dynamically checks the vendor command interface, read-only event
interface, normal-user access, service socket, and a safe device-information
read. It never sends configuration writes or firmware commands. A fully ready
result reports `root_cause: ready`.

## Source Installer Options

Install the desktop app without changing root-owned udev configuration:

```bash
./scripts/install.sh --no-udev
```

Install Studio without the Background service:

```bash
./scripts/install.sh --no-service
```

The second form is useful for a restricted or non-systemd session, but normal
JP-1011 keyboard activation and Linux actions will not be maintained after
Studio closes. Options may be combined.

## Permissions

`packaging/udev/99-vaydeer-studio.rules` grants the active local-seat user a
`uaccess` ACL with mode `0660`. It matches HID parent VID:PID `0483:5752` and
only USB interfaces 0 and 2. It does not use mode `0666`, depend on a
distribution-specific group, or assume a hidraw node number.

Systems without logind `uaccess` support need a locally administered limited
group rule. Do not broaden access to every hidraw device.

## Update

The installer is idempotent. Rerun the same command to update to the latest
release:

```bash
curl -fsSL https://github.com/callum-baillie/vaydeer-studio-linux/releases/latest/download/install.sh | bash
```

The isolated application environment and desktop files are replaced, and the
Background service is restarted. Profiles, backups, preferences, and keypad
mappings are preserved. No keypad mapping is written during an update.

Use a versioned `releases/download/vX.Y.Z/install.sh` URL to pin or roll back.
From a checkout:

```bash
git pull --ff-only
./scripts/install.sh
```

Reconnect the keypad only when the udev rule changed.

## AppImage

The supported x86_64 AppImage contains Python 3.11, PySide6, hidapi, and
Vaydeer Studio. It is built as an AppDir with a checksum-pinned `appimagetool`
and type-2 runtime, embeds GitHub zsync update information, and is validated with
CLI and offscreen mock UI smoke tests.

The bundle relies on the standard Fontconfig, D-Bus, GLib, OpenGL/EGL,
XCB-cursor, and XKB libraries listed under **Build and Install from Source**.
They are normally present on a Linux desktop and are installed explicitly by
the one-line installer.

```bash
curl -fLO https://github.com/callum-baillie/vaydeer-studio-linux/releases/latest/download/Vaydeer_Studio-x86_64.AppImage
chmod +x Vaydeer_Studio-x86_64.AppImage
./Vaydeer_Studio-x86_64.AppImage
```

The bundle cannot install a host udev rule by itself. Without an existing rule,
physical HID access remains unavailable. The **Setup** page can install a user
service that points to the AppImage's stable filesystem location, so move the
file to its final location before enabling that service.

## Uninstall

From a checkout or release source archive:

```bash
./scripts/uninstall.sh
```

To retain the permission rule for another compatible local tool:

```bash
./scripts/uninstall.sh --keep-udev
```

Without the source archive, remove the same integration directly:

```bash
systemctl --user disable --now vaydeer-studio.service
rm -f ~/.config/systemd/user/vaydeer-studio.service
systemctl --user daemon-reload
uv tool uninstall vaydeer-studio
sudo rm -f /etc/udev/rules.d/99-vaydeer-studio.rules
sudo udevadm control --reload-rules
```

User data is deliberately retained. By default, profiles, backups, and
diagnostics are under `~/.local/share/Vaydeer Studio/`; preferences are under
the platform's Qt user configuration location.

## Package Status

`make package` builds and smoke-tests the wheel, source archive, and release
installer. `make appimage` also builds and smoke-tests the x86_64 AppImage and
zsync metadata. Every artifact is covered by `dist/SHA256SUMS`.

Native Debian, RPM, Arch, and Flatpak packages are not released. They require
separate distro-native dependency, upgrade, user-service, and udev testing; an
untested package would be less reliable than the validated installer and
AppImage. See [../packaging/README.md](../packaging/README.md).
