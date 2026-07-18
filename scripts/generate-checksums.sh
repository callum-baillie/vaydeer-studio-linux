#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
dist_dir="$root/dist"
[[ -d "$dist_dir" ]] || { echo "Release directory does not exist: $dist_dir" >&2; exit 1; }

cd "$dist_dir"
mapfile -d '' artifacts < <(
  find . -maxdepth 1 -type f ! -name '.*' ! -name SHA256SUMS -printf '%P\0' | sort -z
)
((${#artifacts[@]})) || { echo "No release artifacts found." >&2; exit 1; }

checksum_tmp="$(mktemp "$dist_dir/SHA256SUMS.XXXXXX")"
trap 'rm -f "$checksum_tmp"' EXIT
sha256sum -- "${artifacts[@]}" >"$checksum_tmp"
mv -f "$checksum_tmp" SHA256SUMS
chmod 0644 SHA256SUMS
trap - EXIT
