from __future__ import annotations

import errno

from vaydeer_studio.devices.discovery import EVENT_USAGE, VENDOR_USAGE_PAGE, HidInterface, select_keepalive_interface
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
