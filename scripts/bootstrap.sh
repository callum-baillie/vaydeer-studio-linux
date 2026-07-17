#!/usr/bin/env bash
set -Eeuo pipefail

umask 022

readonly STUDIO_VERSION="1.0.2"
readonly UV_VERSION="0.11.29"
readonly UV_INSTALLER_SHA256="504a79fd2ed0dcd47e7f04f0792cfd0871f62e24a7fe40fa8ae0f563a369f2bd"
readonly REPOSITORY="callum-baillie/vaydeer-studio-linux"

assume_yes=false
install_dependencies=true
install_udev=true
install_service=true
print_plan=false
os_release_file="${VAYDEER_OS_RELEASE:-/etc/os-release}"
temp_dir=""

distro_id=""
distro_like=""
distro_name=""
package_manager=""
declare -a dependency_packages=()
declare -a update_command=()
declare -a install_command=()

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [options]

Download and install a pinned Vaydeer Studio release on a supported Linux
distribution. Run this script as the desktop user who will use the keypad.

Options:
  --yes        Accept the displayed installation plan without prompting.
  --no-deps    Do not install distribution packages.
  --no-udev    Do not install the root-owned device permission rule.
  --no-service Do not install or start the per-user Background service.
  --print-plan Detect the distribution and print the package plan only.
  -h, --help   Show this help.

Supported automatic dependency installation:
  Ubuntu, Debian, Linux Mint, Fedora, Arch Linux, and compatible derivatives.
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
    rm -rf -- "$temp_dir"
  fi
}

trap cleanup EXIT
trap 'die "Installation interrupted."' INT TERM

print_command() {
  printf '  '
  printf '%q ' "$@"
  printf '\n'
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

parse_options() {
  while (($#)); do
    case "$1" in
      --yes) assume_yes=true ;;
      --no-deps) install_dependencies=false ;;
      --no-udev) install_udev=false ;;
      --no-service) install_service=false ;;
      --print-plan) print_plan=true ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1 (use --help for usage)" ;;
    esac
    shift
  done
}

load_os_release() {
  [[ -r "$os_release_file" ]] || die "Cannot read Linux distribution metadata: $os_release_file"

  # /etc/os-release is a root-owned shell-compatible data file defined by os-release(5).
  unset ID ID_LIKE PRETTY_NAME || true
  # shellcheck disable=SC1090
  source "$os_release_file"
  distro_id="${ID:-unknown}"
  distro_like="${ID_LIKE:-}"
  distro_name="${PRETTY_NAME:-$distro_id}"
  distro_id="${distro_id,,}"
  distro_like="${distro_like,,}"
}

distribution_matches() {
  local candidate
  for candidate in "$@"; do
    if [[ "$distro_id" == "$candidate" || " $distro_like " == *" $candidate "* ]]; then
      return 0
    fi
  done
  return 1
}

detect_distribution() {
  load_os_release

  if distribution_matches debian ubuntu; then
    package_manager="apt"
    dependency_packages=(
      ca-certificates curl libhidapi-hidraw0 libegl1 libgl1
      libxcb-cursor0 libxkbcommon-x11-0
    )
    update_command=(sudo apt-get update)
    install_command=(sudo apt-get install -y "${dependency_packages[@]}")
  elif distribution_matches fedora; then
    package_manager="dnf"
    dependency_packages=(
      ca-certificates curl hidapi libglvnd-egl libglvnd-glx
      xcb-util-cursor libxkbcommon-x11
    )
    update_command=()
    install_command=(sudo dnf install -y "${dependency_packages[@]}")
  elif distribution_matches arch; then
    package_manager="pacman"
    dependency_packages=(
      ca-certificates curl hidapi mesa libglvnd xcb-util-cursor libxkbcommon-x11
    )
    update_command=()
    install_command=(sudo pacman -S --needed --noconfirm "${dependency_packages[@]}")
  else
    package_manager="unsupported"
    dependency_packages=()
    update_command=()
    install_command=()
  fi
}

