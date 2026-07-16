# Changelog

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
