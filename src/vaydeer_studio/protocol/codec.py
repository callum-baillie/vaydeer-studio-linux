"""Known key-assignment serialization, deserialization, and packet planning."""

from __future__ import annotations

from dataclasses import dataclass

from vaydeer_studio.core.errors import ProtocolError, UnsupportedActionError
from vaydeer_studio.core.models import AssignmentKind, KeyAssignment, SupportLevel

from .packets import Command, build_request

START_MARKER = 0xFF
END_MARKER = 0xFE
MAX_KEY_DATA_CHUNK = 60


@dataclass(frozen=True)
class DecodedKeyHeader:
    key_type: int
    subtype: int
    encoding: int
    label: str


def encode_utf16be(value: str) -> bytes:
    try:
        return value.encode("utf-16-be")
    except UnicodeEncodeError as error:
        raise ProtocolError(f"Could not encode key label as UTF-16BE: {error}") from error


def decode_utf16be(value: bytes) -> str:
    usable = value[: len(value) - (len(value) % 2)]
    if not usable:
        return ""
    try:
        return usable.decode("utf-16-be").rstrip("\x00")
    except UnicodeDecodeError:
        return usable.decode("utf-16-be", errors="replace").rstrip("\x00")


def assignment_type(assignment: KeyAssignment) -> int:
    if assignment.kind == AssignmentKind.DISABLED:
        return 0
    if assignment.kind in {
        AssignmentKind.KEYBOARD,
        AssignmentKind.MODIFIER,
        AssignmentKind.MEDIA,
        AssignmentKind.SYSTEM,
    }:
        return 0
    if assignment.kind == AssignmentKind.COMBINATION:
        return 1
    raise UnsupportedActionError(
        f"{assignment.kind.value} has no validated on-device payload format and cannot be sent"
    )


def encode_assignment_frames(layer_index: int, assignment: KeyAssignment) -> list[bytes]:
    """Produce the documented 0x61 header/data/end sequence without writing it."""

    if not assignment.transmit_supported:
        raise UnsupportedActionError(
            f"{assignment.kind.value} is {assignment.support.value} and cannot be stored on a keypad"
        )
    key_type = assignment_type(assignment)
    data = bytes([0]) if assignment.kind == AssignmentKind.DISABLED else bytes(assignment.key_codes)
    header = bytes(
        [
            START_MARKER,
            layer_index,
            assignment.key_index,
            key_type,
            assignment.subtype,
            assignment.trigger_type,
        ]
    ) + encode_utf16be(assignment.label)
    frames = [build_request(Command.WRITE_KEY, header)]
    for sequence, offset in enumerate(range(0, len(data), MAX_KEY_DATA_CHUNK)):
        frames.append(
            build_request(Command.WRITE_KEY, bytes([sequence % 16]) + data[offset : offset + MAX_KEY_DATA_CHUNK])
        )
    frames.append(build_request(Command.WRITE_KEY, bytes([END_MARKER])))
    return frames


def encode_layer_name_frame(layer_index: int, maximum_layer_index: int, name: str) -> bytes:
    payload = bytes([layer_index, maximum_layer_index]) + encode_utf16be(name)
    return build_request(Command.WRITE_LAYER_NAME, payload)


def encode_commit_frame(layer_index: int, maximum_layer_index: int) -> bytes:
    return build_request(Command.COMMIT_LAYER, bytes([layer_index, maximum_layer_index]))


def decode_key_header(value: bytes) -> DecodedKeyHeader:
    """Decode the observed 0x62 header after its status byte has been removed."""

    if len(value) < 4:
        raise ProtocolError("Read-key header was too short")
    # Observed format is [unknown, keyType, subType, encoding, UTF-16BE label...].
    return DecodedKeyHeader(key_type=value[1], subtype=value[2], encoding=value[3], label=decode_utf16be(value[4:]))


def decode_assignment(key_index: int, header: DecodedKeyHeader, data: bytes) -> KeyAssignment:
    """Map only understood key types to stable models; preserve others as experimental."""

    if header.key_type == 0:
        if data == bytes([0]) or not data:
            return KeyAssignment(key_index=key_index, label=header.label, kind=AssignmentKind.DISABLED)
        kind = AssignmentKind.MEDIA if data[0] in range(0xA6, 0xB8) else AssignmentKind.KEYBOARD
        return KeyAssignment(
            key_index=key_index,
            label=header.label,
            kind=kind,
            key_codes=[data[0]],
            subtype=header.subtype,
        )
    if header.key_type == 1:
        if len(data) < 2:
            return KeyAssignment(
                key_index=key_index,
                label=header.label,
                kind=AssignmentKind.SPECIAL,
                payload=list(data),
                subtype=header.subtype,
                support=SupportLevel.EXPERIMENTAL,
                notes="Truncated combination payload; retained without guessing a replacement mapping.",
            )
        return KeyAssignment(
            key_index=key_index,
            label=header.label,
            kind=AssignmentKind.COMBINATION,
            key_codes=list(data),
            subtype=header.subtype,
        )
    type_map = {
        2: AssignmentKind.TEXT,
        3: AssignmentKind.HOST_TRIGGER,
        4: AssignmentKind.MOUSE,
        5: AssignmentKind.MACRO,
        6: AssignmentKind.VAYDEER,
        7: AssignmentKind.SPECIAL,
    }
    return KeyAssignment(
        key_index=key_index,
        label=header.label,
        kind=type_map.get(header.key_type, AssignmentKind.SPECIAL),
        payload=list(data),
        subtype=header.subtype,
        support=SupportLevel.EXPERIMENTAL,
        notes="Payload was read from device but is not transmitted by Vaydeer Studio.",
    )
