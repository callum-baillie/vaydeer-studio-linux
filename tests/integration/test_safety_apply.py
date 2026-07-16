from __future__ import annotations

from pathlib import Path

import pytest

from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.errors import PartialWriteError, SafetyConfirmationRequired
from vaydeer_studio.core.models import AssignmentKind, KeyAssignment
from vaydeer_studio.core.safety import apply_prepared, prepare_apply
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.protocol.client import VaydeerProtocol


def proposed_change(protocol: VaydeerProtocol):
    current = protocol.read_snapshot()
    layer = current.layer(0).with_assignment(
        KeyAssignment(key_index=0, label="A", kind=AssignmentKind.KEYBOARD, key_codes=[65])
    )
    return current.with_layer(layer)


def test_apply_creates_timestamped_backup_and_verifies_readback(tmp_path: Path) -> None:
    protocol = VaydeerProtocol(MockJP1011Transport())
    preview = prepare_apply(protocol, proposed_change(protocol), BackupStore(tmp_path))
    assert preview.backup_path.exists()
    assert preview.diff
    result = apply_prepared(protocol, preview, confirmed=True)
    assert result.verified.layer(0).assignment_for(0).label == "A"


def test_apply_requires_confirmation_after_diff_and_backup(tmp_path: Path) -> None:
    protocol = VaydeerProtocol(MockJP1011Transport())
    preview = prepare_apply(protocol, proposed_change(protocol), BackupStore(tmp_path))
    with pytest.raises(SafetyConfirmationRequired):
        apply_prepared(protocol, preview, confirmed=False)
    assert protocol.read_key_assignment(0, 0).label == "Num 7"


def test_partial_write_reports_preserved_backup(tmp_path: Path) -> None:
    transport = MockJP1011Transport()
    transport.fail_after_writes = 0
    protocol = VaydeerProtocol(transport)
    preview = prepare_apply(protocol, proposed_change(protocol), BackupStore(tmp_path))
    with pytest.raises(PartialWriteError, match="Backup remains"):
        apply_prepared(protocol, preview, confirmed=True)
    assert preview.backup_path.exists()
