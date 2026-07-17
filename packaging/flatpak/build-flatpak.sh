#!/usr/bin/env bash
set -euo pipefail

echo "Flatpak is not a supported v1 package because host udev and systemd integration is unresolved." >&2
echo "See packaging/README.md. No artifact was produced." >&2
exit 2
