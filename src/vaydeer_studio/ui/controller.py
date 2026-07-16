"""QML-facing application model; all configuration changes still use core safety APIs."""

from __future__ import annotations

import json
import logging
import subprocess
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_path
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

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
from vaydeer_studio.devices.diagnostics import collect_diagnostics, render_report
from vaydeer_studio.devices.discovery import discover_linux_hidraw, select_command_interface
from vaydeer_studio.devices.layouts import layout_for_key_count
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.devices.transport import HidrawCommandTransport, open_command_transport
from vaydeer_studio.protocol.client import VaydeerProtocol
from vaydeer_studio.service.bindings import BindingExecutor
from vaydeer_studio.service.daemon import default_socket_path
from vaydeer_studio.service.daemon import request as service_request

LOGGER = logging.getLogger(__name__)
_STARTUP_RETRY_DELAYS_MS = (250, 500, 1_000, 1_500, 2_000)

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
        self._transport: MockJP1011Transport | HidrawCommandTransport | None = None
        self._protocol: VaydeerProtocol | None = None
        self.profile = factory_jp1011_profile()
        self._snapshot = DeviceSnapshot(
            device=MockJP1011Transport().snapshot().device,
            layers=self.profile.layers,
        )
        self._connection: dict[str, str | bool] = {
            "state": "starting",
            "title": "Checking for a Vaydeer keypad",
            "message": "Inspecting Linux HID interfaces.",
            "recovery": "Retry detection in a moment.",
            "connected": False,
        }
        self._status = "Mock JP-1011 ready" if mock else "Checking for a Vaydeer keypad"
        self._service_keepalive = "Mock active" if mock else "Service unavailable"
        self._retry_attempt = 0
        self._diagnostic_summary = "Run diagnostics to inspect the current Linux hardware setup."
        if mock:
            self._transport = MockJP1011Transport()
            self._protocol = VaydeerProtocol(self._transport)
            self._snapshot = self._load_snapshot()
            self._set_connection("connected", "Mock JP-1011 connected", "Mock transport is ready.", "", True)
        else:
            self._attempt_connection(schedule_retry=True)
        self._selected_key = 0
        self._selected_layer = 0
        self._preview: ApplyPreview | None = None
        self._tester_open = False
        self._tester_events: list[dict[str, str | int]] = []
        self.executor = BindingExecutor(mock_mode=mock)

    def _set_connection(self, state: str, title: str, message: str, recovery: str, connected: bool) -> None:
        self._connection = {
            "state": state,
            "title": title,
            "message": message,
            "recovery": recovery,
            "connected": connected,
        }

    def _attempt_connection(self, *, schedule_retry: bool) -> None:
        self._close_command_transport()
        self._connect_readonly()
        self._refresh_service_status()
        if self._protocol is not None:
            self._snapshot = self._load_snapshot()
        should_retry = (
            not bool(self._connection["connected"])
            and schedule_retry
            and self._retry_attempt < len(_STARTUP_RETRY_DELAYS_MS)
        )
        if should_retry and QGuiApplication.instance() is not None:
            delay = _STARTUP_RETRY_DELAYS_MS[self._retry_attempt]
            self._retry_attempt += 1
            QTimer.singleShot(delay, self.retryDetection)

    def _connect_readonly(self) -> None:
        """Open only the known vendor command interface for safe inspection."""

        try:
            interfaces = discover_linux_hidraw()
            candidates = [item for item in interfaces if item.is_vaydeer]
            if not candidates:
                self._set_connection(
                    "no_device",
                    "No Vaydeer device detected",
                    "No HID interface with VID:PID 0483:5752 is present.",
                    "Reconnect the keypad, then select Retry detection.",
                    False,
                )
                self._status = "No Vaydeer keypad detected"
                return
            interface = select_command_interface(candidates)
            if interface is None:
                self._set_connection(
                    "command_interface_missing",
                    "Vaydeer detected, command interface unavailable",
                    "Interface 0 with vendor usage 0xFF00/0x0001 was not found.",
                    "Reconnect the keypad and open Diagnostics for the interface table.",
                    False,
                )
                self._status = "Vaydeer detected but command interface 0 is unavailable"
                return
            self._transport = open_command_transport(interface.path)
            self._protocol = VaydeerProtocol(self._transport)
            self._status = "Vaydeer command interface opened; reading device information"
        except Exception as error:
            message = str(error)
            state = "permission_denied" if "Permission denied" in message else "command_interface_inaccessible"
            recovery = (
                "Run ./scripts/install.sh, then reconnect the keypad."
                if state == "permission_denied"
                else "Retry detection or open Diagnostics."
            )
            self._set_connection(state, "Vaydeer command interface inaccessible", message, recovery, False)
            self._status = f"Vaydeer detected but cannot open command interface: {message}"
            LOGGER.warning("Vaydeer command interface open failed: %s", message)

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
                capability = capability_for(snapshot.device)
                if capability.writable:
                    self._set_connection(
                        "connected",
                        "Vaydeer JP-1011 connected",
                        "Device information and mappings were read successfully.",
                        "",
                        True,
                    )
                else:
                    self._set_connection(
                        "unsupported_read_only",
                        "Vaydeer connected in read-only mode",
                        capability.reason,
                        "Export the profile or diagnostics; hardware writes are intentionally disabled.",
                        True,
                    )
                return snapshot
            except Exception as error:
                message = str(error)
                self._set_connection(
                    "protocol_failed",
                    "Vaydeer detected, protocol initialization failed",
                    message,
                    "Retry detection. If it persists, run vaydeer-studio-cli diagnostics --verbose.",
                    False,
                )
                self._status = f"Device inspection failed: {message}"
                LOGGER.warning("Vaydeer protocol initialization failed: %s", message)
        return self._snapshot

    @Property(dict, notify=changed)
    def device(self) -> dict[str, Any]:
        if not bool(self._connection["connected"]):
            return {
                "model": str(self._connection["title"]),
                "keyCount": 0,
                "firmware": "Not available",
                "bootloader": "Not available",
                "activeLayer": 0,
                "layerCount": 0,
                "keepalive": self._service_keepalive,
                "usb": "Disconnected",
                "permissions": "Check diagnostics",
                "writable": False,
                "warning": str(self._connection["message"]),
            }
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
            "usb": "Connected" if self._connection["state"] == "connected" else "Connected (read-only)",
            "permissions": "Granted (mock)" if self.mock else "Granted; verified by diagnostics",
            "writable": capability.writable and self.mock,
            "warning": (
                ""
                if self._service_keepalive not in {"Service unavailable", "stopped"}
                else (
                    "Keepalive service is unavailable. Run ./scripts/install.sh "
                    "to enable JP-1011 Linux key activation."
                )
            )
            if capability.writable
            else capability.reason,
        }

    @Property(dict, notify=changed)
    def connection(self) -> dict[str, str | bool]:
        return self._connection

    @Property(str, notify=changed)
    def diagnosticSummary(self) -> str:
        return self._diagnostic_summary

    @Property(list, notify=changed)
    def setupChecks(self) -> list[dict[str, str]]:
        device_status = "pass" if self._connection["connected"] else "fail"
        service_status = "pass" if self._service_keepalive == "active_readonly" else "warn"
        return [
            {"label": "Vaydeer device", "status": device_status},
            {"label": "Command interface 0", "status": device_status},
            {"label": "Keepalive interface 2", "status": service_status},
            {"label": "User service", "status": service_status},
        ]

    @Property(list, notify=changed)
    def keys(self) -> list[dict[str, Any]]:
        if not bool(self._connection["connected"]):
            return []
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
        if not bool(self._connection["connected"]):
            return []
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
        return layout_for_key_count(self._snapshot.device.key_count).columns if self._connection["connected"] else 3

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
            self._status = "No device is available to read; retrying detection"
            self._attempt_connection(schedule_retry=True)
        else:
            try:
                self._snapshot = self._protocol.read_snapshot()
                self.profile = self.profile.model_copy(update={"layers": self._snapshot.layers})
                self._status = "Read current configuration from device"
            except Exception as error:
                message = str(error)
                self._set_connection(
                    "protocol_failed",
                    "Vaydeer disconnected or stopped responding",
                    message,
                    "Retry detection. If it persists, open Diagnostics.",
                    False,
                )
                self._close_command_transport()
                self._status = f"Read failed: {message}; reconnecting"
                self._attempt_connection(schedule_retry=True)
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def reconnectDevice(self) -> None:
        if self.mock:
            self.readFromDevice()
            return
        self._retry_attempt = 0
        self._status = "Retrying Vaydeer device detection"
        self._attempt_connection(schedule_retry=True)
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def retryDetection(self) -> None:
        if self.mock:
            return
        self._attempt_connection(schedule_retry=True)
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def refreshDiagnostics(self) -> None:
        report = collect_diagnostics(verbose=False)
        self._diagnostic_summary = render_report(report, as_json=False)
        self._status = f"Diagnostics complete: {report.root_cause}"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def copyDiagnosticSummary(self) -> None:
        QGuiApplication.clipboard().setText(self._diagnostic_summary)
        self._status = "Sanitized diagnostic summary copied"
        self.statusChanged.emit()

    @Slot()
    def showSetupCommand(self) -> None:
        self._status = "Run ./scripts/install.sh in the project directory, then reconnect the keypad."
        self.statusChanged.emit()

    @Slot()
    def reloadService(self) -> None:
        result = subprocess.run(
            ["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True
        )
        if result.returncode == 0:
            result = subprocess.run(
                ["systemctl", "--user", "restart", "vaydeer-studio.service"],
                check=False,
                capture_output=True,
                text=True,
            )
        self._refresh_service_status()
        self._status = (
            "Keepalive service reloaded"
            if result.returncode == 0
            else result.stderr.strip() or "Could not reload service"
        )
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
        payload = collect_diagnostics(verbose=False).as_dict() | {"ui_status": self._status}
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
