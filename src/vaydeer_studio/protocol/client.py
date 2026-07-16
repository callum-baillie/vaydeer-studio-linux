"""Command implementations with no UI dependencies."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from vaydeer_studio.core.errors import ProtocolError
from vaydeer_studio.core.models import DeviceInfo, DeviceSnapshot, KeyAssignment, Layer, LayerInfo

from .codec import (
    END_MARKER,
    decode_assignment,
    decode_key_header,
    decode_utf16be,
    encode_assignment_frames,
    encode_commit_frame,
    encode_layer_name_frame,
)
from .packets import Command, build_request, parse_response


class CommandTransport(Protocol):
    """A transport that accepts a complete host report and returns one response."""

    def transact(self, report: bytes, timeout_ms: int) -> bytes: ...

    def close(self) -> None: ...


class VaydeerProtocol:
    """Documented configuration protocol; firmware update does not exist here."""

    def __init__(self, transport: CommandTransport, *, timeout_ms: int = 2_000) -> None:
        self._transport = transport
        self.timeout_ms = timeout_ms
        self._session_lock = threading.RLock()
        self._session_depth = 0

    def close(self) -> None:
        self._transport.close()

    @contextmanager
    def session(self) -> Iterator[None]:
        """Keep a compound protocol operation together when the transport supports it."""

        with self._session_lock:
            if self._session_depth:
                self._session_depth += 1
                try:
                    yield
                finally:
                    self._session_depth -= 1
                return

            session_factory: Any = getattr(self._transport, "session", None)
            if not callable(session_factory):
                self._session_depth = 1
                try:
                    yield
                finally:
                    self._session_depth = 0
                return

            with session_factory(self.timeout_ms):
                self._session_depth = 1
                try:
                    yield
                finally:
                    self._session_depth = 0

    def request(self, command: Command, payload: bytes = b"") -> bytes:
        report = build_request(command, payload)
        response = self._transport.transact(report, self.timeout_ms)
        data = parse_response(response, expected_command=command)
        if not data:
            raise ProtocolError(f"Command 0x{int(command):02X} returned no status byte")
        if data[0] != 0:
            raise ProtocolError(f"Command 0x{int(command):02X} failed with device status {data[0]}")
        return data[1:]

    def initialize(self) -> None:
        self.request(Command.INITIALIZE)

    def read_device_info(self) -> DeviceInfo:
        data = self.request(Command.READ_DEVICE_INFO)
        if len(data) < 11:
            raise ProtocolError("Device-info response was shorter than 11 bytes")
        return DeviceInfo(
            device_type=data[0],
            subtype=data[1],
            firmware=(data[2], data[3], data[4]),
            bootloader=(data[5], data[6], data[7]),
            active_layer=data[8],
            layer_count=data[9],
            max_layers=data[10],
            product_name=f"Vaydeer {data[1]}-key keypad",
        )

    def read_layer_info(self) -> LayerInfo:
        data = self.request(Command.READ_LAYER_INFO)
        if len(data) < 3:
            raise ProtocolError("Layer-info response was shorter than three bytes")
        return LayerInfo(active_layer=data[0], layer_count=data[1], max_layers=data[2])

    def read_layer_name(self, layer_index: int) -> str:
        return decode_utf16be(self.request(Command.READ_LAYER_NAME, bytes([layer_index])))

    def set_active_layer(self, layer_index: int) -> None:
        self.request(Command.CHANGE_ACTIVE_LAYER, bytes([layer_index]))

    def read_key_assignment(self, layer_index: int, key_index: int) -> KeyAssignment:
        with self.session():
            header_data = self.request(Command.READ_KEY, bytes([0xFF, layer_index, key_index]))
            header = decode_key_header(header_data)
            chunks = bytearray()
            for sequence in range(16):
                chunk = self.request(Command.READ_KEY, bytes([sequence, layer_index, key_index]))
                if not chunk:
                    raise ProtocolError("Read-key data response was empty")
                if chunk[0] == END_MARKER:
                    return decode_assignment(key_index, header, bytes(chunks))
                chunks.extend(chunk[1:])
            raise ProtocolError("Read-key did not terminate within the documented sequence range")

    def write_key_assignment(self, layer_index: int, assignment: KeyAssignment) -> None:
        with self.session():
            for frame in encode_assignment_frames(layer_index, assignment):
                response = self._transport.transact(frame, self.timeout_ms)
                data = parse_response(response, expected_command=Command.WRITE_KEY)
                if not data or data[0] != 0:
                    raise ProtocolError("Write-key command was rejected by the device")

    def write_layer_name(self, layer_index: int, maximum_layer_index: int, name: str) -> None:
        with self.session():
            self._write_frame(encode_layer_name_frame(layer_index, maximum_layer_index, name), Command.WRITE_LAYER_NAME)

    def commit_layer(self, layer_index: int, maximum_layer_index: int) -> None:
        with self.session():
            self._write_frame(encode_commit_frame(layer_index, maximum_layer_index), Command.COMMIT_LAYER)

    def _write_frame(self, frame: bytes, command: Command) -> None:
        response = self._transport.transact(frame, self.timeout_ms)
        data = parse_response(response, expected_command=command)
        if not data or data[0] != 0:
            raise ProtocolError(f"Command 0x{int(command):02X} was rejected by the device")

    def read_snapshot(self) -> DeviceSnapshot:
        with self.session():
            info = self.read_device_info()
            layer_info = self.read_layer_info()
            layers: list[Layer] = []
            for layer_index in range(layer_info.layer_count):
                assignments = [self.read_key_assignment(layer_index, key) for key in range(info.key_count)]
                layers.append(Layer(index=layer_index, name=self.read_layer_name(layer_index), assignments=assignments))
            return DeviceSnapshot(device=info, layers=layers)

    def preview_write_packets(self, snapshot: DeviceSnapshot) -> list[bytes]:
        packets: list[bytes] = []
        maximum_layer_index = max(0, snapshot.device.max_layers - 1)
        for layer in snapshot.layers:
            packets.append(encode_layer_name_frame(layer.index, maximum_layer_index, layer.name))
            for assignment in layer.assignments:
                packets.extend(encode_assignment_frames(layer.index, assignment))
            packets.append(encode_commit_frame(layer.index, maximum_layer_index))
        return packets
