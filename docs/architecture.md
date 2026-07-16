# Architecture

Vaydeer Studio is a Python 3.11+ application with a Qt Quick/PySide6 shell.
The UI, CLI, and service share one protocol and safety core so a visual control
cannot bypass a device safeguard.

| Layer | Responsibility |
| --- | --- |
| `protocol/` | Fixed report framing, XOR validation, known commands, typed key codecs, and a hard firmware-command block. |
| `devices/` | Sysfs/hidapi discovery, HID transport, capability table, declarative layouts, and mock JP-1011. |
| `core/` | Profile schema, portable JSON/YAML, backup store, diff, and transactional apply preparation. |
| `service/` | Interface-2 read-only keepalive, binding executor, hotplug tick loop, and Unix-socket IPC. |
| `ui/` | QML views and a Qt controller; real hardware is inspection-only from the desktop shell. |
| `cli/` | Inspection, backup, dry run, profile validation, restore staging, and explicitly confirmed writes. |

`prepare_apply()` reads the live snapshot, matches a known capability, saves a
backup, produces packets and a diff, and returns an immutable preview.
`apply_prepared()` refuses an unconfirmed preview, sends only known stable
mapping/layer commands, reads back, and compares the intended result. A partial
write remains reported with the preserved pre-write backup.

The user service has no raw packet API and never sends command `0xFC`. Its
socket protocol is a small JSON request/response channel for state, bindings,
mock events, and clean shutdown.
