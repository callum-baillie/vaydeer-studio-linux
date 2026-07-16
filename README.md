# Vaydeer Studio

Vaydeer Studio is a Linux-first desktop configurator for Vaydeer macro keypads.
It targets the Vaydeer JP-1011 nine-key keypad first, using a read-only HID
keepalive that makes its normal keyboard interface stay active on Linux. The
application separates portable onboard mappings from Linux-side actions,
creates a backup before every eligible write, previews the diff, and verifies a
write by reading it back.

## Screenshots

![Vaydeer Studio overview in the dark theme](screenshots/ui-overview-dark.png)

![On-device key editor in the dark theme](screenshots/ui-on-device-keys-dark.png)

![Linux actions in the dark theme](screenshots/ui-linux-actions-dark.png)

## Why this exists

The JP-1011's normal keyboard reports can stop unless its vendor asynchronous
HID interface is held open. Opening the correct interface read-only is enough;
no vendor command, write, or read loop is required. Vaydeer Studio discovers
that interface dynamically rather than relying on a `/dev/hidrawN` number, and
keeps it open through a small user service.

## How it works

**Vaydeer Studio** is the desktop app used to inspect the keypad, edit drafts,
and manage profiles. It can be closed after configuration.

**On-device keys** are written to keypad memory. Supported keyboard, media,
system, layer, and layer-name mappings work on a compatible computer without
Studio or Linux installed.

**Linux actions** stay on this Linux computer. The lightweight **Background
service** (`vaydeer-studiod`) keeps the JP-1011 active on Linux and executes
actions such as launching applications or opening URLs after Studio is closed.
They never modify keypad memory.

## Features

- Device inspection, layers, layer names, and current mappings.
- A physical 3-by-3 JP-1011 editor with readable value choices, keyboard
  capture, layer controls, device-baseline versus pending-sync indicators, and
  a diff review.
- Stable onboard single keys, modifiers, combinations, media/system keys, and
  disabled keys for the observed JP-1011 firmware `1.0.2` / bootloader `0.2.1`.
- Timestamped open JSON backups, restore staging, dry-run packets, and
  read-back verification.
- Portable JSON/YAML profiles and an XDG-backed profile library.
- Platform-targeted presets for Codex, ChatGPT, Photoshop, and Illustrator,
  with Linux, macOS, and Windows shortcut variants.
- Linux-side launch, URL, file, directory, command, notification, and script
  bindings handled by `vaydeer-studiod`, with editable press/release triggers
  and a structured argument array. Text injection remains backend-dependent.
- Host-local user-service state for installation, current runtime, control
  socket reachability, and login startup, with a no-`sudo` user-unit install.
- Mock JP-1011 mode for trying the complete interface without hardware.
- Live tester, diagnostics export, a scoped udev rule, desktop entry, MIME
  registration, and systemd user service.

## Supported devices

| Device / firmware | Read | On-device writes | Layout |
| --- | --- | --- | --- |
| JP-1011, firmware `1.0.2`, bootloader `0.2.1` | Yes | Stable basic mappings | Verified 3 by 3 |
| Same VID:PID, unknown firmware | Yes, guarded | Disabled | Detected key count |
| One-, four-, and six-key protocol variants | Adapter/layout scaffold | Disabled pending capture validation | Generic/provisional |

The project probes device type, subtype, firmware, and bootloader. It does not
assume public `1.1.2` firmware behaves like the observed `1.0.2` device.

## Safety

Firmware updating is intentionally absent. Command `0xFC` is rejected by the
protocol core and has regression tests proving it cannot be built. Unknown
commands are rejected too. Before any eligible configuration write, Vaydeer
Studio reads the device, checks capability, backs it up, creates a human
readable diff and packet preview, requires confirmation, commits, reads back,
and compares the result. The desktop UI requires a reviewed diff and a typed
`APPLY` confirmation before a real write; the CLI retains its own explicit
terminal confirmation.

See [docs/safety.md](docs/safety.md) for the full boundary.

## Quick start

Mock mode is the fastest validated route:

```bash
uv sync --extra dev
uv run vaydeer-studio --mock jp1011
```

The current checkout was validated with `uv sync`, `pytest`, Ruff, mypy, the
source/wheel build, offscreen Qt smoke launches, and a normal-user read-only
inspection of an attached JP-1011. For a physical keypad, follow
[docs/installation.md](docs/installation.md).

## Recommended installation

