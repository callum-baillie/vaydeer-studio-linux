#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

write_os_release() {
  local name="$1"
  local id="$2"
  local id_like="${3:-}"
  printf 'ID=%s\nID_LIKE="%s"\nPRETTY_NAME="Fixture %s"\n' \
    "$id" "$id_like" "$name" >"$test_root/$name"
}

assert_plan_contains() {
  local fixture="$1"
  shift
  local output
  output="$(VAYDEER_OS_RELEASE="$test_root/$fixture" "$root/scripts/bootstrap.sh" --print-plan)"
  local expected
  for expected in "$@"; do
    grep -F -- "$expected" <<<"$output" >/dev/null || {
      printf 'Expected %q in plan:\n%s\n' "$expected" "$output" >&2
      exit 1
    }
  done
}

write_os_release ubuntu ubuntu debian
write_os_release mint linuxmint "ubuntu debian"
write_os_release fedora fedora
write_os_release arch arch
write_os_release unknown gentoo

assert_plan_contains ubuntu \
  "Package manager: apt" \
  "sudo apt-get update" \
  "libhidapi-hidraw0" \
  "libxcb-cursor0"
assert_plan_contains mint \
  "Package manager: apt" \
  "libxkbcommon-x11-0"
assert_plan_contains fedora \
  "Package manager: dnf" \
  "hidapi" \
  "libglvnd-egl" \
  "xcb-util-cursor"
assert_plan_contains arch \
  "Package manager: pacman" \
  "--needed" \
  "mesa" \
  "libglvnd"
assert_plan_contains unknown \
  "Package manager: unsupported" \
  "automatic installation is not supported"

unknown_no_deps="$(
  VAYDEER_OS_RELEASE="$test_root/unknown" \
    "$root/scripts/bootstrap.sh" --print-plan --no-deps --no-udev --no-service
)"
grep -F "System packages: skipped (--no-deps)" <<<"$unknown_no_deps" >/dev/null
grep -F "Device permission rule: skip" <<<"$unknown_no_deps" >/dev/null
grep -F "Background service: skip" <<<"$unknown_no_deps" >/dev/null

# Exercise the no-dependency path without network access. Reaching the fake
# downloader proves the skipped package step returned success under `set -e`.
mkdir -p "$test_root/fake-bin" "$test_root/home"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'printf reached >"$VAYDEER_TEST_DOWNLOAD_MARKER"' \
  'exit 42' >"$test_root/fake-bin/curl"
chmod +x "$test_root/fake-bin/curl"
set +e
PATH="$test_root/fake-bin:/usr/bin:/bin" \
HOME="$test_root/home" \
VAYDEER_OS_RELEASE="$test_root/ubuntu" \
VAYDEER_TEST_DOWNLOAD_MARKER="$test_root/download-marker" \
  "$root/scripts/bootstrap.sh" --yes --no-deps --no-udev --no-service \
  >"$test_root/no-deps-output" 2>&1
no_deps_status=$?
set -e
[[ "$no_deps_status" -eq 1 ]] || {
  cat "$test_root/no-deps-output" >&2
  printf 'Expected controlled download failure status 1, got %s.\n' "$no_deps_status" >&2
  exit 1
}
grep -F "Downloading pinned uv" "$test_root/no-deps-output" >/dev/null
grep -F "Error: Download failed:" "$test_root/no-deps-output" >/dev/null
grep -F "reached" "$test_root/download-marker" >/dev/null

echo "Bootstrap distribution plan tests passed."
