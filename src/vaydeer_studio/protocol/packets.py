"""Packet framing and command allowlisting for the vendor HID channel."""

from __future__ import annotations

from enum import IntEnum

from vaydeer_studio.core.errors import ForbiddenCommandError, ProtocolError

REPORT_ID = 0x00
HID_WRITE_SIZE = 65
FORBIDDEN_FIRMWARE_COMMAND = 0xFC


class Command(IntEnum):
    READ_DEVICE_INFO = 0x60
    WRITE_KEY = 0x61
    READ_KEY = 0x62
    READ_LAYER_INFO = 0x63
    CHANGE_ACTIVE_LAYER = 0x64
    WRITE_LAYER_NAME = 0x65
    COMMIT_LAYER = 0x66
    READ_LAYER_NAME = 0x67
    INITIALIZE = 0xFD


_PERMITTED_COMMANDS = frozenset(int(command) for command in Command)


def xor_checksum(data: bytes | bytearray | list[int]) -> int:
    result = 0
    for value in data:
        if not 0 <= value <= 0xFF:
            raise ProtocolError(f"checksum input is outside byte range: {value!r}")
        result ^= value
    return result


def assert_permitted_command(command: int | Command) -> int:
    value = int(command)
    if value == FORBIDDEN_FIRMWARE_COMMAND:
        raise ForbiddenCommandError("Firmware command 0xFC is permanently disabled in Vaydeer Studio")
    if value not in _PERMITTED_COMMANDS:
        raise ForbiddenCommandError(f"Command 0x{value:02X} is not in Vaydeer Studio's allowlist")
    return value


def build_request(command: int | Command, payload: bytes | bytearray | list[int] = b"", *, pad: bool = True) -> bytes:
    """Build a report-ID-prefixed request and reject unsafe commands before I/O."""

    command_value = assert_permitted_command(command)
    raw_payload = bytes(payload)
    if len(raw_payload) > 61:
        raise ProtocolError(f"Request payload is too large for the 64-byte HID report: {len(raw_payload)}")
    body = bytes([command_value, len(raw_payload)]) + raw_payload
    frame = bytes([REPORT_ID]) + body + bytes([xor_checksum(body)])
    if not pad:
        return frame
    return frame + bytes(HID_WRITE_SIZE - len(frame))


def parse_response(response: bytes | bytearray | list[int], *, expected_command: int | Command | None = None) -> bytes:
    """Validate one response and return its data field including the status byte."""

    raw = bytes(response)
    candidates = [raw]
    if raw[:1] == bytes([REPORT_ID]):
        candidates.append(raw[1:])
    for candidate in candidates:
        try:
            if len(candidate) < 3:
                raise ProtocolError("Response is shorter than command, length, and checksum")
            command = candidate[0]
            length = candidate[1]
            meaningful_length = length + 3
            if len(candidate) < meaningful_length:
                raise ProtocolError(
                    f"Response length declares {length} data bytes but only {len(candidate)} bytes arrived"
                )
            meaningful = candidate[:meaningful_length]
            if xor_checksum(meaningful[:-1]) != meaningful[-1]:
                raise ProtocolError("Response checksum does not match")
            if expected_command is not None and command != int(expected_command):
                raise ProtocolError(
                    f"Response command 0x{command:02X} did not match request 0x{int(expected_command):02X}"
                )
            return meaningful[2:-1]
        except ProtocolError:
            continue
    raise ProtocolError("Invalid response frame")


def make_response(command: int | Command, data: bytes | bytearray | list[int]) -> bytes:
    """Build a non-padded response frame for deterministic mock fixtures."""

    value = int(command)
    raw_data = bytes(data)
    body = bytes([value, len(raw_data)]) + raw_data
    return body + bytes([xor_checksum(body)])
