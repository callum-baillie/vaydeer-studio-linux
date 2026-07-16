from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from vaydeer_studio.core.errors import DeviceError, ForbiddenCommandError
from vaydeer_studio.devices.transport import HidrawCommandTransport
from vaydeer_studio.protocol.packets import HID_WRITE_SIZE, Command, build_request, make_response


@contextmanager
def no_command_lock(_fd: int, _timeout_ms: int) -> Iterator[None]:
    yield


def test_hidraw_transport_uses_dynamic_path_and_reads_response() -> None:
    opened: list[tuple[str, int]] = []
    written: list[bytes] = []
    transport = HidrawCommandTransport(
        "/dev/hidraw17",
        opener=lambda path, flags: opened.append((path, flags)) or 41,
        writer=lambda _fd, report: written.append(report) or len(report),
        reader=lambda _fd, _size: make_response(Command.READ_DEVICE_INFO, bytes([0, 1, 9])),
        selector=lambda read, _write, _error, _timeout: (read, [], []),
        command_lock=no_command_lock,
    )

    response = transport.transact(build_request(Command.READ_DEVICE_INFO), 500)

    assert opened == [("/dev/hidraw17", os.O_RDWR | os.O_CLOEXEC)]
    assert written == [build_request(Command.READ_DEVICE_INFO)]
    assert response == make_response(Command.READ_DEVICE_INFO, bytes([0, 1, 9]))


def test_hidraw_transport_reports_timeout_without_busy_loop() -> None:
    transport = HidrawCommandTransport(
        "/dev/hidraw17",
        opener=lambda _path, _flags: 41,
        writer=lambda _fd, report: len(report),
        reader=lambda _fd, _size: b"",
        selector=lambda _read, _write, _error, _timeout: ([], [], []),
        command_lock=no_command_lock,
    )

    with pytest.raises(DeviceError, match="timed out"):
        transport.transact(build_request(Command.READ_DEVICE_INFO), 1)


def test_hidraw_transport_rejects_firmware_command_before_write() -> None:
    written: list[bytes] = []
    transport = HidrawCommandTransport(
        "/dev/hidraw17",
        opener=lambda _path, _flags: 41,
        writer=lambda _fd, report: written.append(report) or len(report),
        reader=lambda _fd, _size: b"",
        selector=lambda _read, _write, _error, _timeout: ([], [], []),
        command_lock=no_command_lock,
    )
    forbidden = bytes([0, 0xFC, 0, 0xFC]) + bytes(HID_WRITE_SIZE - 4)

    with pytest.raises(ForbiddenCommandError):
        transport.transact(forbidden, 1)
    assert written == []


def test_hidraw_transport_holds_lock_for_the_complete_exchange() -> None:
    events: list[str] = []

    @contextmanager
    def recording_lock(_fd: int, _timeout_ms: int) -> Iterator[None]:
        events.append("lock")
        try:
            yield
        finally:
            events.append("unlock")

    transport = HidrawCommandTransport(
        "/dev/hidraw18",
        opener=lambda _path, _flags: 41,
        writer=lambda _fd, report: events.append("write") or len(report),
        reader=lambda _fd, _size: events.append("read") or make_response(Command.READ_DEVICE_INFO, bytes([0, 1, 9])),
        selector=lambda read, _write, _error, _timeout: (read, [], []),
        command_lock=recording_lock,
    )

    transport.transact(build_request(Command.READ_DEVICE_INFO), 500)
    assert events == ["lock", "write", "read", "unlock"]
