"""QML-facing application model; all configuration changes still use core safety APIs."""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_path
from PySide6.QtCore import Property, QObject, Signal, Slot

from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.models import (
    AssignmentKind,
    DeviceSnapshot,
    KeyAssignment,
    Layer,
    LinuxActionKind,
    LinuxBinding,
    SupportLevel,
    factory_jp1011_profile,
)
from vaydeer_studio.core.profiles import ProfileStore, load_profile, save_profile
from vaydeer_studio.core.safety import ApplyPreview, apply_prepared, prepare_apply
from vaydeer_studio.devices.capabilities import capability_for
from vaydeer_studio.devices.discovery import discover_linux_hidraw, select_command_interface
from vaydeer_studio.devices.layouts import layout_for_key_count
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.devices.transport import HidApiCommandTransport
from vaydeer_studio.protocol.client import VaydeerProtocol
from vaydeer_studio.service.bindings import BindingExecutor
from vaydeer_studio.service.daemon import default_socket_path
from vaydeer_studio.service.daemon import request as service_request

_KEY_CODES = {
    "CTRL": 17,
    "SHIFT": 16,
    "ALT": 18,
    "META": 91,
    "SPACE": 32,
    "ENTER": 13,
    "ESC": 27,
    "TAB": 9,
    "PLAY_PAUSE": 179,
    "VOLUME_UP": 175,
    "VOLUME_DOWN": 174,
    "VOLUME_MUTE": 173,
}
_KEY_CODES.update({chr(value): value for value in range(ord("A"), ord("Z") + 1)})
_KEY_CODES.update({f"F{value}": 111 + value for value in range(1, 25)})
_KEY_CODES.update({f"NUM_{value}": 96 + value for value in range(10)})


