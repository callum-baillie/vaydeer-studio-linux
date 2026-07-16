# Changelog

## 0.1.1 - 2026-07-16

- Repair live JP-1011 discovery with a sysfs-selected native hidraw command
  transport when hidapi exposes incomplete metadata or cannot open the node.
- Add a bounded cross-process HID transaction lock, safe `doctor` diagnostics,
  explicit disconnected/recovery UI state, and verified udev/service setup.
- Correct the udev parent/interface match, improve uninstall behavior, and add
  live-device detection research plus regression coverage for recovery paths.

## 0.1.0 - 2026-07-15

- Initial Linux-first Vaydeer Studio release candidate.
