# Device Architecture

The observed JP-1011 uses an APM32F103CBT6 microcontroller. It exposes four HID
interfaces under VID:PID `0483:5752`:

| USB interface | Role | Collection / report role |
| --- | --- | --- |
| 0 | Vendor command/configuration | Usage page `0xFF00`, usage `0x0001`, 64-byte IN/OUT reports |
| 1 | Standard keyboard | Normal keyboard reports |
| 2 | Vendor physical-key events | Usage page `0xFF00`, usage `0x0002`, 16-byte IN reports |
| 3 | Mouse, consumer, system control | Standard auxiliary HID reports |

The device stores key assignments and layer metadata on-board. Vendor indexing
for the nine keys is row-major: `0` top-left through `8` bottom-right. Device
info identifies available layer capacity; the investigated unit reported six
layers. Standard keyboard, consumer, mouse, and system reports are separate
from the vendor configuration and async-event channels.

The conclusion does not assert that every Vaydeer device has this exact USB
shape. Discovery checks VID/PID, USB interface number, vendor usage page, usage,
report descriptor, and sysfs location before selecting a channel.
