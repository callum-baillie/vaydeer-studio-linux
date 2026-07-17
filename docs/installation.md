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

The recommended workflow downloads a versioned script to a temporary file so
you can inspect exactly what will run. Run it as your normal desktop user, not
with `sudo`:

```bash
(
  set -e
  installer="$(mktemp)"
  trap 'rm -f "$installer"' EXIT
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    https://raw.githubusercontent.com/callum-baillie/vaydeer-studio-linux/v1.0.2/scripts/bootstrap.sh \
    --output "$installer"
  printf '%s  %s\n' \
    1de1f5a319c83ec1e787b48ee86e477366c0b9a0a9e40a10956d25b90591ee9a \
    "$installer" | sha256sum --check -
  less "$installer"
  bash "$installer"
)
```

The command verifies the downloaded script before displaying or executing it.
The installer then prints its detected distribution, exact package commands,
app version, udev choice, and Background service choice before asking to
continue. It supports automatic dependency installation on:

- Ubuntu 22.04+, Debian 12+, Linux Mint, and compatible derivatives.
- Fedora and compatible derivatives.
- Arch Linux and compatible derivatives.

For a shorter interactive form after you trust the versioned source URL:

```bash
curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
  https://raw.githubusercontent.com/callum-baillie/vaydeer-studio-linux/v1.0.2/scripts/bootstrap.sh | bash
```

The script reads confirmation from the terminal even when its source arrives on
standard input. For unattended use, add `bash -s -- --yes` only after reviewing
the plan and script.

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
curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
  https://raw.githubusercontent.com/callum-baillie/vaydeer-studio-linux/v1.0.2/scripts/bootstrap.sh \
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

## Manual Installation

Install distribution libraries:

```bash
# Ubuntu 22.04+, Debian 12+, Linux Mint
sudo apt-get update
sudo apt-get install -y ca-certificates curl libhidapi-hidraw0 libegl1 libgl1 \
  libxcb-cursor0 libxkbcommon-x11-0

# Fedora
sudo dnf install -y ca-certificates curl hidapi libglvnd-egl libglvnd-glx \
  xcb-util-cursor libxkbcommon-x11

# Arch Linux
sudo pacman -S --needed ca-certificates curl hidapi mesa libglvnd \
  xcb-util-cursor libxkbcommon-x11
```

Install the same pinned [uv](https://docs.astral.sh/uv/getting-started/installation/)
release used by the bootstrap, then install from GitHub:

```bash
(
  set -e
  uv_installer="$(mktemp)"
  trap 'rm -f "$uv_installer"' EXIT
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    https://github.com/astral-sh/uv/releases/download/0.11.29/uv-installer.sh \
    --output "$uv_installer"
  printf '%s  %s\n' \
    504a79fd2ed0dcd47e7f04f0792cfd0871f62e24a7fe40fa8ae0f563a369f2bd \
    "$uv_installer" | sha256sum --check -
  less "$uv_installer"
  env UV_NO_MODIFY_PATH=1 sh "$uv_installer"
)
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

The bootstrap and source installers are idempotent. To update from a release,
run the versioned installer shown in that release's README. To update from a
checkout:

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

`make package` builds and smoke-tests the wheel and source archive, then writes
their hashes to `dist/SHA256SUMS`. These are the supported v1 release artifacts.
Native AppImage, Debian, RPM, and Flatpak bundles are not released; see
[../packaging/README.md](../packaging/README.md).
