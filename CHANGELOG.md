# Changelog

## 1.1.0 - 2026-07-17

- Make the primary installation and update path a stable one-line command using
  the latest release's `install.sh` asset.
- Add a minimal vector keypad logo with a red top-right key and use it for the
  application window, desktop entry, source install, and portable package.
- Add a portable, update-aware x86_64 AppImage build with Python 3.11,
  PySide6, release checksums, CLI validation, and offscreen mock UI testing.
- Add a tag-driven release workflow that validates version metadata, builds all
  supported artifacts, and publishes them to GitHub Releases.
- Restart the Background service after source-installer upgrades so the running
  daemon always matches the newly installed Studio version.

## 1.0.2 - 2026-07-16

- Fix `--no-deps` exiting immediately after the installation plan under strict
  shell error handling.
- Add an execution-level regression test that verifies the dependency-skip path
  reaches the verified download stage without changing the host.

## 1.0.1 - 2026-07-16

- Add a hardened, distro-aware bootstrap installer for Ubuntu/Debian, Fedora,
  Arch Linux, and compatible derivatives.
- Pin and checksum the fallback uv installer, verify release source archives,
  show package-manager changes before execution, and retain per-user privilege
  boundaries.
- Document reviewed-download and interactive `curl | bash` workflows, installer
  options, manual installation, and update behavior.
- Generate a `SHA256SUMS` manifest with every release build and test bootstrap
  distribution plans in CI.

## 1.0.0 - 2026-07-16

- Promote the validated JP-1011 scope to the first public release and add
  consistent `--version` output for the desktop app, CLI, and Background
  service.
- Replace checkout-bound launchers with an isolated `uv tool` installation,
  install the previously omitted CLI, and generate desktop and systemd entries
  using the actual installed executable paths.
- Make the udev rule portable across supported distributions by using a scoped
  `uaccess` ACL without a distribution-specific group.
- Add release artifact smoke tests, repository hygiene checks, dependency
  bounds, public project metadata, and GitHub contribution templates.
- Rewrite installation and project documentation around the supported v1
  path, with an explicit unofficial-project notice and honest native-package
  limitations.

## 0.1.17 - 2026-07-16

- Restore versioned, decorated window-frame geometry after the native window
  manager has created the frame. Legacy client-only geometry is ignored, new
  windows use the window manager's placement, and restored frames are clamped
  to the current usable displays.
- Prevent smoke and screenshot validation from changing the user's saved
  window state.
- Give every long page a consistent visible scrollbar and keyboard Page Up,
  Page Down, Home, and End navigation at constrained window heights.
- Fix Live Tester header and empty-state clipping and keep the on-device layout
  heading readable at the supported minimum window size.

## 0.1.16 - 2026-07-16

- Persist normal window size, location, and maximized state, while clamping a
  restored window to an available display after monitor, panel, or DPI changes.
- Replace the Profiles page's implicit clipped overflow with a visible,
  keyboard and pointer-scrollable viewport at constrained laptop heights.

## 0.1.15 - 2026-07-16

- Normalize text-field and text-area foreground, placeholder, disabled,
  selection, and focus styling across dark and light themes.
- Add a QML smoke assertion that verifies readable dark and light input colors,
  and refresh affected UI screenshots.

## 0.1.14 - 2026-07-16

- Polish the desktop shell with a fixed application bar, restrained design
  tokens, compact device/service status, clearer navigation, persistent theme,
  and persistent Basic/Advanced mode.
- Add Overview and Setup workflows that distinguish Studio, keypad memory, and
  the lightweight Background service without low-level terminology in Basic
  mode.
- Rename and simplify the core screens: On-device keys uses a reviewed
  read-edit-review-write flow; Linux actions clearly remain local and
  service-dependent; Profiles group on-device and Linux-only content.
- Improve Live tester and Diagnostics with actionable empty states, concise
  event data, pause/clear/copy/export controls, and plain-language health
  summaries. Raw HID details now appear only in Advanced mode.
- Add headless QML shell coverage for navigation, Basic/Advanced mode, and the
  fixed header, plus tester session export/clear coverage and refreshed UI
  documentation and screenshots.

## 0.1.13 - 2026-07-16

- Add in-app scope explainers to On-device mappings, Profiles, and Live key
  tester. Each screen now distinguishes persistent keypad configuration from
  host-only `vaydeer-studiod` behavior.
- Add a Help page at the bottom of the sidebar with a concise first-run flow,
  an explanation of the lightweight background service, and instructions for
  every workspace.

## 0.1.12 - 2026-07-16

- Allow a compatible, connected keypad to be written directly from the desktop
  application after a reviewed diff and typed in-app `APPLY` confirmation.
  Backups, capability guards, known-command restrictions, exclusive sessions,
  and read-back verification remain mandatory.
- Invalidate an attempted write preview after a disconnect or write failure, so
  users must re-read and review the device instead of retrying a stale plan.

