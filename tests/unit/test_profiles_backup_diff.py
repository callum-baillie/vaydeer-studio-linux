from __future__ import annotations

from pathlib import Path

from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.diff import format_diff, snapshot_diff
from vaydeer_studio.core.models import (
    AssignmentKind,
    DeviceInfo,
    KeyAssignment,
    Layer,
    MacroEventKind,
    MacroStep,
    Profile,
    ProfileTargetPlatform,
    factory_jp1011_profile,
)
from vaydeer_studio.core.profiles import ProfileStore, load_profile, save_profile, validate_for_device
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.protocol.client import VaydeerProtocol


def test_profile_json_and_yaml_are_portable(tmp_path: Path) -> None:
    profile = factory_jp1011_profile().model_copy(
        update={"target_platform": ProfileTargetPlatform.MACOS, "target_application": "Adobe Illustrator"}
    )
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
    active_profile = store.load_active()
    assert active_profile is not None
    assert active_profile.id == profile.id
    store.delete(profile.id)
    assert store.list() == []
    assert store.load_active() is None


def test_profile_snapshot_materializes_missing_keys_as_disabled() -> None:
    device = DeviceInfo(
        device_type=1,
        subtype=4,
        firmware=(1, 0, 0),
        bootloader=(0, 1, 0),
        active_layer=0,
        layer_count=1,
        max_layers=1,
    )
    profile = Profile(key_count=4, layers=[Layer(index=0, assignments=[])])
    assert [item.kind for item in profile.to_snapshot(device).layer(0).assignments] == [
        AssignmentKind.DISABLED,
        AssignmentKind.DISABLED,
        AssignmentKind.DISABLED,
        AssignmentKind.DISABLED,
    ]


def test_profile_keeps_readable_key_values_and_typed_macro_steps() -> None:
    shortcut = KeyAssignment(key_index=0, kind=AssignmentKind.COMBINATION, key_codes=[17, 80])
    macro = KeyAssignment(
        key_index=1,
        kind=AssignmentKind.MACRO,
        macro_steps=[
            MacroStep(event=MacroEventKind.PRESS, key_code=17),
            MacroStep(event=MacroEventKind.PRESS, key_code=67),
            MacroStep(event=MacroEventKind.RELEASE, key_code=67),
            MacroStep(event=MacroEventKind.RELEASE, key_code=17),
            MacroStep(event=MacroEventKind.DELAY, delay_ms=120),
        ],
    )

    assert shortcut.display_name == "Ctrl + P"
    assert [step.display_name for step in macro.macro_steps][-1] == "Wait 120 ms"
