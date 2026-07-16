# Installation

Vaydeer Studio is developed and tested as a source installation using `uv`.
It needs Python 3.11+, a working Qt/GL desktop stack, and hidapi.

```bash
git clone <your Vaydeer Studio remote>
cd vaydeer-studio-linux
uv sync --extra dev
./scripts/install.sh
```

The script installs user-level launchers, desktop/MIME files, and a systemd user
service. It prompts for `sudo` only to install
`/etc/udev/rules.d/99-vaydeer-studio.rules`, scoped to the Vaydeer `0483:5752`
command and event interfaces. Reconnect the keypad after the rule reloads:

```bash
systemctl --user enable --now vaydeer-studio.service
vaydeer-studio
```

For a no-hardware demo, run `uv run vaydeer-studio --mock jp1011`.

## Permissions

The udev rule uses `TAG+="uaccess"` and mode `0660`, with `plugdev` as a
distribution fallback. It does not use `0666` or grant access to unrelated
HID devices. On systems without `plugdev`, remove that group clause or create
the distribution-appropriate limited group before installing the rule.

## Package status

`make package` builds a sdist and wheel. It conditionally invokes AppImage,
Debian, and Flatpak bundle scripts when their external toolchains are installed.
The native package routes are not validated here. See the README for current
environment limitations; no native package is represented as released.
