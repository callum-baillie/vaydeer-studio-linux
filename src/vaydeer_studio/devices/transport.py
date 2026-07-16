"""Safe command-channel HID transport."""

from __future__ import annotations

from typing import Any

from vaydeer_studio.core.errors import DeviceError


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
        try:
            self._handle.write(list(report))
            return bytes(self._handle.read(64, timeout_ms))
        except OSError as error:
            raise DeviceError(f"HID command transport failed: {error}") from error

    def close(self) -> None:
        close = getattr(self._handle, "close", None)
        if close is not None:
            close()
