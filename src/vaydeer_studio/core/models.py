"""Versioned configuration models shared by the CLI, daemon, and QML UI."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vaydeer_studio.core.keycodes import display_key_codes


class AssignmentKind(StrEnum):
    """All assignment categories observed in the vendor application."""

    KEYBOARD = "keyboard"
    MODIFIER = "modifier"
    COMBINATION = "combination"
    MEDIA = "media"
    SYSTEM = "system"
    DISABLED = "disabled"
    TEXT = "text"
    HOST_TRIGGER = "host_trigger"
    MOUSE = "mouse"
    MACRO = "macro"
    VAYDEER = "vaydeer"
    SPECIAL = "special"
    LINUX_HOST = "linux_host"


class SupportLevel(StrEnum):
    ON_DEVICE = "on_device"
    SERVICE = "service"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class LinuxActionKind(StrEnum):
    APPLICATION = "application"
    URL = "url"
    FILE = "file"
    DIRECTORY = "directory"
    COMMAND = "command"
    NOTIFICATION = "notification"
    SCRIPT = "script"
    TEXT = "text"


class TriggerKind(StrEnum):
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    DOUBLE_TAP = "double_tap"
    CHORD = "chord"


class ProfileTargetPlatform(StrEnum):
    """Operating system a portable profile is intended to run on."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class MacroEventKind(StrEnum):
    """Portable macro events retained in profiles until the device codec is known."""

    PRESS = "press"
    RELEASE = "release"
    DELAY = "delay"


class MacroStep(BaseModel):
    """A typed, non-transmittable macro step for service and profile workflows."""

    event: MacroEventKind
    key_code: int | None = Field(default=None, ge=0, le=255)
    delay_ms: int | None = Field(default=None, ge=0, le=60_000)

    @model_validator(mode="after")
    def validate_event_shape(self) -> MacroStep:
        if self.event == MacroEventKind.DELAY:
            if self.delay_ms is None:
                raise ValueError("a delay macro event needs delay_ms")
            if self.key_code is not None:
                raise ValueError("a delay macro event cannot contain a key code")
        elif self.key_code is None:
            raise ValueError("a key macro event needs key_code")
        return self

    @property
    def display_name(self) -> str:
        if self.event == MacroEventKind.DELAY:
            return f"Wait {self.delay_ms} ms"
        return f"{self.event.value.title()} {display_key_codes([self.key_code or 0])}"


class DeviceInfo(BaseModel):
    """Stable result of command 0x60."""

    model_config = ConfigDict(frozen=True)

    vendor_id: int = 0x0483
    product_id: int = 0x5752
    device_type: int = Field(ge=0, le=255)
    subtype: int = Field(ge=0, le=255)
    firmware: tuple[int, int, int]
    bootloader: tuple[int, int, int]
    active_layer: int = Field(ge=0, le=255)
    layer_count: int = Field(ge=0, le=255)
    max_layers: int = Field(ge=0, le=255)
    product_name: str = "Vaydeer keypad"

    @property
    def key_count(self) -> int:
        return self.subtype

    @property
    def firmware_version(self) -> str:
        return ".".join(str(value) for value in self.firmware)

    @property
    def bootloader_version(self) -> str:
        return ".".join(str(value) for value in self.bootloader)


class LayerInfo(BaseModel):
    """Stable result of command 0x63."""

    model_config = ConfigDict(frozen=True)

    active_layer: int = Field(ge=0, le=255)
    layer_count: int = Field(ge=0, le=255)
    max_layers: int = Field(ge=0, le=255)


class KeyAssignment(BaseModel):
    """One physical key assignment, keeping uncertain payloads non-transmittable."""

    key_index: int = Field(ge=0, le=255)
    # 27 UTF-16 code units plus the observed six-byte header fit one 0x61 request.
    label: str = Field(default="", max_length=27)
    kind: AssignmentKind = AssignmentKind.DISABLED
    key_codes: list[int] = Field(default_factory=list)
    subtype: int = Field(default=0xFF, ge=0, le=255)
    trigger_type: int = Field(default=0, ge=0, le=255)
    payload: list[int] = Field(default_factory=list)
    action_data: str = Field(default="", max_length=1024)
    macro_steps: list[MacroStep] = Field(default_factory=list)
    support: SupportLevel = SupportLevel.ON_DEVICE
    notes: str = ""

    @model_validator(mode="after")
    def validate_shape(self) -> KeyAssignment:
        values = self.key_codes or self.payload
        if any(value < 0 or value > 255 for value in values):
            raise ValueError("assignment bytes must fit in one byte")
        if self.kind == AssignmentKind.DISABLED and (self.key_codes or self.payload):
            raise ValueError("disabled assignments cannot contain payload bytes")
        if self.kind == AssignmentKind.DISABLED and (self.action_data or self.macro_steps):
            raise ValueError("disabled assignments cannot contain action data")
        if self.macro_steps and self.kind != AssignmentKind.MACRO:
            raise ValueError("only macro assignments can contain macro steps")
        if self.kind == AssignmentKind.COMBINATION and len(self.key_codes) < 2:
            raise ValueError("a key combination needs at least two key codes")
        single_key_kinds = {
            AssignmentKind.KEYBOARD,
            AssignmentKind.MODIFIER,
            AssignmentKind.MEDIA,
            AssignmentKind.SYSTEM,
        }
        if self.kind in single_key_kinds and len(self.key_codes) != 1:
            raise ValueError(f"{self.kind.value} assignments need exactly one key code")
        return self

    @property
    def transmit_supported(self) -> bool:
        return (
            self.kind
            in {
                AssignmentKind.KEYBOARD,
                AssignmentKind.MODIFIER,
                AssignmentKind.COMBINATION,
                AssignmentKind.MEDIA,
                AssignmentKind.SYSTEM,
                AssignmentKind.DISABLED,
            }
            and self.support == SupportLevel.ON_DEVICE
        )

    @property
    def display_name(self) -> str:
        if self.label:
            return self.label
        if self.kind == AssignmentKind.DISABLED:
            return "Disabled"
        if self.key_codes:
            return display_key_codes(self.key_codes)
        if self.kind == AssignmentKind.MACRO and self.macro_steps:
            return "Macro"
        if self.action_data:
            return self.action_data.splitlines()[0][:24]
        return self.kind.value.replace("_", " ").title()


