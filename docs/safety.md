# Safety

Vaydeer Studio configures physical USB hardware and uses a deny-by-default
protocol boundary.

## Non-negotiable restrictions

- Firmware command `0xFC` is absent from the public command enum and is
  rejected even when requested by numeric value.
- Unknown command IDs are rejected before a transport can receive bytes.
- The app has no firmware UI, raw packet sender, command scanner, bootloader
  controls, or official-updater integration.
- Unknown firmware is read-only. Experimental assignment payloads are never
  serialized for physical hardware.
- The keepalive opens only the dynamically matched vendor event interface with
  `O_RDONLY | O_CLOEXEC`; it never writes to it.
- A reconnect is identified by the selected sysfs HID instance as well as the
  hidraw node, so reusing a node name cannot retain a stale keepalive handle.

## Write sequence

1. Match VID:PID and the vendor command interface.
2. Read device info and match the capability table.
3. Read all layers, names, and assignments.
4. Save an XDG timestamped JSON backup.
5. Produce a packet list and human-readable diff.
6. Require confirmation. Real writes require `--confirm-real-write` plus the
   typed terminal word `APPLY`.
7. Write stable assignments/layer names, commit the layer, and read back.
8. Compare the expected snapshot to the actual snapshot and retain the backup.

The full write and verification sequence uses one exclusive command session.
This prevents an independent Studio CLI or desktop inspection from interleaving
with a multi-frame operation; stale interface-0 response frames are discarded
before the session's first known request.

The graphical application performs no real write; this makes the terminal
review an intentional, auditable boundary. A dry run never writes.

## Backups and diagnostics

Backups are portable, versioned JSON in the user's XDG data directory. A failed
or partial write does not delete or overwrite them. Diagnostics omit serial
numbers and home-directory paths where practical. Do not attach unsanitized
system logs to public issues.
