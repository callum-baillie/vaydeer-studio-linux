from __future__ import annotations

from pathlib import Path

from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.diff import format_diff, snapshot_diff
from vaydeer_studio.core.models import AssignmentKind, KeyAssignment, factory_jp1011_profile
from vaydeer_studio.core.profiles import ProfileStore, load_profile, save_profile, validate_for_device
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.protocol.client import VaydeerProtocol


def test_profile_json_and_yaml_are_portable(tmp_path: Path) -> None:
    profile = factory_jp1011_profile()
    for suffix in (".json", ".yaml"):
        path = tmp_path / f"profile{suffix}"
        save_profile(profile, path)
        assert load_profile(path).model_dump(mode="json") == profile.model_dump(mode="json")


def test_backup_format_and_diff(tmp_path: Path) -> None:
    protocol = VaydeerProtocol(MockJP1011Transport())
    before = protocol.read_snapshot()
    after = before.with_layer(
        before.layer(0).with_assignment(
            KeyAssignment(key_index=0, label="A", kind=AssignmentKind.KEYBOARD, key_codes=[65])
        )
    )
    changes = snapshot_diff(before, after)
    assert "Layer 0, key 1: Num 7 -> A" in format_diff(changes)
    store = BackupStore(tmp_path)
    path = store.create(before)
    assert store.load(path).model_dump(mode="json") == before.model_dump(mode="json")


def test_profile_device_validation_identifies_mismatch() -> None:
    profile = factory_jp1011_profile().model_copy(update={"key_count": 4})
    issues = validate_for_device(profile, key_count=9, model="JP-1011")
    assert issues == ["Profile expects 4 keys; device reports 9"]


def test_profile_store_round_trip_and_delete(tmp_path: Path) -> None:
    profile = factory_jp1011_profile()
    store = ProfileStore(tmp_path)
    path = store.save(profile)
    assert path.exists()
    assert [item.id for item in store.list()] == [profile.id]
    assert store.load(profile.id).name == profile.name
    store.set_active(profile.id)
    assert store.load_active() is not None
    assert store.load_active().id == profile.id  # type: ignore[union-attr]
    store.delete(profile.id)
    assert store.list() == []
    assert store.load_active() is None
