# Linux Activation

The JP-1011 does not reliably continue sending normal Linux keyboard events
unless vendor USB interface 2 is opened. This has been repeatedly observed with
the matched event HID collection: usage page `0xFF00`, usage `0x0002`, 16-byte
input report.

- Opening interface 2 `O_RDONLY | O_CLOEXEC` and retaining the descriptor is
  sufficient.
- No read call is required.
- No write is required.
- No vendor configuration command is required.
- Normal keyboard traffic appears while the descriptor is open and stops after
  it closes.

Linux's hidraw open causes interrupt-IN polling to remain active. The service
does not hard-code `hidraw2`; it finds the interface by VID/PID, USB interface
number, vendor usage page/usage, report descriptor, and sysfs metadata. It
retries after unplug/replug with backoff and exposes permission, waiting, and
active status.

This is intentionally a user service, not a privileged daemon. The accompanying
udev rule grants access only to the vendor command/event interfaces.
