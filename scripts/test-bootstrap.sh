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

echo "Bootstrap distribution plan tests passed."
