# Troubleshooting

## Normal keyboard events stop

The JP-1011 requires its vendor event interface to remain open. Check:

```bash
systemctl --user status vaydeer-studio.service
vaydeer-studio-cli doctor
vaydeer-studio-cli diagnostics --verbose
```

Reconnect the keypad after installing the udev rule. Do not open a guessed
`/dev/hidrawN` node manually: the service selects VID:PID, interface `2`, usage
page `0xFF00`, and usage `0x0002` dynamically.

`doctor` identifies the first failed stage as `root_cause`, including no
device, a missing command/event interface, permission denial, a stopped
service, protocol initialization failure, or an unknown firmware that is
intentionally read-only. It is safe to run while the GUI is open: command
transactions are serialized on the selected HID node.

## Permission denied

Confirm the rule is installed, reload it, reconnect the keypad, and inspect the
diagnostics. Ensure the active desktop session receives `uaccess`; on a system
using the fallback group, ensure the user belongs to the configured group and
starts a new session.

To repair the installed integration, run:

```bash
./scripts/install.sh
vaydeer-studio-cli doctor --json --sanitize
```

The installer reloads udev rules but deliberately does not pretend this changes
permissions on an already-enumerated keypad. Reconnect it before testing again.

## Device is read-only

This is expected for unknown firmware versions and unsupported models. Export
the profile and diagnostics, then open an issue with sanitized report data. Do
not use a firmware updater to make the app writable.

## Service does not start

Run `systemctl --user daemon-reload`, then inspect
`journalctl --user -u vaydeer-studio.service`. The service should be installed
as the same user who launches the desktop session.

For a stale installed unit after updating a source checkout:

```bash
./scripts/install.sh
systemctl --user restart vaydeer-studio.service
```

## Device appears in USB tools but not in the app

The Linux command path is intentionally based on sysfs HID metadata and the
report descriptor, not on hidapi enumeration alone. Some hidapi builds expose
opaque interface paths and zero usage fields for this keypad. Run the verbose
diagnostic and see [live-device-detection-debug.md](research/live-device-detection-debug.md).
Do not manually substitute a fixed `/dev/hidrawN` path.