## 0.1.11 - 2026-07-16

- Remove deprecated implicit signal arguments from keypad handlers and declare
  delegate indexes explicitly, eliminating the QML `keyIndex`/`index` runtime
  warnings.
- Bind each physical-key delegate to its owning repeater before handling a
  click, so all keypad rows select and animate their intended physical key
  without unresolved `keypad` references.
- Add deterministic offscreen checks for clicking a lower-row keypad key and
  keep named keypad surfaces available to UI validation tooling.

## 0.1.10 - 2026-07-16

- Give the reviewed-device-change dialog explicit themed header and diff-list
  surfaces. It now remains legible in both dark and light modes instead of
  inheriting the desktop platform's light dialog palette.

## 0.1.9 - 2026-07-16

- Preserve numeric keypad input during physical keyboard capture: Qt keypad
  digits now serialize as `Num 0` through `Num 9`, matching the JP-1011's
  existing virtual-key mappings instead of changing them to top-row digits.
- Make key capture an explicit, visible state with a captured-value explanation
  and a physical-key selection listener while the mapping editor is open.
- Improve portable macro recording with held-modifier de-duplication and
  recorded delays. Macros remain profile-only experimental data and are never
  transmitted to a keypad.
- Add platform-targeted application presets for Codex, ChatGPT, Photoshop, and
  Illustrator. Profiles can target Linux, macOS, or Windows; only Linux
  profiles load Linux-side bindings into the local service.

## 0.1.8 - 2026-07-16

- Rework on-device mappings around a last-read device baseline, a protected
  mapping draft, per-key current/pending indicators, readable key pickers, and
  physical keyboard capture. Refreshing the keypad no longer overwrites
  pending mapping changes.
- Make Linux bindings editable, surface local service readiness in the binding
  workflow, and offer only `press` and `release` triggers because those are the
  triggers currently dispatched by the service.
- Expand profile workflow with local-save state, device-baseline refresh,
  explicit use-device-state behavior, JSON/YAML export selection, and saved
  profile metadata. Add interaction-design research and update the mock image.

## 0.1.7 - 2026-07-16

- Continue read-only command-interface discovery after startup until the
  already-connected keypad has been inspected successfully; a USB replug is no
  longer required after a transient HID or protocol initialization delay.
- Stop the retry poll immediately after a successful read and suppress repeated
  identical connection warnings while recovery is in progress.

## 0.1.6 - 2026-07-16

- Keep each JP-1011 key delegate in its assigned grid cell while animating the
  inner keycap, fixing lower-row tester keys jumping into the top row.
- Preserve a short visual pressed state when a physical press/release pair is
  drained in one service poll, so every logged press is observable in the
  tester.

## 0.1.5 - 2026-07-16

- Rework the desktop workspace around a selectable JP-1011 physical keypad,
  readable key values, profile layers, and distinct onboard and Linux-side
  action flows.
- Add physical-keyboard capture for key values, portable macro recording and
  manual macro steps, binding trigger/window controls, and live tester
  press/lift animation.
- Show host-local `vaydeer-studiod` installation, running, reachability, and
  login-start status. The app can install and enable its user unit from the
  Devices screen without invoking `sudo`; scoped udev permission setup remains
  explicit.

## 0.1.4 - 2026-07-16

- Connect the live key tester to the JP-1011 vendor-event service instead of
  only generating mock events.
- Enable event reads only while the tester has a renewable UI lease, retain a
  bounded in-memory event queue, and expose unrecognized raw reports safely.

## 0.1.3 - 2026-07-16

- Serialize complete JP-1011 command sessions, not only individual HID
  exchanges, and discard stale response frames before a newly locked session.
- Prevent concurrent CLI and desktop inspections from cross-consuming queued
  interface-0 responses during multi-frame snapshot reads or verified applies.
- Add regression coverage for stale-frame draining and compound-session locks.

## 0.1.2 - 2026-07-16

- Automatically surface USB disappearance in the desktop UI and retry the
  command channel after reconnect.
- Track the sysfs HID instance as well as the hidraw node, recovering safely
  when Linux reuses a node name after a physical replug.
- Expand the first-run hardware setup report and document the sanitized live
  interface inventory and remaining manual reconnect validation.
- Validate a real unplug/replug recovery: USB detection, controller discovery,
  and the interface-2 read-only keepalive all recovered without a write.

## 0.1.1 - 2026-07-16

- Repair live JP-1011 discovery with a sysfs-selected native hidraw command
  transport when hidapi exposes incomplete metadata or cannot open the node.
- Add a bounded cross-process HID transaction lock, safe `doctor` diagnostics,
  explicit disconnected/recovery UI state, and verified udev/service setup.
- Correct the udev parent/interface match, improve uninstall behavior, and add
  live-device detection research plus regression coverage for recovery paths.

## 0.1.0 - 2026-07-15

- Initial Linux-first Vaydeer Studio release candidate.