class StudioController(QObject):
    changed = Signal()
    selectedKeyChanged = Signal()
    statusChanged = Signal()
    previewChanged = Signal()
    testerChanged = Signal()

    def __init__(self, *, mock: bool) -> None:
        super().__init__()
        self.mock = mock
        self._transport: MockJP1011Transport | HidApiCommandTransport | None = None
        self._protocol: VaydeerProtocol | None = None
        self._status = "Mock JP-1011 ready" if mock else "No Vaydeer keypad detected"
        self._service_keepalive = "Mock active" if mock else "Service unavailable"
        if mock:
            self._transport = MockJP1011Transport()
            self._protocol = VaydeerProtocol(self._transport)
        else:
            self._connect_readonly()
            self._refresh_service_status()
        self.profile = factory_jp1011_profile()
        self._snapshot = self._load_snapshot()
        self._selected_key = 0
        self._selected_layer = 0
        self._preview: ApplyPreview | None = None
        self._tester_open = False
        self._tester_events: list[dict[str, str | int]] = []
        self.executor = BindingExecutor(mock_mode=mock)

    def _connect_readonly(self) -> None:
        """Open only the known vendor command interface for safe inspection."""

        try:
            interface = select_command_interface(discover_linux_hidraw())
            if interface is None:
                return
            self._transport = HidApiCommandTransport(interface.path)
            self._protocol = VaydeerProtocol(self._transport)
            self._status = "Vaydeer command interface connected (read-only inspection)"
        except Exception as error:
            self._status = f"Vaydeer detected but cannot open command interface: {error}"

    def _close_command_transport(self) -> None:
        if self._protocol is not None:
            with suppress(Exception):
                self._protocol.close()
        self._protocol = None
        self._transport = None

    def _refresh_service_status(self) -> None:
        if self.mock:
            self._service_keepalive = "Mock active"
            return
        try:
            response = service_request(default_socket_path(), {"method": "status"})
            keepalive = response.get("result", {}).get("keepalive", {})
            self._service_keepalive = str(keepalive.get("state", "Service unavailable"))
        except OSError:
            self._service_keepalive = "Service unavailable"

    def _sync_service_bindings(self) -> None:
        if self.mock:
            return
        try:
            service_request(
                default_socket_path(),
                {
                    "method": "set_bindings",
                    "bindings": [item.model_dump(mode="json") for item in self.profile.linux_bindings],
                },
            )
            self._refresh_service_status()
        except OSError:
            self._service_keepalive = "Service unavailable; bindings saved with the profile"

    def _load_snapshot(self) -> DeviceSnapshot:
        if self._protocol is not None:
            try:
                snapshot = self._protocol.read_snapshot()
                self.profile = self.profile.model_copy(update={"layers": snapshot.layers})
                return snapshot
            except Exception as error:
                self._status = f"Device inspection failed: {error}"
        return DeviceSnapshot(
            device=MockJP1011Transport().snapshot().device,
            layers=factory_jp1011_profile().layers,
        )

    @Property(dict, notify=changed)
    def device(self) -> dict[str, Any]:
        info = self._snapshot.device
        capability = capability_for(info)
        return {
            "model": "Vaydeer JP-1011" if info.key_count == 9 else capability.model,
            "keyCount": info.key_count,
            "firmware": info.firmware_version,
            "bootloader": info.bootloader_version,
            "activeLayer": self._selected_layer,
            "layerCount": len(self.profile.layers),
            "keepalive": self._service_keepalive,
            "usb": "Connected" if self.mock or self._protocol else "Disconnected",
            "permissions": "Granted (mock)" if self.mock else "Run diagnostics",
            "writable": capability.writable and self.mock,
            "warning": "" if capability.writable else capability.reason,
        }

    @Property(list, notify=changed)
    def keys(self) -> list[dict[str, Any]]:
        layer = self._current_layer()
        layout = layout_for_key_count(self._snapshot.device.key_count)
        return [
            {
                "index": item.index,
                "physicalLabel": item.label,
                "label": layer.assignment_for(item.index).display_name,
                "kind": layer.assignment_for(item.index).kind.value,
                "support": layer.assignment_for(item.index).support.value,
                "selected": item.index == self._selected_key,
            }
            for item in layout.keys
        ]

    @Property(list, notify=changed)
    def layers(self) -> list[dict[str, Any]]:
        return [
            {"index": layer.index, "name": layer.name, "selected": layer.index == self._selected_layer}
            for layer in self.profile.layers
        ]

    @Property(dict, notify=selectedKeyChanged)
    def selectedKey(self) -> dict[str, Any]:
        assignment = self._current_layer().assignment_for(self._selected_key)
        return {
            "index": assignment.key_index,
            "label": assignment.label,
            "kind": assignment.kind.value,
            "codes": "+".join(str(code) for code in assignment.key_codes),
            "support": assignment.support.value,
            "notes": assignment.notes,
        }

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def dirty(self) -> bool:
        return self.profile.layers != self._snapshot.layers

    @Property(str, notify=changed)
    def profileName(self) -> str:
        return self.profile.name

    @Property(list, notify=previewChanged)
    def previewLines(self) -> list[str]:
        return [] if self._preview is None else [item.describe() for item in self._preview.diff]

    @Property(str, notify=previewChanged)
    def backupPath(self) -> str:
        return "" if self._preview is None else str(self._preview.backup_path)

    @Property(list, notify=testerChanged)
    def testerEvents(self) -> list[dict[str, str | int]]:
        return self._tester_events

    @Property(list, notify=changed)
    def bindings(self) -> list[dict[str, Any]]:
        return [binding.model_dump(mode="json") for binding in self.profile.linux_bindings]

    @Property(list, notify=changed)
    def backups(self) -> list[str]:
        return [str(path) for path in BackupStore().list()[:8]]

    @Property(list, notify=changed)
    def savedProfiles(self) -> list[dict[str, str]]:
        return [{"id": item.id, "name": item.name} for item in ProfileStore().list()]

    @Property(int, notify=changed)
    def layoutColumns(self) -> int:
        return layout_for_key_count(self._snapshot.device.key_count).columns

    @Slot(int)
    def selectKey(self, index: int) -> None:
        self._selected_key = index
        self.selectedKeyChanged.emit()
        self.changed.emit()

    @Slot(int)
    def selectLayer(self, index: int) -> None:
        self._selected_layer = index
        self.changed.emit()
        self.selectedKeyChanged.emit()

    @Slot(str, str, str)
    def saveKey(self, category: str, label: str, code_text: str) -> None:
        try:
            kind, support = self._kind_from_category(category)
            codes = [] if kind == AssignmentKind.DISABLED else self._parse_codes(code_text)
            assignment = KeyAssignment(
                key_index=self._selected_key,
                label=label.strip(),
                kind=kind,
                key_codes=codes if support == SupportLevel.ON_DEVICE else [],
                payload=codes if support != SupportLevel.ON_DEVICE else [],
                support=support,
                notes=("Experimental: read-only on physical hardware." if support != SupportLevel.ON_DEVICE else ""),
            )
            layer = self._current_layer().with_assignment(assignment)
            self._replace_layer(layer)
            self._status = f"Key {self._selected_key + 1} updated in profile"
            self.changed.emit()
            self.selectedKeyChanged.emit()
            self.statusChanged.emit()
        except Exception as error:
            self._status = f"Could not update key: {error}"
            self.statusChanged.emit()

    @Slot()
    def discardChanges(self) -> None:
        self.profile = self.profile.model_copy(update={"layers": self._snapshot.layers})
        self._preview = None
        self._status = "Profile changes discarded"
        self.changed.emit()
        self.previewChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def readFromDevice(self) -> None:
        if self._protocol is None:
            self._status = "No device is available to read"
        else:
            try:
                self._snapshot = self._protocol.read_snapshot()
                self.profile = self.profile.model_copy(update={"layers": self._snapshot.layers})
                self._status = "Read current configuration from device"
            except Exception as error:
                self._status = f"Read failed: {error}"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def reconnectDevice(self) -> None:
        if self.mock:
            self.readFromDevice()
            return
        self._close_command_transport()
        self._connect_readonly()
        self._refresh_service_status()
        if self._protocol is None:
            self._status = "No Vaydeer command interface found after reconnect"
        else:
            try:
                self._snapshot = self._protocol.read_snapshot()
                self.profile = self.profile.model_copy(update={"layers": self._snapshot.layers})
                self._status = "Device reconnected and configuration refreshed"
            except Exception as error:
                self._status = f"Reconnect inspection failed: {error}"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def previewApply(self) -> None:
        if self._protocol is None:
            self._status = "No connected device is available"
        else:
            try:
                proposed = self.profile.to_snapshot(self._snapshot.device)
                self._preview = prepare_apply(self._protocol, proposed, BackupStore())
                self._status = "Diff prepared. Review it before applying."
                self.previewChanged.emit()
            except Exception as error:
                self._status = f"Cannot prepare apply: {error}"
        self.statusChanged.emit()

    @Slot()
    def restoreLatestBackup(self) -> None:
        if self._protocol is None:
            self._status = "No connected device is available"
        else:
            backups = BackupStore().list()
            if not backups:
                self._status = "No Vaydeer Studio backups are available"
            else:
                try:
                    self._preview = prepare_apply(self._protocol, BackupStore().load(backups[0]), BackupStore())
                    self._status = f"Backup staged from {backups[0]}; review the diff before applying."
                    self.previewChanged.emit()
                except Exception as error:
                    self._status = f"Could not stage backup restore: {error}"
        self.statusChanged.emit()

    @Slot()
    def applyPreview(self) -> None:
        if self._preview is None:
            self._status = "Create and review a diff first"
        elif not self.mock:
            self._status = (
                "Hardware writes require terminal confirmation: vaydeer-studio-cli apply-profile --confirm-real-write"
            )
        else:
            try:
                result = apply_prepared(self._protocol, self._preview, confirmed=True)  # type: ignore[arg-type]
                self._snapshot = result.verified
                self.profile = self.profile.model_copy(update={"layers": result.verified.layers})
                self._status = f"Mock write verified. Backup preserved at {result.preview.backup_path}"
                self._preview = None
                self.changed.emit()
                self.previewChanged.emit()
            except Exception as error:
                self._status = f"Apply failed: {error}"
        self.statusChanged.emit()

    @Slot(str, str, str)
    def addBinding(self, action: str, target: str, arguments: str) -> None:
        try:
            binding = LinuxBinding(
                key_index=self._selected_key,
                layer_index=self._selected_layer,
                action=LinuxActionKind(action),
                target=target.strip(),
                arguments=[item for item in arguments.split(" ") if item],
            )
            self.profile = self.profile.model_copy(update={"linux_bindings": [*self.profile.linux_bindings, binding]})
            self._sync_service_bindings()
            self._status = "Linux-side binding added"
            self.changed.emit()
            self.statusChanged.emit()
        except Exception as error:
            self._status = f"Could not add binding: {error}"
            self.statusChanged.emit()

    @Slot(int)
    def runBinding(self, index: int) -> None:
        if not 0 <= index < len(self.profile.linux_bindings):
            return
        if not self.mock:
            self._status = "Linux bindings run from vaydeer-studiod when a physical key event arrives"
            self.statusChanged.emit()
            return
        result = self.executor.execute(self.profile.linux_bindings[index])
        self._status = result.message if result.ok else f"Binding failed: {result.message}"
        self.statusChanged.emit()

    @Slot()
    def duplicateProfile(self) -> None:
        self.profile = self.profile.model_copy(
            update={"id": f"{self.profile.id}-copy", "name": f"{self.profile.name} copy"}
        )
        store = ProfileStore()
        store.save(self.profile)
        store.set_active(self.profile.id)
        self._sync_service_bindings()
        self._status = "Profile duplicated and saved to the local profile library"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot(str)
    def renameProfile(self, name: str) -> None:
        if name.strip():
            self.profile = self.profile.model_copy(update={"name": name.strip()})
            self.changed.emit()

    @Slot(str)
    def importProfile(self, source: str) -> None:
        try:
            profile = load_profile(Path(source).expanduser())
            if profile.key_count != self._snapshot.device.key_count:
                raise ValueError(
                    f"Profile expects {profile.key_count} keys; this keypad has {self._snapshot.device.key_count}"
                )
            self.profile = profile
            self._selected_layer = profile.layers[0].index if profile.layers else 0
            store = ProfileStore()
            store.save(profile)
            store.set_active(profile.id)
            self._sync_service_bindings()
            self._status = f"Imported profile {profile.name!r}"
            self.changed.emit()
            self.selectedKeyChanged.emit()
        except Exception as error:
            self._status = f"Could not import profile: {error}"
        self.statusChanged.emit()

    @Slot()
    def deleteProfile(self) -> None:
        store = ProfileStore()
        store.delete(self.profile.id)
        self.profile = factory_jp1011_profile().model_copy(update={"name": "Untitled profile"})
        self._selected_key = 0
        self._selected_layer = 0
        self._status = "Current profile cleared"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def saveProfile(self) -> None:
        store = ProfileStore()
        path = store.save(self.profile)
        store.set_active(self.profile.id)
        self._sync_service_bindings()
        self._status = f"Profile saved to {path}"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot(str)
    def loadSavedProfile(self, profile_id: str) -> None:
        try:
            profile = ProfileStore().load(profile_id)
            if profile.key_count != self._snapshot.device.key_count:
                raise ValueError(
                    f"Profile expects {profile.key_count} keys; this keypad has {self._snapshot.device.key_count}"
                )
            self.profile = profile
            self._selected_layer = profile.layers[0].index if profile.layers else 0
            ProfileStore().set_active(profile.id)
            self._sync_service_bindings()
            self._status = f"Loaded profile {profile.name!r}"
            self.changed.emit()
            self.selectedKeyChanged.emit()
        except Exception as error:
            self._status = f"Could not load profile: {error}"
            self.statusChanged.emit()

    @Slot()
    def exportProfile(self) -> None:
        root = user_data_path("Vaydeer Studio", "Vaydeer Studio") / "profiles"
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = root / f"{self.profile.name.lower().replace(' ', '-')}-{timestamp}.json"
        save_profile(self.profile, path)
        self._status = f"Profile exported to {path}"
        self.statusChanged.emit()

    @Slot(bool)
    def setTesterOpen(self, opened: bool) -> None:
        self._tester_open = opened
        if not opened:
            self._tester_events = []
        self.testerChanged.emit()

    @Slot(int)
    def simulateKey(self, key_index: int) -> None:
        if not isinstance(self._transport, MockJP1011Transport) or not self._tester_open:
            return
        for pressed in (True, False):
            raw = self._transport.queue_event(key_index, pressed, self._selected_layer)
            self._tester_events.insert(
                0,
                {
                    "timestamp": datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3],
                    "key": key_index + 1,
                    "event": "Press" if pressed else "Release",
                    "layer": self._selected_layer,
                    "raw": raw[:6].hex(" "),
                },
            )
        self._tester_events = self._tester_events[:30]
        self.testerChanged.emit()

    @Slot()
    def exportDiagnostics(self) -> None:
        root = user_data_path("Vaydeer Studio", "Vaydeer Studio") / "diagnostics"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"diagnostics-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        payload = {
            "device": self.device,
            "interfaces": [
                item.__dict__ | {"report_descriptor": item.report_descriptor.hex()} for item in discover_linux_hidraw()
            ],
            "status": self._status,
        }
        path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
        self._status = f"Sanitized diagnostics exported to {path}"
        self.statusChanged.emit()

    def _current_layer(self) -> Layer:
        for layer in self.profile.layers:
            if layer.index == self._selected_layer:
                return layer
        return self.profile.layers[0]

    def _replace_layer(self, replacement: Layer) -> None:
        layers = [replacement if layer.index == replacement.index else layer for layer in self.profile.layers]
        self.profile = self.profile.model_copy(update={"layers": layers})

    @staticmethod
    def _parse_codes(text: str) -> list[int]:
        values: list[int] = []
        for token in text.replace("+", " ").replace(",", " ").split():
            normalized = token.strip().upper()
            if normalized in _KEY_CODES:
                values.append(_KEY_CODES[normalized])
            else:
                values.append(int(normalized, 0))
        if not values:
            raise ValueError("Enter a key code or key name")
        return values

    @staticmethod
    def _kind_from_category(category: str) -> tuple[AssignmentKind, SupportLevel]:
        stable = {
            "Keyboard key": AssignmentKind.KEYBOARD,
            "Modifier": AssignmentKind.MODIFIER,
            "Key combination": AssignmentKind.COMBINATION,
            "Media": AssignmentKind.MEDIA,
            "System control": AssignmentKind.SYSTEM,
            "Disabled": AssignmentKind.DISABLED,
        }
        if category in stable:
            return stable[category], SupportLevel.ON_DEVICE
        experimental = {
            "Mouse": AssignmentKind.MOUSE,
            "Macro": AssignmentKind.MACRO,
            "Text": AssignmentKind.TEXT,
            "Layer action": AssignmentKind.VAYDEER,
            "Vaydeer action": AssignmentKind.VAYDEER,
            "Linux host action": AssignmentKind.LINUX_HOST,
        }
        return experimental.get(category, AssignmentKind.SPECIAL), SupportLevel.EXPERIMENTAL
