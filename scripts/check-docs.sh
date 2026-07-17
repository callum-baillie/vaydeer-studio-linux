#!/usr/bin/env bash
set -euo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"

required=(
  README.md LICENSE ATTRIBUTION.md CHANGELOG.md CODE_OF_CONDUCT.md
  CONTRIBUTING.md SECURITY.md docs/README.md docs/installation.md
  docs/user-guide.md docs/troubleshooting.md docs/architecture.md
  docs/device-support.md docs/safety.md docs/protocol.md docs/bindings.md
  docs/research/overview.md docs/research/sources.md
  research/source-index.md research/sanitized-reports/index.md
  packaging/README.md
)
for file in "${required[@]}"; do
  [[ -s "$file" ]] || { echo "Required documentation is missing or empty: $file" >&2; exit 1; }
done

pattern='<your Vaydeer Studio remote>|example\.com|TODO|TBD'
if command -v rg >/dev/null 2>&1; then
  unresolved="$(rg -n "$pattern" README.md docs packaging/README.md || true)"
else
  unresolved="$(grep -REn "$pattern" README.md docs packaging/README.md || true)"
fi
if [[ -n "$unresolved" ]]; then
  echo "Public documentation contains a placeholder or unresolved marker." >&2
  echo "$unresolved" >&2
  exit 1
fi

for script in scripts/*.sh packaging/*/*.sh; do
  bash -n "$script"
done
if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate packaging/desktop/vaydeer-studio.desktop
fi
if command -v systemd-analyze >/dev/null 2>&1; then
  systemd-analyze --user verify packaging/systemd/vaydeer-studio.service
fi
if command -v udevadm >/dev/null 2>&1; then
  udevadm verify packaging/udev/99-vaydeer-studio.rules >/dev/null
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  prohibited='\.(exe|dmg|msi|asar|bin|dll|pdb|7z|pcap|pcapng|idb|i64|AppImage|deb|flatpak|rpm)$'
  if command -v rg >/dev/null 2>&1; then
    tracked="$(git ls-files | rg "$prohibited" || true)"
  else
    tracked="$(git ls-files | grep -E "$prohibited" || true)"
  fi
  if [[ -n "$tracked" ]]; then
    echo "Prohibited binary or package artifact is tracked:" >&2
    echo "$tracked" >&2
    exit 1
  fi
fi

echo "Documentation and repository hygiene checks passed."
