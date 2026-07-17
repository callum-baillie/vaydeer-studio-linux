#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$root"
echo "AppImage is not a supported v1 package because its portable Qt/HID runtime is unresolved." >&2
echo "See packaging/README.md. No artifact was produced." >&2
exit 2
