# Live JP-1011 Detection Repair

**Status:** validated on Linux with the JP-1011 target.

**Retrieval date:** 2026-07-16.
**Safety boundary:** every probe described here used only device-information
and configuration-read commands. No configuration write, firmware command,
packet scan, or firmware updater was used.

## Symptom

The keypad was visible to USB tools and exposed all four expected HID
interfaces, but the desktop application did not show it as connected. A
separate issue was that the keepalive service was not installed, so interface
2 was not held open for normal keyboard activation.

## Observed interface roles

One enumeration exposed these roles. The hidraw numbers are intentionally not
recorded because they are assigned dynamically and can change after reconnect.

| USB interface | HID collection | Role used by Studio |
| --- | --- | --- |
| 0 | vendor `0xFF00` / usage `0x0001`, 64-byte reports | command/configuration |
| 1 | standard keyboard | normal keyboard reports |
| 2 | vendor `0xFF00` / usage `0x0002`, 16-byte reports | read-only keepalive and optional events |
| 3 | mouse, consumer, and system controls | standard auxiliary input |

The live `0x60` read identified the device as type `1`, subtype `9`, firmware
`1.0.2`, bootloader `0.2.1`, active layer `0`, and maximum six layers.

## Root cause

The original command transport passed a Linux hidraw path to `hidapi.open_path`.
On this system, `hidapi.enumerate(0x0483, 0x5752)` instead returned opaque
interface-style paths and empty or zero usage metadata. Neither the opaque path
nor the hidraw path opened successfully through that hidapi build, even though
a normal-user `os.open` of the sysfs-selected command node worked.

That made hidapi enumeration unsuitable as the source of truth for deciding
which HID collection to use. It also made a false “no device” application
state likely despite correct USB enumeration.

The prior udev draft also combined parent-match conditions from different sysfs
levels. udev does not treat such mixed-parent matches as one rule. As a result,
the intended custom rule did not visibly apply during rule testing.

## Repair

1. Discover Linux hidraw nodes from `/sys/class/hidraw`.
2. Read `HID_ID`, resolve the USB interface number, and parse the report
   descriptor for usage page `0xFF00` and the vendor usage.
3. Open only the matching interface-0 node using native Linux hidraw with
   `O_RDWR | O_CLOEXEC`; keep interface 2 separate and read-only.
4. Validate every outgoing report through the protocol allowlist, including the
   hard prohibition on `0xFC`.
5. Serialize each command write/read response pair with a bounded advisory lock
   on the selected command node. This prevents a GUI and CLI diagnostic from
   consuming each other's response.
6. Install a user service that opens only the dynamically selected interface-2
   node with `O_RDONLY | O_CLOEXEC` and keeps it open without a write or polling
   requirement.
7. Match the udev rule at the HID parent and constrain `DEVPATH` to USB
   interfaces `0` and `2`, with mode `0660`, `plugdev` fallback, and `uaccess`.

## Validation

The following checks passed after installation, without a configuration write:

```bash
vaydeer-studio-cli doctor --json --sanitize
vaydeer-studio-cli inspect
systemctl --user status vaydeer-studio.service
```

The diagnostic reported a ready state, normal-user command and keepalive
access, an active read-only keepalive, and the validated JP-1011 capability.
The inspection returned one layer and nine existing numeric-key mappings. Four
concurrent `doctor` probes also completed successfully after command locking.
The Qt Devices view rendered the live firmware, bootloader, layers, permission,
and keepalive state in offscreen smoke validation.

## USB stability note

Historical kernel messages included transient USB transport failures during
earlier reconnect attempts. They did not recur during the final read-only
validation and are not evidence of a protocol problem. If they recur, test a
different cable or port, inspect the kernel USB log, and rerun `doctor`; do not
attempt firmware updates as a recovery step.

## Operator workflow

Run the source installer, physically reconnect after it updates udev rules,
then use `vaydeer-studio-cli doctor`. The UI exposes the same failure states
with retry, setup, and sanitized diagnostic export controls. It never silently
falls back to a guessed hidraw node or elevated GUI execution.
