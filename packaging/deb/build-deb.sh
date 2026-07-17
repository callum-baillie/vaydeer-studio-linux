#!/usr/bin/env bash
set -euo pipefail

echo "A native Debian package is not a supported v1 artifact." >&2
echo "See packaging/README.md for the dependency and runtime constraints. No artifact was produced." >&2
exit 2
