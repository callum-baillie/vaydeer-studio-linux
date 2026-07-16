from __future__ import annotations

from vaydeer_studio.core.models import AssignmentKind, KeyAssignment, SupportLevel
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.protocol.client import VaydeerProtocol
from vaydeer_studio.protocol.codec import DecodedKeyHeader, decode_assignment, encode_assignment_frames


def test_reads_jp1011_device_layers_names_and_assignments() -> None:
    protocol = VaydeerProtocol(MockJP1011Transport())
    info = protocol.read_device_info()
    assert (info.key_count, info.firmware, info.bootloader) == (9, (1, 0, 2), (0, 2, 1))
    assert protocol.read_layer_info().max_layers == 6
    assert protocol.read_layer_name(0) == "0"
    assignment = protocol.read_key_assignment(0, 0)
    assert assignment.label == "Num 7"
    assert assignment.key_codes == [103]


def test_key_serialization_and_deserialization_round_trip() -> None:
    assignment = KeyAssignment(
        key_index=3,
        label="Copy",
        kind=AssignmentKind.COMBINATION,
        key_codes=[17, 67],
    )
    frames = encode_assignment_frames(0, assignment)
    assert frames[0][1] == 0x61
    assert frames[0][3:9] == bytes([0xFF, 0, 3, 1, 0xFF, 0])
    assert frames[-1][:5] == bytes([0, 0x61, 1, 0xFE, 0x9E])
    decoded = decode_assignment(3, DecodedKeyHeader(1, 0xFF, 0, "Copy"), bytes([17, 67]))
    assert decoded.kind == AssignmentKind.COMBINATION
    assert decoded.key_codes == [17, 67]


def test_unknown_read_assignment_is_preserved_as_experimental() -> None:
    assignment = decode_assignment(1, DecodedKeyHeader(5, 2, 0, "Macro"), bytes([65, 0, 10, 0]))
    assert assignment.kind == AssignmentKind.MACRO
    assert assignment.support == SupportLevel.EXPERIMENTAL
    assert not assignment.transmit_supported


def test_truncated_combination_is_not_replaced_with_guessed_codes() -> None:
    assignment = decode_assignment(1, DecodedKeyHeader(1, 0xFF, 0, "Partial"), bytes([17]))
    assert assignment.kind == AssignmentKind.SPECIAL
    assert assignment.payload == [17]
    assert assignment.support == SupportLevel.EXPERIMENTAL


def test_write_then_read_back_key_configuration() -> None:
    protocol = VaydeerProtocol(MockJP1011Transport())
    assignment = KeyAssignment(key_index=4, label="F13", kind=AssignmentKind.KEYBOARD, key_codes=[124])
    protocol.write_key_assignment(0, assignment)
    assert protocol.read_key_assignment(0, 4).model_dump() == assignment.model_dump()
