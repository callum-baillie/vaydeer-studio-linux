# Changelog

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
