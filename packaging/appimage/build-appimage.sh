#!/usr/bin/env bash
set -Eeuo pipefail

root="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$root"

readonly APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
readonly APPIMAGETOOL_SHA256="a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"
readonly APPIMAGE_RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
readonly APPIMAGE_RUNTIME_SHA256="1cc49bcf1e2ccd593c379adb17c9f85a36d619088296504de95b1d06215aebbf"

command -v uv >/dev/null 2>&1 || { echo "uv is required." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required." >&2; exit 1; }
[[ "$(uname -m)" == "x86_64" ]] || { echo "The validated AppImage target is x86_64 only." >&2; exit 1; }

version="$(sed -n 's/^version = "\([^"]*\)"/\1/p' pyproject.toml)"
[[ -n "$version" ]] || { echo "Could not read the project version." >&2; exit 1; }

build_dir="$root/build/appimage"
appdir="$build_dir/VaydeerStudio.AppDir"
tool="$build_dir/appimagetool-x86_64.AppImage"
runtime="$build_dir/runtime-x86_64"
output="$root/dist/Vaydeer_Studio-x86_64.AppImage"
python_bin="$(UV_PYTHON_PREFERENCE=only-managed uv python find 3.11 2>/dev/null || true)"
if [[ -z "$python_bin" ]]; then
  UV_PYTHON_PREFERENCE=only-managed uv python install 3.11
  python_bin="$(UV_PYTHON_PREFERENCE=only-managed uv python find 3.11)"
fi
python_root="$(CDPATH= cd -- "$(dirname -- "$python_bin")/.." && pwd)"

rm -rf "$appdir"
install -d \
  "$appdir/usr" \
  "$appdir/usr/lib/python3.11/site-packages" \
  "$appdir/usr/share/applications" \
  "$appdir/usr/share/icons/hicolor/scalable/apps" \
  "$appdir/usr/share/metainfo" \
  "$appdir/usr/share/doc/vaydeer-studio" \
  "$appdir/usr/share/vaydeer-studio"
cp -a "$python_root/." "$appdir/usr/"
uv pip install \
  --python "$python_bin" \
  --target "$appdir/usr/lib/python3.11/site-packages" \
  --compile-bytecode \
  "$root"

install -m 0755 packaging/appimage/AppRun "$appdir/AppRun"
desktop_id="io.github.callumbaillie.vaydeer-studio"
install -m 0644 "packaging/desktop/$desktop_id.desktop" \
  "$appdir/usr/share/applications/$desktop_id.desktop"
printf 'X-AppImage-Version=%s\n' "$version" >>"$appdir/usr/share/applications/$desktop_id.desktop"
install -m 0644 src/vaydeer_studio/resources/icons/vaydeer-studio.svg \
  "$appdir/usr/share/icons/hicolor/scalable/apps/vaydeer-studio.svg"
install -m 0644 "packaging/appimage/$desktop_id.metainfo.xml" \
  "$appdir/usr/share/metainfo/$desktop_id.appdata.xml"
install -m 0644 packaging/udev/99-vaydeer-studio.rules \
  "$appdir/usr/share/vaydeer-studio/99-vaydeer-studio.rules"
install -m 0644 LICENSE ATTRIBUTION.md "$appdir/usr/share/doc/vaydeer-studio/"
ln -s "usr/share/applications/$desktop_id.desktop" "$appdir/$desktop_id.desktop"
ln -s usr/share/icons/hicolor/scalable/apps/vaydeer-studio.svg "$appdir/vaydeer-studio.svg"
ln -s vaydeer-studio.svg "$appdir/.DirIcon"

install -d "$build_dir" "$root/dist"
if [[ ! -x "$tool" ]] || \
  [[ "$(sha256sum "$tool" 2>/dev/null | awk '{print $1}')" != "$APPIMAGETOOL_SHA256" ]]; then
  rm -f "$tool"
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    --proto-redir '=https' --retry 3 --output "$tool" "$APPIMAGETOOL_URL"
  [[ "$(sha256sum "$tool" | awk '{print $1}')" == "$APPIMAGETOOL_SHA256" ]] || {
    rm -f "$tool"
    echo "appimagetool checksum mismatch." >&2
    exit 1
  }
  chmod +x "$tool"
fi

if [[ ! -f "$runtime" ]] || \
  [[ "$(sha256sum "$runtime" 2>/dev/null | awk '{print $1}')" != "$APPIMAGE_RUNTIME_SHA256" ]]; then
  rm -f "$runtime"
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
    --proto-redir '=https' --retry 3 --output "$runtime" "$APPIMAGE_RUNTIME_URL"
  [[ "$(sha256sum "$runtime" | awk '{print $1}')" == "$APPIMAGE_RUNTIME_SHA256" ]] || {
    rm -f "$runtime"
    echo "AppImage runtime checksum mismatch." >&2
    exit 1
  }
fi

rm -f "$output" "$output.zsync"
rm -f "$root/$(basename "$output").zsync"
update_information="gh-releases-zsync|callum-baillie|vaydeer-studio-linux|latest|Vaydeer_Studio-x86_64.AppImage.zsync"
ARCH=x86_64 "$tool" --appimage-extract-and-run \
  --runtime-file "$runtime" -u "$update_information" "$appdir" "$output"
generated_zsync="$root/$(basename "$output").zsync"
[[ -f "$generated_zsync" ]] || { echo "AppImage update metadata was not generated." >&2; exit 1; }
mv -f "$generated_zsync" "$output.zsync"

"$output" --appimage-extract-and-run --cli --version
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  "$output" --appimage-extract-and-run --mock jp1011 --smoke
"$root/scripts/generate-checksums.sh"

echo "Validated AppImage: $output"
echo "Update metadata: $output.zsync"
