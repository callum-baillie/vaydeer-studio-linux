# Troubleshooting

## Normal keyboard events stop

The JP-1011 requires its vendor event interface to remain open. Check:

```bash
systemctl --user status vaydeer-studio.service
vaydeer-studio-cli keepalive
vaydeer-studio-cli diagnostics
```

Reconnect the keypad after installing the udev rule. Do not open a guessed
`/dev/hidrawN` node manually: the service selects VID:PID, interface `2`, usage
page `0xFF00`, and usage `0x0002` dynamically.

## Permission denied

Confirm the rule is installed, reload it, reconnect the keypad, and inspect the
diagnostics. Ensure the active desktop session receives `uaccess`; on a system
using the fallback group, ensure the user belongs to the configured group and
starts a new session.

## Device is read-only

This is expected for unknown firmware versions and unsupported models. Export
the profile and diagnostics, then open an issue with sanitized report data. Do
not use a firmware updater to make the app writable.

## Service does not start

Run `systemctl --user daemon-reload`, then inspect
`journalctl --user -u vaydeer-studio.service`. The service should be installed
as the same user who launches the desktop session.
