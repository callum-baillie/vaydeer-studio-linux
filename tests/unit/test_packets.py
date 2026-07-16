from __future__ import annotations

import pytest

from vaydeer_studio.core.errors import ForbiddenCommandError, ProtocolError
from vaydeer_studio.protocol.packets import Command, build_request, make_response, parse_response, xor_checksum


def test_xor_checksum_matches_documented_ping() -> None:
    assert xor_checksum([0xFD, 0x00]) == 0xFD


def test_build_request_pads_documented_device_info_packet() -> None:
    frame = build_request(Command.READ_DEVICE_INFO)
    assert frame[:4] == bytes([0x00, 0x60, 0x00, 0x60])
    assert len(frame) == 65


def test_response_validation_and_report_id_variant() -> None:
    response = make_response(Command.READ_LAYER_INFO, bytes([0, 0, 1, 6]))
    assert parse_response(response, expected_command=Command.READ_LAYER_INFO) == bytes([0, 0, 1, 6])
    assert parse_response(b"\x00" + response, expected_command=Command.READ_LAYER_INFO) == bytes([0, 0, 1, 6])


def test_response_validation_rejects_checksum_and_wrong_command() -> None:
    response = make_response(Command.READ_LAYER_INFO, bytes([0, 0, 1, 6]))
    with pytest.raises(ProtocolError, match="Invalid response"):
        parse_response(response[:-1] + b"\x00", expected_command=Command.READ_LAYER_INFO)
    with pytest.raises(ProtocolError, match="Invalid response"):
        parse_response(response, expected_command=Command.READ_DEVICE_INFO)


@pytest.mark.parametrize("command", [0xFC, 0x00, 0x68, 0xFE])
def test_firmware_and_unknown_commands_cannot_be_emitted(command: int) -> None:
    with pytest.raises(ForbiddenCommandError):
        build_request(command)
