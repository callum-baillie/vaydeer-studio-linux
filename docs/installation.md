# Installation

Vaydeer Studio is developed and tested as a source installation using `uv`.
It needs Python 3.11+, a working Qt/GL desktop stack, and hidapi.

```bash
git clone <your Vaydeer Studio remote>
cd vaydeer-studio-linux
uv sync --extra dev
./scripts/install.sh
```

The script installs user-level launchers, desktop/MIME files, and starts a
systemd user service. It prompts for `sudo` only to install
`/etc/udev/rules.d/99-vaydeer-studio.rules`, scoped to the Vaydeer `0483:5752`
command and event interfaces. It never runs the GUI with elevated privileges.
Reconnect the keypad after the rule reloads, then verify the user-visible state:

```bash
vaydeer-studio-cli doctor
systemctl --user status vaydeer-studio.service
~/.local/bin/vaydeer-studio
```

`doctor` checks the dynamically selected vendor command interface, the
read-only event interface, normal-user access, the service socket, and a safe
`0x60` device-information read. It never sends configuration or firmware
commands. A healthy result has `"root_cause": "ready"` and `"ready": true`.

On first launch, use **Overview** to see the keypad and Background service
state. Open **Setup** for a short checklist when the service, permission rule,
or connection needs attention. Basic mode uses plain-language labels; the
technical service name `vaydeer-studiod` remains available in Advanced mode and
in diagnostics.

For a no-hardware demo, run `uv run vaydeer-studio --mock jp1011`.

## Permissions

The udev rule uses `TAG+="uaccess"` and mode `0660`, with `plugdev` as a
distribution fallback. It does not use `0666` or grant access to unrelated
HID devices. The rules match the HID parent VID:PID and only USB interface `0`
or `2`; they do not assume a `hidraw` number. On systems without `plugdev`,
adjust the group to the distribution-appropriate limited group before
installing the rule.

## Repairing an existing checkout

For a stale user unit or an older udev rule, rerun the installer from the
checkout, reconnect the keypad, and run the diagnostic gate:

```bash
./scripts/install.sh
vaydeer-studio-cli doctor --json --sanitize
```

Use `systemctl --user restart vaydeer-studio.service` after changing only the
service unit. A physical reconnect is required after a udev rule change so the
new permissions apply to the device nodes.

## Package status

`make package` builds a sdist and wheel. It conditionally invokes AppImage,
Debian, and Flatpak bundle scripts when their external toolchains are installed.
The native package routes are not validated here. See the README for current
environment limitations; no native package is represented as released.