print_installation_plan() {
  printf 'Vaydeer Studio %s installation plan\n' "$STUDIO_VERSION"
  printf 'Distribution: %s\n' "$distro_name"
  printf 'Package manager: %s\n' "$package_manager"

  if [[ "$install_dependencies" == true ]]; then
    if [[ "$package_manager" == "unsupported" ]]; then
      printf 'Dependencies: automatic installation is not supported for this distribution.\n'
    else
      printf 'System package commands:\n'
      if ((${#update_command[@]})); then
        print_command "${update_command[@]}"
      fi
      print_command "${install_command[@]}"
    fi
  else
    printf 'System packages: skipped (--no-deps)\n'
  fi

  printf 'uv: use an existing installation, or install pinned version %s after checksum verification.\n' "$UV_VERSION"
  printf 'Application: download and verify the Vaydeer Studio %s source release.\n' "$STUDIO_VERSION"
  printf 'Device permission rule: %s\n' "$([[ "$install_udev" == true ]] && printf 'install' || printf 'skip')"
  printf 'Background service: %s\n' "$([[ "$install_service" == true ]] && printf 'install and start' || printf 'skip')"
}

confirm_plan() {
  if [[ "$assume_yes" == true ]]; then
    return
  fi
  if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
    die "Interactive confirmation needs a terminal; review the script, then rerun with --yes."
  fi

  local reply
  printf '\nContinue with this plan? [y/N] ' >/dev/tty
  IFS= read -r reply </dev/tty || die "Could not read confirmation."
  [[ "$reply" == "y" || "$reply" == "Y" ]] || die "Installation cancelled."
}

preflight_host_integration() {
  if [[ "$install_service" == true ]]; then
    require_command systemctl
    systemctl --user show-environment >/dev/null 2>&1 || {
      die "No usable systemd user manager was found; use --no-service to install Studio only."
    }
  fi
  if [[ "$install_udev" == true ]]; then
    require_command sudo
    require_command udevadm
  fi
}

install_system_dependencies() {
  [[ "$install_dependencies" == true ]] || return 0
  [[ "$package_manager" != "unsupported" ]] || {
    die "Automatic dependency installation is unavailable for $distro_name. Install the documented requirements and rerun with --no-deps."
  }

  require_command sudo
  if [[ "$package_manager" == "apt" ]]; then
    require_command apt-get
  else
    require_command "$package_manager"
  fi
  sudo -v
  if ((${#update_command[@]})); then
    "${update_command[@]}"
  fi
  "${install_command[@]}"
}

secure_download() {
  local url="$1"
  local destination="$2"
  if ! curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    --proto-redir '=https' --retry 3 --retry-delay 1 --output "$destination" "$url"; then
    die "Download failed: $url"
  fi
}

find_uv() {
  local candidate
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return
  fi
  for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  return 1
}

install_uv() {
  local uv_command
  if uv_command="$(find_uv)"; then
    printf 'Using existing uv: %s (%s)\n' "$uv_command" "$("$uv_command" --version)" >&2
    printf '%s\n' "$uv_command"
    return
  fi

  local installer="$temp_dir/uv-installer.sh"
  local actual_sha256
  printf 'Downloading pinned uv %s installer...\n' "$UV_VERSION" >&2
  secure_download \
    "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-installer.sh" \
    "$installer"
  actual_sha256="$(sha256sum "$installer" | awk '{print $1}')"
  [[ "$actual_sha256" == "$UV_INSTALLER_SHA256" ]] || {
    die "uv installer checksum mismatch; no installer was executed."
  }
  if ! env UV_NO_MODIFY_PATH=1 sh "$installer" >&2; then
    die "The verified uv installer failed."
  fi
  uv_command="$(find_uv)" || die "uv installed but its executable could not be found."
  printf 'Installed verified uv: %s (%s)\n' "$uv_command" "$("$uv_command" --version)" >&2
  printf '%s\n' "$uv_command"
}

verify_release_archive() {
  local archive="$1"
  local checksums="$2"
  local archive_name="$3"
  local expected
  local actual
  local matches

  matches="$(awk -v name="$archive_name" '$2 == name || $2 == "*" name {print $1}' "$checksums")"
  [[ "$(printf '%s\n' "$matches" | sed '/^$/d' | wc -l)" -eq 1 ]] || {
    die "The release checksum manifest has no unique entry for $archive_name."
  }
  expected="$(printf '%s' "$matches" | tr '[:upper:]' '[:lower:]')"
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || die "The release checksum entry is malformed."
  actual="$(sha256sum "$archive" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || die "Vaydeer Studio release checksum mismatch."
}

extract_release_archive() {
  local archive="$1"
  local destination="$2"
  local expected_prefix="vaydeer_studio-${STUDIO_VERSION}/"
  local entry

  while IFS= read -r entry; do
    [[ "$entry" == "$expected_prefix"* ]] || die "Release archive contains an unexpected path: $entry"
    [[ "$entry" != *'/../'* && "$entry" != *'/./'* ]] || die "Release archive contains an unsafe path."
  done < <(tar -tzf "$archive")

  mkdir -p "$destination"
  tar --extract --gzip --file "$archive" --directory "$destination" \
    --strip-components=1 --no-same-owner --no-same-permissions
  [[ -x "$destination/scripts/install.sh" ]] || die "Release archive is missing scripts/install.sh."
}

download_and_install_studio() {
  local uv_command="$1"
  local release_base="https://github.com/${REPOSITORY}/releases/download/v${STUDIO_VERSION}"
  local archive_name="vaydeer_studio-${STUDIO_VERSION}.tar.gz"
  local archive="$temp_dir/$archive_name"
  local checksums="$temp_dir/SHA256SUMS"
  local source_dir="$temp_dir/source"
  local -a installer_options=()

  printf 'Downloading Vaydeer Studio %s...\n' "$STUDIO_VERSION"
  secure_download "$release_base/$archive_name" "$archive"
  secure_download "$release_base/SHA256SUMS" "$checksums"
  verify_release_archive "$archive" "$checksums" "$archive_name"
  printf 'Verified release archive checksum.\n'
  extract_release_archive "$archive" "$source_dir"

  [[ "$install_udev" == true ]] || installer_options+=(--no-udev)
  [[ "$install_service" == true ]] || installer_options+=(--no-service)
  PATH="$(dirname "$uv_command"):$PATH" "$source_dir/scripts/install.sh" "${installer_options[@]}"
}

main() {
  parse_options "$@"

  [[ "$(uname -s)" == "Linux" ]] || die "Vaydeer Studio's host integration is supported on Linux only."
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    die "Run this installer as your desktop user, not as root or through sudo."
  fi

  detect_distribution
  print_installation_plan
  if [[ "$print_plan" == true ]]; then
    return
  fi
  if [[ "$install_dependencies" == true && "$package_manager" == "unsupported" ]]; then
    die "Automatic dependency installation is unavailable for $distro_name. Install the documented requirements and rerun with --no-deps."
  fi

  require_command curl
  require_command sha256sum
  require_command awk
  require_command sed
  require_command tr
  require_command wc
  require_command tar
  require_command mktemp
  preflight_host_integration
  confirm_plan

  temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/vaydeer-studio-install.XXXXXXXX")"
  install_system_dependencies
  local uv_command
  uv_command="$(install_uv)"
  download_and_install_studio "$uv_command"
}

main "$@"
