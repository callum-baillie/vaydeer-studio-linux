"""Version-aware capability policy: unknown firmware is intentionally read-only."""

from __future__ import annotations

from dataclasses import dataclass

from vaydeer_studio.core.models import AssignmentKind, DeviceInfo


@dataclass(frozen=True)
class DeviceCapability:
    model: str
    key_count: int
    readable: bool
    writable: bool
    firmware_known: bool
    reason: str
    stable_kinds: frozenset[AssignmentKind]


_STABLE_KINDS = frozenset(
    {
        AssignmentKind.KEYBOARD,
        AssignmentKind.MODIFIER,
        AssignmentKind.COMBINATION,
        AssignmentKind.MEDIA,
        AssignmentKind.SYSTEM,
        AssignmentKind.DISABLED,
    }
)


def capability_for(info: DeviceInfo) -> DeviceCapability:
    """Return the narrowest safe capability based on device identity and firmware."""

    identity = (info.vendor_id, info.product_id, info.device_type, info.subtype)
    if identity == (0x0483, 0x5752, 1, 9) and info.firmware == (1, 0, 2) and info.bootloader == (0, 2, 1):
        return DeviceCapability(
            model="JP-1011",
            key_count=9,
            readable=True,
            writable=True,
            firmware_known=True,
            reason="Validated JP-1011 capability record for firmware 1.0.2 / bootloader 0.2.1.",
            stable_kinds=_STABLE_KINDS,
        )
    if identity[:3] == (0x0483, 0x5752, 1) and info.subtype in {1, 4, 6, 9}:
        return DeviceCapability(
            model=f"Generic Vaydeer {info.subtype}-key",
            key_count=info.subtype,
            readable=True,
            writable=False,
            firmware_known=False,
            reason=(
                f"Firmware {info.firmware_version} / bootloader {info.bootloader_version} is not in the "
                "write-validated capability table. Inspection and export are available."
            ),
            stable_kinds=frozenset(),
        )
    return DeviceCapability(
        model="Unknown Vaydeer-compatible HID device",
        key_count=info.key_count,
        readable=True,
        writable=False,
        firmware_known=False,
        reason="Unknown type, subtype, or firmware. Vaydeer Studio will not enable writes.",
        stable_kinds=frozenset(),
    )
