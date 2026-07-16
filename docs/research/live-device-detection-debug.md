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

## Sanitized host inventory

The validation host was Ubuntu 25.10 on Linux `6.17.0-40-generic`, using an
X11/LXQt desktop session. The normal desktop user had the `plugdev` group and
an active `uaccess` ACL. The source installation used Python `3.14.3` and uv
`0.10.3`; the project itself supports Python 3.11 and later. No mock-mode
environment setting was active. The installed user service was active and held
the event interface as a read-only file descriptor.

The following table records one sanitized enumeration. `<instance>` is a
kernel-assigned HID instance suffix and `<hidrawN>` is explicitly variable
across reconnects. Descriptor values are included because they are protocol
evidence, not device identifiers.

| USB interface | Sanitized sysfs shape | Observed hidraw | Usage page / usage | Descriptor prefix | Access | Open-process role |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `.../usb/1-2/1-2:1.0/0003:0483:5752.<instance>` | `/dev/hidraw0` | `0xFF00` / `0x0001` | `06 00 ff 09 01` | `crw-rw---- root:plugdev`, ACL, normal-user read/write open | Studio command transport only |
| 1 | `.../usb/1-2/1-2:1.1/0003:0483:5752.<instance>` | `/dev/hidraw1` | keyboard page / no vendor usage | `05 01 09 06` | `crw-rw---- root:plugdev`, ACL, normal-user read open | Linux keyboard input |
| 2 | `.../usb/1-2/1-2:1.2/0003:0483:5752.<instance>` | `/dev/hidraw2` | `0xFF00` / `0x0002` | `06 00 ff 09 02` | `crw-rw---- root:plugdev`, ACL, normal-user read open | `vaydeer-studiod`, read-only keepalive |
| 3 | `.../usb/1-2/1-2:1.3/0003:0483:5752.<instance>` | `/dev/hidraw3` | mouse page / no vendor usage | `05 01 09 02` | `crw-rw---- root:plugdev`, ACL, normal-user read open | Linux mouse, consumer, and system input |

`udevadm test` confirmed that the installed Vaydeer Studio rule applies mode
`0660`, group `plugdev`, and `uaccess` only to interfaces 0 and 2. The service
unit runs through the user-level launcher rather than a privileged GUI. A
verbose diagnostic intentionally omits serial values while reporting the same
usage, permission, service, and protocol facts.

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
5. Serialize entire command sessions with a bounded advisory lock on the
   selected command node. Before the first request, discard any response frames
   already queued by a prior client. This prevents a GUI and CLI diagnostic
   from consuming each other's response during multi-frame reads.
6. Install a user service that opens only the dynamically selected interface-2
   node with `O_RDONLY | O_CLOEXEC` and keeps it open without a write or polling
   requirement.
7. Match the udev rule at the HID parent and constrain `DEVPATH` to USB
   interfaces `0` and `2`, with mode `0660`, `plugdev` fallback, and `uaccess`.
8. Track the sysfs HID-instance path in addition to the hidraw node. If Linux
   reuses the same hidraw number after a replug, both the keepalive and UI
   reopen their handles instead of mistaking a stale descriptor for a live one.

## Validation

The following checks passed after installation, without a configuration write:

```bash
vaydeer-studio-cli doctor --json --sanitize
vaydeer-studio-cli inspect
systemctl --user status vaydeer-studio.service
```

The diagnostic reported a ready state, normal-user command and keepalive
access, an active read-only keepalive, and the validated JP-1011 capability.
The inspection returned one layer and nine existing numeric-key mappings. The
Qt Devices view rendered the live firmware, bootloader, layers, permission, and
keepalive state in offscreen smoke validation.

### Concurrent client correction

Initial one-request concurrent `doctor` probes passed with an exchange-level
lock. A later concurrent, read-only `inspect` and Qt snapshot exposed a more
subtle HID behavior: clients which had already opened interface 0 could retain
a response broadcast by another client. That left an old response at the head
of the next client's queue, which correctly failed checksum/command validation
instead of being mistaken for valid device state.

The transport now takes the advisory lock for the full protocol session. A
snapshot holds one lock for device information, layer information, names, and
every multi-frame key read; an approved configuration transaction holds one
lock through writes and read-back verification. The newly locked session drains
up to 256 already-readable frames before it sends its first known request. It
aborts without a write if the queue remains nonempty after that limit. It never
sends arbitrary or firmware commands. Unit and integration coverage
exercises the stale-frame and compound-session cases.

The corrected path was validated on the connected JP-1011 with two simultaneous
`vaydeer-studio-cli inspect` processes and an offscreen live Qt Devices view.
All three completed successfully and reported firmware `1.0.2`, bootloader
`0.2.1`, one layer, and nine numeric-key assignments. This used only the
reviewed initialization and read commands; no configuration write occurred.

## Reconnect validation status

The service and controller both have automated coverage for disappearance,
startup races, changed hidraw nodes, and same-node reuse after a replug. A
controlled 2026-07-16 physical validation completed after the required
preparation notice and countdown. The observed sequence was:

| Observation | USB VID:PID | Controller state | Keepalive state |
| --- | --- | --- | --- |
| Immediately after unplug | absent | `no_device` | `waiting_for_device` |
| USB re-enumerated | present | discovery retry in progress | `waiting_for_device` |
| Command channel restored | present | `connected` | `waiting_for_device` |
| Event keepalive restored | present | `connected` | `active_readonly` |

The controller was deliberately launched while the device was absent, proving
automatic recovery from a real startup/reconnect race without pressing Retry.
The existing GUI-model regression test separately proves the already-connected
state becomes **Vaydeer keypad disconnected** when the command interface
disappears. Together these cover physical re-enumeration and the two UI
connection transitions without any configuration write.

The post-reconnect validation commands were:

```bash
systemctl --user status vaydeer-studio.service
vaydeer-studio-cli doctor --json --sanitize
```

They reported a fresh interface-2 read-only handle and `"ready": true`.

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
