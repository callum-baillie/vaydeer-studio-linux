"""Safe command-channel HID transport."""

from __future__ import annotations

import errno
import fcntl
import os
import select
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from typing import Any

from vaydeer_studio.core.errors import DeviceError
from vaydeer_studio.protocol.packets import HID_WRITE_SIZE, assert_permitted_command

Selector = Callable[
    [list[int], list[int], list[int], float],
    tuple[list[int], list[int], list[int]],
]
CommandLock = Callable[[int, int], AbstractContextManager[None]]


class HidApiCommandTransport:
    """A small adapter over hidapi that does not expose arbitrary handles to callers."""

    def __init__(self, path: str | bytes, hid_module: Any | None = None) -> None:
        if hid_module is None:
            try:
                import hid
            except ImportError as error:
                raise DeviceError("hidapi is unavailable; install dependencies with uv sync") from error
            hid_module = hid
        assert hid_module is not None
        self._handle = hid_module.device()
        self._handle.open_path(path.encode() if isinstance(path, str) else path)

    def transact(self, report: bytes, timeout_ms: int) -> bytes:
        _validate_command_report(report)
        try:
            self._handle.write(list(report))
            return bytes(self._handle.read(64, timeout_ms))
        except OSError as error:
            raise DeviceError(f"HID command transport failed: {error}") from error

    def close(self) -> None:
        close = getattr(self._handle, "close", None)
        if close is not None:
            close()


class HidrawCommandTransport:
    """Linux-native command transport for kernels where hidapi cannot open hidraw."""

    def __init__(
        self,
        path: str,
        *,
        opener: Callable[[str, int], int] = os.open,
        closer: Callable[[int], None] = os.close,
        writer: Callable[[int, bytes], int] = os.write,
        reader: Callable[[int, int], bytes] = os.read,
        selector: Selector = select.select,
        command_lock: CommandLock | None = None,
    ) -> None:
        self.path = path
        self._closer = closer
        self._writer = writer
        self._reader = reader
        self._selector = selector
        self._command_lock = command_lock or _lock_command_fd
        try:
            self._fd: int | None = opener(path, os.O_RDWR | os.O_CLOEXEC)
        except PermissionError as error:
            raise DeviceError(f"Permission denied opening Vaydeer command interface {path}") from error
        except OSError as error:
            raise DeviceError(f"Could not open Vaydeer command interface {path}: {error}") from error

    def transact(self, report: bytes, timeout_ms: int) -> bytes:
        _validate_command_report(report)
        if self._fd is None:
            raise DeviceError("Vaydeer command transport is closed")
        try:
            # A hidraw endpoint has one shared response queue. Serialize the full
            # write/read exchange across GUI and CLI processes, never just the write.
            with self._command_lock(self._fd, timeout_ms):
                written = self._writer(self._fd, report)
                if written != len(report):
                    raise DeviceError(f"HID command write was partial: {written} of {len(report)} bytes")
                readable, _, _ = self._selector([self._fd], [], [], timeout_ms / 1000)
                if not readable:
                    raise DeviceError("Vaydeer command interface timed out waiting for a response")
                return self._reader(self._fd, 64)
        except DeviceError:
            raise
        except OSError as error:
            if error.errno in {errno.ENODEV, errno.EIO, errno.ENOENT}:
                raise DeviceError("Vaydeer command interface disappeared; reconnect the keypad and retry") from error
            raise DeviceError(f"HID command transport failed: {error}") from error

    def close(self) -> None:
        if self._fd is not None:
            try:
                self._closer(self._fd)
            finally:
                self._fd = None


def open_command_transport(path: str) -> HidrawCommandTransport:
    """Open only a sysfs-selected Linux hidraw command node; never a guessed node."""

    return HidrawCommandTransport(path)


def _validate_command_report(report: bytes) -> None:
    if len(report) != HID_WRITE_SIZE or not report:
        raise DeviceError(f"Invalid HID command report length: {len(report)}")
    if report[0] != 0:
        raise DeviceError("Vaydeer command reports must start with report ID 0x00")
    assert_permitted_command(report[1])


@contextmanager
def _lock_command_fd(fd: int, timeout_ms: int) -> Iterator[None]:
    """Take a bounded advisory lock on the selected command interface.

    Linux applies ``flock`` to hidraw nodes, allowing independent Studio
    processes to avoid consuming each other's response. The lock is released
    automatically on close, including an unplug or crashed client.
    """

    deadline = time.monotonic() + max(timeout_ms, 1) / 1000
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError as error:
            if time.monotonic() >= deadline:
                raise DeviceError("Vaydeer command interface is busy; retry the operation") from error
            time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        except OSError as error:
            raise DeviceError(f"Could not lock Vaydeer command interface: {error}") from error
    try:
        yield
    finally:
        # The fd can already be invalid after an unplug; the OS releases it.
        with suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
