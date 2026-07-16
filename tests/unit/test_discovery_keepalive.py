from __future__ import annotations

import errno
import os
from pathlib import Path

from vaydeer_studio.devices.discovery import (
    COMMAND_USAGE,
    EVENT_USAGE,
    VENDOR_USAGE_PAGE,
    HidInterface,
    discover_linux_hidraw,
    hidapi_interfaces,
    open_readonly_cloexec,
    select_command_interface,
    select_keepalive_interface,
)
from vaydeer_studio.service.keepalive import KeepaliveManager, KeepaliveState


def event_interface(path: str = "/dev/hidraw7") -> HidInterface:
    return HidInterface(path, 0x0483, 0x5752, 2, VENDOR_USAGE_PAGE, EVENT_USAGE)


def test_keepalive_selects_only_interface_two_with_vendor_usage() -> None:
    interfaces = [
        HidInterface("/dev/hidraw0", 0x0483, 0x5752, 0, VENDOR_USAGE_PAGE, 1),
        HidInterface("/dev/hidraw1", 0x0483, 0x5752, 1, None, None),
        event_interface(),
    ]
    assert select_keepalive_interface(interfaces) == event_interface()


def test_command_interface_selects_only_interface_zero_with_vendor_usage() -> None:
    command = HidInterface("/dev/hidraw5", 0x0483, 0x5752, 0, VENDOR_USAGE_PAGE, COMMAND_USAGE)
    assert select_command_interface([event_interface(), command]) == command


def test_sysfs_discovery_reads_interface_number_and_vendor_usage(tmp_path: Path) -> None:
    sys_class = tmp_path / "sys" / "class" / "hidraw"
    sys_class.mkdir(parents=True)
    hid_device = tmp_path / "sys" / "devices" / "usb" / "1-1" / "1-1:1.2" / "0003:0483:5752.0001"
    hid_device.mkdir(parents=True)
    (hid_device / "uevent").write_text("HID_ID=0003:00000483:00005752\n", encoding="utf-8")
    (hid_device / "report_descriptor").write_bytes(bytes([0x06, 0x00, 0xFF, 0x09, 0x02]))
    (sys_class / "hidraw12").mkdir()
    (sys_class / "hidraw12" / "device").symlink_to(hid_device, target_is_directory=True)

    interfaces = discover_linux_hidraw(sys_class, Path("/dev/mock"))
    assert interfaces == [
        HidInterface("/dev/mock/hidraw12", 0x0483, 0x5752, 2, VENDOR_USAGE_PAGE, EVENT_USAGE, bytes([6, 0, 255, 9, 2]))
    ]


def test_sysfs_metadata_remains_authoritative_when_hidapi_usage_is_incomplete(tmp_path: Path) -> None:
    class IncompleteHidApi:
        @staticmethod
        def enumerate(_vendor_id: int, _product_id: int) -> list[dict[str, object]]:
            return [
                {
                    "path": b"1-2:1.2",
                    "vendor_id": 0x0483,
                    "product_id": 0x5752,
                    "interface_number": 0,
                    "usage_page": 0,
                    "usage": 0,
                }
            ]

    sys_class = tmp_path / "sys" / "class" / "hidraw"
    sys_class.mkdir(parents=True)
    hid_device = tmp_path / "sys" / "devices" / "usb" / "1-2" / "1-2:1.2" / "0003:0483:5752.0001"
    hid_device.mkdir(parents=True)
    (hid_device / "uevent").write_text("HID_ID=0003:00000483:00005752\n", encoding="utf-8")
    (hid_device / "report_descriptor").write_bytes(bytes([0x06, 0x00, 0xFF, 0x09, 0x02]))
    (sys_class / "hidraw18").mkdir()
    (sys_class / "hidraw18" / "device").symlink_to(hid_device, target_is_directory=True)

    assert select_keepalive_interface(hidapi_interfaces(IncompleteHidApi())) is None
    assert select_keepalive_interface(discover_linux_hidraw(sys_class, Path("/dev/mock"))) == HidInterface(
        "/dev/mock/hidraw18", 0x0483, 0x5752, 2, VENDOR_USAGE_PAGE, EVENT_USAGE, bytes([6, 0, 255, 9, 2])
    )


def test_keepalive_open_uses_readonly_cloexec(monkeypatch) -> None:
    captured: list[tuple[str, int]] = []
    monkeypatch.setattr(os, "open", lambda path, flags: captured.append((path, flags)) or 99)
    assert open_readonly_cloexec("/dev/hidraw42") == 99
    assert captured == [("/dev/hidraw42", os.O_RDONLY | os.O_CLOEXEC)]


def test_keepalive_opens_readonly_selected_node_and_handles_unplug() -> None:
    visible = [event_interface("/dev/hidraw9")]
    opened: list[str] = []
    closed: list[int] = []
    manager = KeepaliveManager(
        discover=lambda: visible,
        opener=lambda path: opened.append(path) or 42,
        closer=closed.append,
    )
    assert manager.tick().state == KeepaliveState.ACTIVE
    assert opened == ["/dev/hidraw9"]
    assert manager.tick().state == KeepaliveState.ACTIVE
    assert opened == ["/dev/hidraw9"]
    visible.clear()
    assert manager.tick().state == KeepaliveState.WAITING
    assert closed == [42]


def test_keepalive_reopens_after_hidraw_node_changes_on_replug() -> None:
    visible = [event_interface("/dev/hidraw9")]
    opened: list[str] = []
    closed: list[int] = []
    manager = KeepaliveManager(
        discover=lambda: visible,
        opener=lambda path: opened.append(path) or (40 + len(opened)),
        closer=closed.append,
    )
    assert manager.tick().state == KeepaliveState.ACTIVE
    visible[:] = [event_interface("/dev/hidraw18")]
    assert manager.tick().state == KeepaliveState.ACTIVE
    assert opened == ["/dev/hidraw9", "/dev/hidraw18"]
    assert closed == [41]


def test_keepalive_permission_and_eio_are_not_busy_loops() -> None:
    denied = KeepaliveManager(
        discover=lambda: [event_interface()],
        opener=lambda _: (_ for _ in ()).throw(PermissionError("denied")),
    )
    assert denied.tick().state == KeepaliveState.PERMISSION_DENIED
    eio = KeepaliveManager(
        discover=lambda: [event_interface()],
        opener=lambda _: (_ for _ in ()).throw(OSError(errno.EIO, "gone")),
    )
    assert eio.tick().state == KeepaliveState.WAITING
