"""HID discovery that identifies the JP-1011 event interface without hidraw numbers."""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vaydeer_studio.core.errors import DeviceError

VAYDEER_VID = 0x0483
VAYDEER_PID = 0x5752
VENDOR_USAGE_PAGE = 0xFF00
COMMAND_USAGE = 0x0001
EVENT_USAGE = 0x0002

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HidInterface:
    path: str
    vendor_id: int
    product_id: int
    interface_number: int | None
    usage_page: int | None
    usage: int | None
    report_descriptor: bytes = b""
    serial: str = ""
    product: str = ""

    @property
    def is_vaydeer(self) -> bool:
        return self.vendor_id == VAYDEER_VID and self.product_id == VAYDEER_PID


def _parse_usage(descriptor: bytes) -> tuple[int | None, int | None]:
    """Read the primary vendor usage from short HID items without external tooling."""

    page: int | None = None
    usage: int | None = None
    index = 0
    while index < len(descriptor):
        prefix = descriptor[index]
        if prefix == 0xFE:
            if index + 2 >= len(descriptor):
                break
            index += 3 + descriptor[index + 1]
            continue
        size_code = prefix & 0x03
        size = 4 if size_code == 3 else size_code
        item_type = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        data = descriptor[index + 1 : index + 1 + size]
        value = int.from_bytes(data, "little") if data else 0
        if item_type == 1 and tag == 0:  # Global Usage Page
            page = value
        elif item_type == 2 and tag == 0 and page == VENDOR_USAGE_PAGE:  # Local Usage
            usage = value
            break
        index += 1 + size
    return page, usage


def _interface_number(real_path: Path) -> int | None:
    match = re.search(r":1\.(\d+)(?:/|$)", str(real_path))
    return int(match.group(1)) if match else None


def _hid_identity(uevent: str) -> tuple[int, int] | None:
    match = re.search(r"HID_ID=\w+:([0-9A-Fa-f]{8}):([0-9A-Fa-f]{8})", uevent)
    if not match:
        return None
    return int(match.group(1), 16), int(match.group(2), 16)


def discover_linux_hidraw(
    sys_class: Path = Path("/sys/class/hidraw"), dev_root: Path = Path("/dev")
) -> list[HidInterface]:
    """Inspect sysfs metadata and report descriptors for each hidraw node."""

    discovered: list[HidInterface] = []
    if not sys_class.exists():
        return discovered
    for entry in sorted(sys_class.glob("hidraw*")):
        try:
            device = (entry / "device").resolve()
            identity = _hid_identity((device / "uevent").read_text(encoding="utf-8", errors="replace"))
            descriptor = (device / "report_descriptor").read_bytes()
        except OSError as error:
            LOGGER.debug("HID candidate rejected: node=%s reason=sysfs_unreadable error=%s", entry.name, error)
            continue
        if identity is None:
            LOGGER.debug("HID candidate rejected: node=%s reason=missing_hid_identity", entry.name)
            continue
        page, usage = _parse_usage(descriptor)
        LOGGER.debug(
            "HID candidate discovered: node=%s vid=%04x pid=%04x interface=%s usage=%s/%s",
            entry.name,
            identity[0],
            identity[1],
            _interface_number(device),
            f"{page:#06x}" if page is not None else "missing",
            f"{usage:#06x}" if usage is not None else "missing",
        )
        discovered.append(
            HidInterface(
                path=str(dev_root / entry.name),
                vendor_id=identity[0],
                product_id=identity[1],
                interface_number=_interface_number(device),
                usage_page=page,
                usage=usage,
                report_descriptor=descriptor,
            )
        )
    return discovered


def select_keepalive_interface(interfaces: Iterable[HidInterface]) -> HidInterface | None:
    """Return only JP-1011 interface 2 with the matching vendor collection."""

    matches = _select_interfaces(interfaces, interface_number=2, usage=EVENT_USAGE, role="keepalive")
    if len(matches) > 1:
        raise DeviceError("Multiple JP-1011 vendor event interfaces matched; refusing to guess")
    return matches[0] if matches else None


def select_command_interface(interfaces: Iterable[HidInterface]) -> HidInterface | None:
    matches = _select_interfaces(interfaces, interface_number=0, usage=COMMAND_USAGE, role="command")
    if len(matches) > 1:
        raise DeviceError("Multiple Vaydeer command interfaces matched; refusing to guess")
    return matches[0] if matches else None


def hidapi_interfaces(hid_module: Any | None = None) -> list[HidInterface]:
    """Discover command and event interfaces through hidapi for cross-desktop use."""

    if hid_module is None:
        try:
            import hid
        except ImportError as error:
            raise DeviceError("hidapi is unavailable; install dependencies with uv sync") from error
        hid_module = hid
    assert hid_module is not None
    raw_devices = hid_module.enumerate(VAYDEER_VID, VAYDEER_PID)
    result: list[HidInterface] = []
    for raw in raw_devices:
        path_value = raw.get("path", b"")
        path = path_value.decode(errors="replace") if isinstance(path_value, bytes) else str(path_value)
        result.append(
            HidInterface(
                path=path,
                vendor_id=int(raw.get("vendor_id") or 0),
                product_id=int(raw.get("product_id") or 0),
                interface_number=_maybe_int(raw.get("interface_number")),
                usage_page=_maybe_int(raw.get("usage_page")),
                usage=_maybe_int(raw.get("usage")),
                serial=str(raw.get("serial_number") or ""),
                product=str(raw.get("product_string") or ""),
            )
        )
    return result


def group_physical_devices(interfaces: Iterable[HidInterface]) -> dict[str, list[HidInterface]]:
    groups: dict[str, list[HidInterface]] = defaultdict(list)
    for interface in interfaces:
        key = interface.serial or _path_group_key(interface.path)
        groups[key].append(interface)
    return dict(groups)


def _path_group_key(path: str) -> str:
    lower = path.lower()
    for token in ("&mi_", "#mi_", ":1."):
        if token in lower:
            return lower.split(token, 1)[0]
    return lower


def _maybe_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def open_readonly_cloexec(path: str) -> int:
    """Open a dynamically discovered hidraw node without reading or writing it."""

    return os.open(path, os.O_RDONLY | os.O_CLOEXEC)


def _select_interfaces(
    interfaces: Iterable[HidInterface], *, interface_number: int, usage: int, role: str
) -> list[HidInterface]:
    matches: list[HidInterface] = []
    for interface in interfaces:
        if not interface.is_vaydeer:
            continue
        reason: str | None = None
        if interface.interface_number != interface_number:
            reason = f"interface_number={interface.interface_number!r}"
        elif interface.usage_page != VENDOR_USAGE_PAGE:
            reason = f"usage_page={interface.usage_page!r}"
        elif interface.usage != usage:
            reason = f"usage={interface.usage!r}"
        if reason is not None:
            LOGGER.debug("HID candidate rejected: node=%s role=%s reason=%s", interface.path, role, reason)
            continue
        matches.append(interface)
    return matches
