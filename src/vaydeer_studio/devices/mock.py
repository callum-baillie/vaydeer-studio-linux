"""Deterministic JP-1011 hardware model for UI demos and automated tests."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass

from vaydeer_studio.core.errors import DeviceError
from vaydeer_studio.core.models import AssignmentKind, DeviceInfo, DeviceSnapshot, KeyAssignment, Layer
from vaydeer_studio.protocol.codec import decode_utf16be, encode_utf16be
from vaydeer_studio.protocol.packets import Command, make_response


@dataclass
class _WriteContext:
    layer_index: int
    key_index: int
    key_type: int
    subtype: int
    trigger_type: int
    label: str
    data: bytearray


class MockJP1011Transport:
    """Emulates known configuration commands, errors, events, disconnects, and replug."""

    def __init__(self) -> None:
        self.connected = True
        self.permission_denied = False
        self.checksum_failure = False
        self.fail_after_writes: int | None = None
        self._write_count = 0
        self._write_context: _WriteContext | None = None
        self._read_context: tuple[int, int] | None = None
        self._events: deque[bytes] = deque()
        codes = [103, 104, 105, 100, 101, 102, 97, 98, 99]
        labels = ["Num 7", "Num 8", "Num 9", "Num 4", "Num 5", "Num 6", "Num 1", "Num 2", "Num 3"]
        self.info = DeviceInfo(
            device_type=1,
            subtype=9,
            firmware=(1, 0, 2),
            bootloader=(0, 2, 1),
            active_layer=0,
            layer_count=1,
            max_layers=6,
            product_name="Vaydeer JP-1011",
        )
        self.layers = [
            Layer(
                index=0,
                name="0",
                assignments=[
                    KeyAssignment(key_index=index, label=labels[index], kind=AssignmentKind.KEYBOARD, key_codes=[code])
                    for index, code in enumerate(codes)
                ],
            )
        ]

    def close(self) -> None:
        return None

    def disconnect(self) -> None:
        self.connected = False

    def reconnect(self) -> None:
        self.connected = True

    def snapshot(self) -> DeviceSnapshot:
        info = self.info.model_copy(update={"layer_count": len(self.layers)})
        return DeviceSnapshot(device=info, layers=deepcopy(self.layers))

    def queue_event(self, key_index: int, pressed: bool = True, layer_index: int = 0) -> bytes:
        event = 0x00 if pressed else 0x02
        raw = bytes([0xFB, 0x03, layer_index, key_index, event])
        report = raw + bytes([raw[0] ^ raw[1] ^ raw[2] ^ raw[3] ^ raw[4]]) + bytes(10)
        self._events.append(report)
        return report

    def read_event(self) -> bytes | None:
        return self._events.popleft() if self._events else None

    def transact(self, report: bytes, timeout_ms: int) -> bytes:
        del timeout_ms
        if self.permission_denied:
            raise PermissionError("Mock hidraw permission denied")
        if not self.connected:
            raise DeviceError("Mock JP-1011 is disconnected")
        command, payload = self._request(report)
        response = self._dispatch(command, payload)
        if self.checksum_failure:
            return response[:-1] + bytes([response[-1] ^ 0xFF])
        return response

    def _request(self, report: bytes) -> tuple[Command, bytes]:
        if len(report) < 4 or report[0] != 0:
            raise DeviceError("Mock received an invalid HID report")
        command = Command(report[1])
        length = report[2]
        meaningful = report[: 4 + length]
        body = meaningful[1:-1]
        expected = 0
        for value in body:
            expected ^= value
        if expected != meaningful[-1]:
            raise DeviceError("Mock received a bad request checksum")
        return command, report[3 : 3 + length]

    def _dispatch(self, command: Command, payload: bytes) -> bytes:
        if command == Command.INITIALIZE:
            return make_response(command, bytes([0]))
        if command == Command.READ_DEVICE_INFO:
            info = self.info.model_copy(update={"layer_count": len(self.layers)})
            data = bytes(
                [
                    0,
                    info.device_type,
                    info.subtype,
                    *info.firmware,
                    *info.bootloader,
                    info.active_layer,
                    len(self.layers),
                    info.max_layers,
                ]
            )
            return make_response(command, data)
        if command == Command.READ_LAYER_INFO:
            return make_response(command, bytes([0, self.info.active_layer, len(self.layers), self.info.max_layers]))
        if command == Command.READ_LAYER_NAME:
            return make_response(command, bytes([0]) + encode_utf16be(self._layer(payload[0]).name))
        if command == Command.CHANGE_ACTIVE_LAYER:
            self.info = self.info.model_copy(update={"active_layer": payload[0]})
            return make_response(command, bytes([0]))
        if command == Command.READ_KEY:
            return self._read_key(payload)
        if command == Command.WRITE_KEY:
            return self._write_key(payload)
        if command == Command.WRITE_LAYER_NAME:
            layer_index, _maximum = payload[:2]
            layer = self._layer(layer_index)
            replacement = layer.model_copy(update={"name": decode_utf16be(payload[2:])})
            self._replace_layer(replacement)
            return make_response(command, bytes([0]))
        if command == Command.COMMIT_LAYER:
            self._increment_write_count()
            return make_response(command, bytes([0]))
        raise DeviceError(f"Mock cannot dispatch command {command}")

    def _read_key(self, payload: bytes) -> bytes:
        if len(payload) != 3:
            raise DeviceError("Malformed mock read-key payload")
        marker, layer_index, key_index = payload
        assignment = self._layer(layer_index).assignment_for(key_index)
        if marker == 0xFF:
            self._read_context = (layer_index, key_index)
            key_type = 1 if assignment.kind == AssignmentKind.COMBINATION else 0
            data = bytes([0, 0, key_type, assignment.subtype, 0, *encode_utf16be(assignment.label)])
            return make_response(Command.READ_KEY, data)
        if self._read_context != (layer_index, key_index):
            raise DeviceError("Mock read-key sequence did not start with a header")
        if marker == 0:
            bytes_value = bytes([0]) if assignment.kind == AssignmentKind.DISABLED else bytes(assignment.key_codes)
            return make_response(Command.READ_KEY, bytes([0, marker, *bytes_value]))
        return make_response(Command.READ_KEY, bytes([0, 0xFE]))

    def _write_key(self, payload: bytes) -> bytes:
        if not payload:
            raise DeviceError("Empty mock write-key payload")
        if payload[0] == 0xFF:
            if len(payload) < 6:
                raise DeviceError("Truncated mock write-key header")
            self._write_context = _WriteContext(
                layer_index=payload[1],
                key_index=payload[2],
                key_type=payload[3],
                subtype=payload[4],
                trigger_type=payload[5],
                label=decode_utf16be(payload[6:]),
                data=bytearray(),
            )
            return make_response(Command.WRITE_KEY, bytes([0]))
        if self._write_context is None:
            raise DeviceError("Mock write-key sequence did not start with a header")
        if payload[0] == 0xFE:
            context = self._write_context
            self._write_context = None
            kind = AssignmentKind.COMBINATION if context.key_type == 1 else AssignmentKind.KEYBOARD
            data = list(context.data)
            assignment = (
                KeyAssignment(key_index=context.key_index, label=context.label, kind=AssignmentKind.DISABLED)
                if data == [0]
                else KeyAssignment(
                    key_index=context.key_index,
                    label=context.label,
                    kind=kind,
                    key_codes=data if kind == AssignmentKind.COMBINATION else [data[0]],
                    subtype=context.subtype,
                    trigger_type=context.trigger_type,
                )
            )
            self._replace_layer(self._layer(context.layer_index).with_assignment(assignment))
            self._increment_write_count()
            return make_response(Command.WRITE_KEY, bytes([0]))
        self._write_context.data.extend(payload[1:])
        return make_response(Command.WRITE_KEY, bytes([0]))

    def _increment_write_count(self) -> None:
        self._write_count += 1
        if self.fail_after_writes is not None and self._write_count > self.fail_after_writes:
            raise DeviceError("Mock partial write failure")

    def _layer(self, index: int) -> Layer:
        for layer in self.layers:
            if layer.index == index:
                return layer
        raise DeviceError(f"Mock layer {index} does not exist")

    def _replace_layer(self, replacement: Layer) -> None:
        self.layers = [replacement if layer.index == replacement.index else layer for layer in self.layers]
