# Device Support

The primary supported target is Vaydeer JP-1011 PCB `JP1E0111-V1.2`, USB
VID:PID `0483:5752`, firmware `1.0.2`, and bootloader `0.2.1`. It has nine
keys in a verified 3-by-3 layout and reports up to six layers.

The capability registry gates writes on VID, PID, type/subtype-derived key
count, firmware, and bootloader. The exact observed JP-1011 tuple enables only
single key, modifier, key combination, media, system-control, disable, layer
name, active-layer, and commit operations. Other firmware is exportable and
inspectable but read-only.

The common-protocol one-, four-, six-, and nine-key adapters are intentionally
conservative. One/four/six layouts are selectable generic layouts unless a
reliable physical arrangement has been captured. No guessed visual arrangement
influences protocol key indexing.

On Linux, live detection requires sysfs HID metadata plus the report descriptor
to identify the four interface roles. hidapi enumeration remains a dependency
for compatibility experiments but is not trusted as the sole source of usage
metadata. See [live-device-detection-debug.md](research/live-device-detection-debug.md).

## Experimental categories

Mouse, macro, text, host trigger, Vaydeer action, layer action, and special
assignments have typed profile representations and visible editor categories.
Their undocumented wire payloads are not stable: they may be decoded as an
experimental record, but they cannot be serialized to a physical device. Mock
fixtures and the protocol research document the next evidence needed.
