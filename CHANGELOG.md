# Changelog

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
