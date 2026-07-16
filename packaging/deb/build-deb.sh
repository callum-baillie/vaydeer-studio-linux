#!/usr/bin/env bash
set -euo pipefail

command -v dh_virtualenv >/dev/null || { echo "Install dh-virtualenv first." >&2; exit 2; }
command -v dpkg-buildpackage >/dev/null || { echo "Install dpkg-dev first." >&2; exit 2; }
echo "A Debian control file is intentionally not generated until a target distribution's Qt and hidapi dependency names are selected."
echo "Use the source installation meanwhile; see docs/installation.md."