class Layer(BaseModel):
    """On-device layer with vendor indexes preserved exactly."""

    index: int = Field(ge=0, le=255)
    name: str = Field(default="Layer", max_length=28)
    assignments: list[KeyAssignment] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_key_indexes(self) -> Layer:
        indexes = [assignment.key_index for assignment in self.assignments]
        if len(indexes) != len(set(indexes)):
            raise ValueError("a layer cannot contain duplicate key indexes")
        return self

    def assignment_for(self, key_index: int) -> KeyAssignment:
        for assignment in self.assignments:
            if assignment.key_index == key_index:
                return assignment
        return KeyAssignment(key_index=key_index)

    def with_assignment(self, assignment: KeyAssignment) -> Layer:
        remaining = [item for item in self.assignments if item.key_index != assignment.key_index]
        return self.model_copy(
            update={"assignments": sorted([*remaining, assignment], key=lambda item: item.key_index)}
        )


class DeviceSnapshot(BaseModel):
    """Open, versioned representation used for backups and verification."""

    schema_version: int = 1
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    device: DeviceInfo
    layers: list[Layer]

    @model_validator(mode="after")
    def valid_snapshot(self) -> DeviceSnapshot:
        if len(self.layers) > self.device.max_layers:
            raise ValueError("snapshot has more layers than the device permits")
        if any(layer.index >= self.device.max_layers for layer in self.layers):
            raise ValueError("layer index exceeds device maximum")
        return self

    def layer(self, layer_index: int) -> Layer:
        for layer in self.layers:
            if layer.index == layer_index:
                return layer
        raise KeyError(f"layer {layer_index} is not present")

    def with_layer(self, layer: Layer) -> DeviceSnapshot:
        remaining = [item for item in self.layers if item.index != layer.index]
        return self.model_copy(update={"layers": sorted([*remaining, layer], key=lambda item: item.index)})


class LinuxBinding(BaseModel):
    """A service-managed action triggered from the vendor async event channel."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    key_index: int = Field(ge=0, le=255)
    layer_index: int = Field(default=0, ge=0, le=255)
    trigger: TriggerKind = TriggerKind.PRESS
    action: LinuxActionKind
    target: str = ""
    arguments: list[str] = Field(default_factory=list)
    allow_shell: bool = False
    active_window_pattern: str | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def validate_command(self) -> LinuxBinding:
        if self.action == LinuxActionKind.COMMAND and not self.arguments and not self.target:
            raise ValueError("a command binding needs a program or arguments")
        if (
            self.action
            in {
                LinuxActionKind.URL,
                LinuxActionKind.FILE,
                LinuxActionKind.DIRECTORY,
                LinuxActionKind.APPLICATION,
                LinuxActionKind.SCRIPT,
            }
            and not self.target
        ):
            raise ValueError(f"{self.action.value} bindings need a target")
        return self


class Profile(BaseModel):
    """Portable profile schema for device mappings and Linux-side bindings."""

    schema_version: Annotated[int, Field(ge=1)] = 2
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(default="Untitled profile", min_length=1, max_length=64)
    device_model: str = "JP-1011"
    key_count: int = Field(default=9, ge=1, le=255)
    target_platform: ProfileTargetPlatform = ProfileTargetPlatform.LINUX
    target_application: str | None = Field(default=None, max_length=64)
    layers: list[Layer] = Field(default_factory=list)
    linux_bindings: list[LinuxBinding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_profile(self) -> Profile:
        indexes = [layer.index for layer in self.layers]
        if len(indexes) != len(set(indexes)):
            raise ValueError("a profile cannot contain duplicate layer indexes")
        for layer in self.layers:
            if any(item.key_index >= self.key_count for item in layer.assignments):
                raise ValueError("profile assignment exceeds its declared key count")
        return self

    def to_snapshot(self, device: DeviceInfo) -> DeviceSnapshot:
        # The writer sends every physical key. Materialize omitted draft entries as
        # explicit disabled mappings so preview, write, and read-back agree.
        layers = [
            layer.model_copy(update={"assignments": [layer.assignment_for(key) for key in range(device.key_count)]})
            for layer in self.layers
        ]
        return DeviceSnapshot(device=device, layers=layers)


def factory_jp1011_profile() -> Profile:
    """A useful mock profile matching the observed factory numpad layout."""

    codes = [103, 104, 105, 100, 101, 102, 97, 98, 99]
    labels = ["Num 7", "Num 8", "Num 9", "Num 4", "Num 5", "Num 6", "Num 1", "Num 2", "Num 3"]
    assignments = [
        KeyAssignment(key_index=index, label=labels[index], kind=AssignmentKind.KEYBOARD, key_codes=[code])
        for index, code in enumerate(codes)
    ]
    return Profile(name="JP-1011 Factory", layers=[Layer(index=0, name="Default", assignments=assignments)])


def jsonable(model: BaseModel) -> dict[str, Any]:
    """Return a JSON-safe model representation for IPC and QML."""

    return model.model_dump(mode="json")
