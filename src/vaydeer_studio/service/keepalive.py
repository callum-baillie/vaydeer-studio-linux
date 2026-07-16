"""JP-1011 interface-2 keepalive with no fixed hidraw node and no writes."""

from __future__ import annotations

import contextlib
import errno
import logging
import os
import select
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import StrEnum

from vaydeer_studio.devices.discovery import (
    HidInterface,
    discover_linux_hidraw,
    open_readonly_cloexec,
    select_keepalive_interface,
)

LOGGER = logging.getLogger(__name__)


class KeepaliveState(StrEnum):
    STOPPED = "stopped"
    WAITING = "waiting_for_device"
    ACTIVE = "active_readonly"
    PERMISSION_DENIED = "permission_denied"
    ERROR = "error"


@dataclass(frozen=True)
class KeepaliveStatus:
    state: KeepaliveState
    node: str | None
    message: str
    event_listening: bool


class KeepaliveManager:
    """Holds exactly the confirmed vendor async interface open O_RDONLY|O_CLOEXEC."""

    def __init__(
        self,
        *,
        discover: Callable[[], list[HidInterface]] = discover_linux_hidraw,
        opener: Callable[[str], int] = open_readonly_cloexec,
        closer: Callable[[int], None] = os.close,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        retry_seconds: float = 2.0,
    ) -> None:
        self._discover = discover
        self._opener = opener
        self._closer = closer
        self._sleeper = sleeper
        self._clock = clock
        self.retry_seconds = retry_seconds
        self._fd: int | None = None
        self._node: str | None = None
        self._instance_key: str | None = None
        self._event_listening = False
        self._retry_after = 0.0
        self._status = KeepaliveStatus(KeepaliveState.STOPPED, None, "Not started", False)
        self._lock = threading.Lock()

    def status(self) -> dict[str, object]:
        with self._lock:
            return asdict(self._status)

    def set_event_listening(self, enabled: bool) -> None:
        with self._lock:
            self._event_listening = enabled
            self._set_status(self._status.state, self._status.node, self._status.message)

    def tick(self) -> KeepaliveStatus:
        """One hotplug-aware iteration, convenient for testing and service loops."""

        with self._lock:
            if self._fd is None and self._clock() < self._retry_after:
                return self._status
            try:
                target = select_keepalive_interface(self._discover())
            except Exception as error:
                self._close_locked()
                self._set_status(KeepaliveState.ERROR, None, str(error))
                return self._status
            if target is None:
                self._close_locked()
                self._set_status(KeepaliveState.WAITING, None, "JP-1011 interface 2 is not connected")
                self._retry_after = self._clock() + self.retry_seconds
                return self._status
            if self._fd is not None and self._node == target.path and self._instance_key == target.instance_key:
                self._set_status(KeepaliveState.ACTIVE, target.path, "Read-only interface 2 handle is open")
                return self._status
            self._close_locked()
            try:
                self._fd = self._opener(target.path)
                self._node = target.path
                self._instance_key = target.instance_key
                self._retry_after = 0.0
                self._set_status(KeepaliveState.ACTIVE, target.path, "Read-only interface 2 handle is open")
            except PermissionError as error:
                self._set_status(KeepaliveState.PERMISSION_DENIED, target.path, str(error))
                self._retry_after = self._clock() + self.retry_seconds
            except OSError as error:
                state = (
                    KeepaliveState.WAITING
                    if error.errno in {errno.ENODEV, errno.EIO, errno.ENOENT}
                    else KeepaliveState.ERROR
                )
                self._set_status(state, target.path, str(error))
                self._retry_after = self._clock() + self.retry_seconds
            return self._status

    def read_event(self, max_bytes: int = 16) -> bytes | None:
        """Read only when live-event handling was explicitly enabled."""

        with self._lock:
            if not self._event_listening or self._fd is None:
                return None
            try:
                if not select.select([self._fd], [], [], 0)[0]:
                    return None
                return os.read(self._fd, max_bytes)
            except BlockingIOError:
                return None
            except OSError as error:
                if error.errno in {errno.EIO, errno.ENODEV}:
                    self._close_locked()
                    self._set_status(KeepaliveState.WAITING, None, "Device unplugged while reading vendor events")
                    self._retry_after = self._clock() + self.retry_seconds
                    return None
                raise

    def run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            self.tick()
            stop.wait(self.retry_seconds)
        self.stop()

    def run_for(self, seconds: float) -> None:
        if seconds <= 0:
            self.tick()
            return
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.tick()
            self._sleeper(min(self.retry_seconds, max(0.0, deadline - time.monotonic())))
        self.stop()

    def stop(self) -> None:
        with self._lock:
            self._close_locked()
            self._set_status(KeepaliveState.STOPPED, None, "Stopped")

    def _close_locked(self) -> None:
        if self._fd is not None:
            with contextlib.suppress(OSError):
                self._closer(self._fd)
        self._fd = None
        self._node = None
        self._instance_key = None

    def _set_status(self, state: KeepaliveState, node: str | None, message: str) -> None:
        if (state, node, message) != (self._status.state, self._status.node, self._status.message):
            LOGGER.info("Keepalive state=%s node=%s message=%s", state, node or "none", message)
        self._status = KeepaliveStatus(state, node, message, self._event_listening)
