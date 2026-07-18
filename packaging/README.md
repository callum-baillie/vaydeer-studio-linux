# Packaging Status

Vaydeer Studio supports two release-grade Linux delivery paths:

- `install.sh` is the recommended cross-distribution installer. It detects the
  host, installs only known dependencies, configures the scoped udev rule and
  per-user systemd service, and installs Studio through `uv tool`.
- `Vaydeer_Studio-x86_64.AppImage` is a portable application bundle. It includes
  Python 3.11, PySide6, hidapi, and zsync update metadata, while relying on the
  documented standard desktop libraries. It cannot modify host udev
  configuration by itself.

`scripts/package.sh` builds and smoke-tests the wheel, source archive, and
release installer. `packaging/appimage/build-appimage.sh` creates a compliant
AppDir, downloads a checksum-pinned appimagetool and type-2 runtime, builds the
AppImage, and runs CLI plus offscreen mock UI smoke tests.
`scripts/generate-checksums.sh` covers every artifact in `dist/SHA256SUMS`.

The tag-driven release workflow rebuilds these files on Ubuntu 22.04 and uploads
them to the matching GitHub release. The version in the tag, `pyproject.toml`,
Python package, bootstrap installer, and AppStream metadata must agree.

The AppImage CLI and offscreen mock UI are smoke-tested in clean Debian 12,
Fedora 43, and Arch Linux userspaces with the runtime libraries documented in
`docs/installation.md`. Physical HID, udev, desktop-menu, and systemd integration
remain the responsibility of the host-integrated installer.

## Native bundle constraints

Native Debian, RPM, Arch, and Flatpak packages are not currently released:

- A Debian package needs release-specific PySide6 dependency decisions or a
  maintained private runtime, plus policy-compliant maintainer scripts and
  upgrade tests on every claimed Debian/Ubuntu release.
- RPM and Arch packages need equivalent native dependency and lifecycle testing
  rather than conversion from an Ubuntu-built package.
- A Flatpak cannot install the required host udev rule or ordinary systemd user
  service from inside its sandbox. Broad `--device=all` access is not an
  acceptable substitute for the scoped host permission rule.

The Debian and Flatpak helper scripts still fail explicitly instead of producing
misleading artifacts. The one-line installer is the full host-integrated path;
the AppImage is the portable path.
