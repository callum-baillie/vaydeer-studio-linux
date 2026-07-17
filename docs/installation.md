# Installation

Vaydeer Studio 1.0 uses `uv tool` for an isolated per-user application
environment. It does not install packages into the system Python, and the
source checkout can be removed after installation.

## Requirements

- A Linux graphical desktop using Wayland or X11.
- udev and logind `uaccess` ACL support for physical keypad access.
- A systemd user manager for the Background service.
- EGL/GL and hidapi system libraries.
- [uv](https://docs.astral.sh/uv/getting-started/installation/).

The official uv installer is:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install distribution libraries first:

```bash
# Ubuntu 22.04+, Debian 12+, Linux Mint
sudo apt update
sudo apt install libhidapi-hidraw0 libegl1 libgl1

# Fedora
sudo dnf install hidapi libglvnd-egl libglvnd-glx

# Arch Linux
sudo pacman -S hidapi mesa libglvnd
```

Then install from GitHub:

```bash
git clone https://github.com/callum-baillie/vaydeer-studio-linux.git
cd vaydeer-studio-linux
./scripts/install.sh
```

The installer:

1. Builds and installs Vaydeer Studio in uv's persistent tool directory.
2. Exposes `vaydeer-studio`, `vaydeer-studio-cli`, and `vaydeer-studiod` in
   uv's user executable directory, normally `~/.local/bin`.
3. Installs the desktop entry, icon, and profile MIME metadata under the XDG
   user data directory.
4. Generates a systemd user unit with the actual installed daemon path, then
   enables and starts it.
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

## Install Options

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

The installer is idempotent and replaces the isolated tool environment and
integration files:

```bash
git pull --ff-only
./scripts/install.sh
```

Reconnect the keypad only when the udev rule changed. A service-only update can
be applied with `systemctl --user restart vaydeer-studio.service`.

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

`make package` builds and smoke-tests the wheel and source archive. These are
the supported v1 release artifacts. Native AppImage, Debian, RPM, and Flatpak
bundles are not released; see [../packaging/README.md](../packaging/README.md).
