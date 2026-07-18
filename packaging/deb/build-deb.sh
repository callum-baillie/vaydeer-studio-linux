#!/usr/bin/env bash
set -euo pipefail

echo "A native Debian package is not currently a supported release artifact." >&2
echo "See packaging/README.md for the dependency and runtime constraints. No artifact was produced." >&2
exit 2
