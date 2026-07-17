# Packaging Status

Vaydeer Studio 1.0 supports an isolated, per-user installation on Linux through
`uv tool`. Run `scripts/install.sh` from a release source archive or checkout.
That path installs the application independently of the checkout and integrates
the desktop entry, MIME metadata, udev rule, and systemd user service.

`scripts/package.sh` produces and smoke-tests the Python wheel and source
archive, then generates `dist/SHA256SUMS`. Those are the release artifacts
validated by CI and consumed by the versioned bootstrap installer.

## Native bundle constraints

The files in `appimage/`, `deb/`, and `flatpak/` record future packaging work;
they are not supported v1 installers:

- An AppImage must bundle a compatible Python, Qt, hidapi, and GL stack, while
  still installing host-side udev and systemd integration separately.
- A Debian package needs release-specific PySide6 dependency decisions or a
  carefully maintained private runtime. A package built for one distribution
  must not be represented as portable across all Debian derivatives.
- A Flatpak cannot install the required host udev rule or ordinary systemd user
  service from inside its sandbox. Broad `--device=all` access is not an
  acceptable substitute for the scoped host permission rule.

The native helper scripts exit without producing an artifact. This is
intentional: incomplete packages are more harmful than an explicit limitation.