Install [uv](https://docs.astral.sh/uv/), clone this repository, then run:

```bash
uv sync --extra dev
./scripts/install.sh
# Reconnect the keypad after udev reloads its rule, then verify the complete path.
vaydeer-studio-cli doctor
~/.local/bin/vaydeer-studio
```

`install.sh` installs only user integration plus the narrowly scoped udev rule
for VID:PID `0483:5752` interfaces 0 and 2. It requires `sudo` only for that
one udev file and starts the user service. Do not run the desktop application
as root.

### Ubuntu and Debian

Install a current Python 3.11+ and system HID library before using `uv`:

```bash
sudo apt install libhidapi-hidraw0 libegl1 libgl1
uv sync --extra dev
./scripts/install.sh
```

### Fedora

```bash
sudo dnf install hidapi libglvnd-egl mesa-libGL
uv sync --extra dev
./scripts/install.sh
```

### Arch Linux

```bash
sudo pacman -S hidapi mesa
uv sync --extra dev
./scripts/install.sh
```

Distribution package names can vary. The diagnostic screen reports the actual
permission and interface state when a command interface cannot be opened.

### AppImage, Debian package, and Flatpak

`make package` always builds the Python sdist and wheel. Reproducible AppImage,
Debian, and Flatpak scripts/manifests live in `packaging/`, but none of those
native artifacts was produced in this environment because `appimagetool`,
`dh-virtualenv`, and `flatpak-builder` were unavailable. The scripts report
their missing prerequisites rather than claiming a completed package.

### Source installation

Use the quick-start commands for a source checkout. The install script creates
`~/.local/bin/vaydeer-studio`, `~/.local/bin/vaydeer-studiod`, desktop/MIME
entries, and a user unit. `make run` is a mock-mode shortcut.

## First run

1. Open **Overview**. It shows the keypad and Background service state, then
   points to either keypad-memory configuration or Linux-only actions.
2. Open **Setup** when permissions or the service need attention. It safely
   verifies each prerequisite and can install or start the user service. Use
   `./scripts/install.sh` to install the scoped udev rule, then reconnect the
   keypad.
3. Open **On-device keys**, choose a layer and physical key, then use **Read
   from keypad** from the action menu before editing a draft.
4. Select **Review changes** and then **Write to keypad**. The dialog shows the
   backup location and affected keys; a real write requires typing `APPLY` in
   the application and is read back for verification.
5. Use **Linux actions** for work that only runs on this computer. Save those
   actions to a Linux profile; they run while the Background service is ready.
6. Save or export the profile from **Profiles**. Selecting a profile does not
   write it to the keypad automatically.

Every backup is versioned JSON under the XDG data directory, normally
`~/.local/share/Vaydeer Studio/backups`. Restore first stages that backup for
the same review flow.

## Linux actions

Linux actions deliberately live outside keypad firmware. Select a physical key
and layer, create an action in **Linux actions**, then save it to the profile.
The Background service handles the vendor event. Commands use an executable
plus argument array by default; shell execution requires an explicit opt-in in
Advanced mode. The service currently executes `press` and `release` triggers.
These actions need Linux and the running service, unlike stable on-device keys.

## Basic and Advanced modes

Basic mode is the default and contains the normal configuration workflow.
Advanced mode exposes raw reports, documented values, capability notes, and
shell options without changing stored data. The selected mode, theme, and last
page are retained between launches.

## Application presets and portable profiles

The **Profiles** page can start a new JP-1011 profile from Codex, ChatGPT,
Photoshop, or Illustrator presets. Choose **Linux**, **macOS**, or **Windows**
before creating it. The primary modifier is written as `Ctrl` for Linux and
Windows and `Meta` (Command) for macOS, so exported profiles remain explicit
about their target. These presets contain portable onboard shortcuts only;
Linux-side actions are enabled and synchronized to `vaydeer-studiod` only for
profiles whose target is Linux.

On the mapping page, **Capture a key** makes the next computer-keyboard input
explicit. A numeric keypad `7` is captured as `Num 7`, while the ordinary top
row digit remains `7`; the capture message shows the stored JP-1011 value.
While this page is open, pressing a physical keypad key selects that same key
in the editor without writing or recording a live tester event.

## Troubleshooting

If normal key events disappear, check the service:

```bash
systemctl --user status vaydeer-studio.service
vaydeer-studio-cli doctor
vaydeer-studio-cli diagnostics --verbose
```

Reconnect the keypad after installing the udev rule. See
[docs/troubleshooting.md](docs/troubleshooting.md) for permissions and HID
diagnostics, [the live detection report](docs/research/live-device-detection-debug.md)
for the repaired hidapi/sysfs behavior, and export a sanitized diagnostic bundle
from the app.

## Uninstall

```bash
./scripts/uninstall.sh
# Keep the scoped udev rule for another local HID client:
./scripts/uninstall.sh --keep-udev
```

Backups and profiles are retained deliberately.

## Development

```bash
make setup
make lint
make typecheck
make test
make build
make docs
```

Hardware tests are opt-in with `VAYDEER_HARDWARE_TESTS=1`; they never include
firmware commands. [docs/development.md](docs/development.md) explains the
mock transport and test layers, and [docs/interaction-design.md](docs/interaction-design.md)
records the mapping, binding, and profile workflow. Contributions are welcome
under [CONTRIBUTING.md](CONTRIBUTING.md).

## Limitations

Mouse, macro, text, layer/Vaydeer-specific, host-trigger, and unknown vendor
assignments are modeled as experimental only. Their physical payload formats
are not sent because they cannot yet be safely round-tripped. Firmware flashing
and QMK replacement are out of scope. See [docs/device-support.md](docs/device-support.md)
and [docs/research](docs/research) for evidence and unknowns.

## License and acknowledgement

Vaydeer Studio is MIT licensed. It is an original implementation informed by
public projects and locally conducted research; no vendor binaries or copied
unlicensed source are included. See [LICENSE](LICENSE),
[ATTRIBUTION.md](ATTRIBUTION.md), and [docs/research/sources.md](docs/research/sources.md).
