"""QML-facing application model; all configuration changes still use core safety APIs."""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import socket
import subprocess
import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

from platformdirs import user_data_path
from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.keycodes import display_key_codes, parse_key_codes
from vaydeer_studio.core.models import (
    AssignmentKind,
    DeviceSnapshot,
    KeyAssignment,
    Layer,
    LinuxActionKind,
    LinuxBinding,
    MacroEventKind,
    MacroStep,
    Profile,
    ProfileTargetPlatform,
    SupportLevel,
    TriggerKind,
    factory_jp1011_profile,
)
from vaydeer_studio.core.profiles import ProfileStore, load_profile, save_profile
from vaydeer_studio.core.safety import ApplyPreview, apply_prepared, prepare_apply
from vaydeer_studio.core.templates import create_profile_from_template, profile_template_summaries
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
_CONNECTION_RETRY_INTERVAL_MS = 1_000
_CONNECTION_HEALTH_INTERVAL_MS = 1_500
_TESTER_POLL_INTERVAL_MS = 150
_TESTER_MINIMUM_PRESS_MS = 150
_SERVICE_UNIT = "vaydeer-studio.service"

_QT_KEY_F1 = int(Qt.Key.Key_F1)
_QT_KEY_F24 = int(Qt.Key.Key_F24)
_QT_KEY_A = int(Qt.Key.Key_A)
_QT_KEY_Z = int(Qt.Key.Key_Z)
_QT_KEY_0 = int(Qt.Key.Key_0)
_QT_KEY_9 = int(Qt.Key.Key_9)
_QT_KEYPAD_MODIFIER = Qt.KeyboardModifier.KeypadModifier.value
_QT_TO_VAYDEER_CODES = {
    int(Qt.Key.Key_Backspace): 8,
    int(Qt.Key.Key_Tab): 9,
    int(Qt.Key.Key_Return): 13,
    int(Qt.Key.Key_Enter): 13,
    int(Qt.Key.Key_Shift): 16,
    int(Qt.Key.Key_Control): 17,
    int(Qt.Key.Key_Alt): 18,
    int(Qt.Key.Key_Escape): 27,
    int(Qt.Key.Key_Space): 32,
    int(Qt.Key.Key_PageUp): 33,
    int(Qt.Key.Key_PageDown): 34,
    int(Qt.Key.Key_End): 35,
    int(Qt.Key.Key_Home): 36,
    int(Qt.Key.Key_Left): 37,
    int(Qt.Key.Key_Up): 38,
    int(Qt.Key.Key_Right): 39,
    int(Qt.Key.Key_Down): 40,
    int(Qt.Key.Key_Insert): 45,
    int(Qt.Key.Key_Delete): 46,
    int(Qt.Key.Key_Meta): 91,
}
_QT_MODIFIER_CODES = (
    (Qt.KeyboardModifier.ControlModifier.value, 17),
    (Qt.KeyboardModifier.AltModifier.value, 18),
    (Qt.KeyboardModifier.ShiftModifier.value, 16),
    (Qt.KeyboardModifier.MetaModifier.value, 91),
)


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
        self._command_instance_key: str | None = None
        self.profile = factory_jp1011_profile()
        self._profile_origin = "Device snapshot"
        self._saved_profile: Profile | None = None
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
        self._service_status: dict[str, str | bool] = {
            "host": socket.gethostname(),
            "installed": False,
            "running": False,
            "startup": False,
            "reachable": False,
            "detail": "Checking the local user service.",
        }
        self._diagnostic_summary = "Run diagnostics to inspect the current Linux hardware setup."
        self._setup_checks: list[dict[str, str]] = self._default_setup_checks()
        self._last_connection_error: str | None = None
        self._selected_key = 0
        self._selected_layer = 0
        self._selected_binding_index = -1
        self._connection_timer: QTimer | None = None
        self._health_timer: QTimer | None = None
        self._tester_timer: QTimer | None = None
        if mock:
            self._transport = MockJP1011Transport()
            self._protocol = VaydeerProtocol(self._transport)
            self._snapshot = self._load_snapshot()
            self._set_connection("connected", "Mock JP-1011 connected", "Mock transport is ready.", "", True)
        else:
            self._attempt_connection()
        if mock:
            self._refresh_service_status()
            self._setup_checks = [
                {"label": label, "status": "pass"}
                for label in (
                    "Mock keypad",
                    "Command interface",
                    "Keepalive interface",
                    "Command access",
                    "Keepalive access",
                    "udev rule",
                    "User service",
                    "Protocol read",
                )
            ]
            self._diagnostic_summary = "Mock JP-1011 diagnostics are ready; no physical HID device was opened."
        self._preview: ApplyPreview | None = None
        self._tester_open = False
        self._mapping_key_selection_active = False
        self._tester_events: list[dict[str, str | int]] = []
        self._tester_pressed_keys: set[int] = set()
        self._tester_press_started: dict[int, float] = {}
        self._tester_press_generations: dict[int, int] = {}
        self._tester_status = "Open the tester to begin listening for vendor events."
        self._captured_key_value = ""
        self._key_capture_active = False
        self._key_capture_hint = "Choose a value or start capture to record one explicit keyboard key."
        self._macro_recording = False
        self._macro_steps: list[MacroStep] = []
        self._macro_held_codes: set[int] = set()
        self._macro_last_input_at: float | None = None
        self.executor = BindingExecutor(mock_mode=mock)
        if not mock and QGuiApplication.instance() is not None:
            self._connection_timer = QTimer(self)
            self._connection_timer.setInterval(_CONNECTION_RETRY_INTERVAL_MS)
            self._connection_timer.timeout.connect(self._retry_connection_poll)
            self._health_timer = QTimer(self)
            self._health_timer.setInterval(_CONNECTION_HEALTH_INTERVAL_MS)
            self._health_timer.timeout.connect(self._monitor_device_connection)
            self._health_timer.start()
            self._tester_timer = QTimer(self)
            self._tester_timer.setInterval(_TESTER_POLL_INTERVAL_MS)
            self._tester_timer.timeout.connect(self._poll_tester_events)
        self._ensure_connection_polling()

    def _set_connection(self, state: str, title: str, message: str, recovery: str, connected: bool) -> None:
        self._connection = {
            "state": state,
            "title": title,
            "message": message,
            "recovery": recovery,
            "connected": connected,
        }

    def _attempt_connection(self, *, inspect_service: bool = True) -> None:
        self._close_command_transport()
        self._connect_readonly()
        self._refresh_service_status(inspect_unit=inspect_service)
        if self._protocol is not None:
            self._snapshot = self._load_snapshot()
        if bool(self._connection["connected"]):
            self._last_connection_error = None
            self._stop_connection_polling()
        else:
            self._ensure_connection_polling()

    def _ensure_connection_polling(self) -> None:
        """Keep retrying read-only discovery until the initial device read succeeds."""

        if self.mock or bool(self._connection["connected"]):
            return
        if self._connection_timer is not None and not self._connection_timer.isActive():
            self._connection_timer.start()

    def _stop_connection_polling(self) -> None:
        if self._connection_timer is not None and self._connection_timer.isActive():
            self._connection_timer.stop()

    def _retry_connection_poll(self) -> None:
        if self.mock or bool(self._connection["connected"]):
            self._stop_connection_polling()
            return
        self._attempt_connection(inspect_service=False)
        self.changed.emit()
        self.statusChanged.emit()

    def _log_connection_failure(self, context: str, message: str) -> None:
        error = f"{context}: {message}"
        if error != self._last_connection_error:
            LOGGER.warning("%s", error)
            self._last_connection_error = error

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
            self._command_instance_key = interface.instance_key
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
            self._log_connection_failure("Vaydeer command interface open failed", message)

    def _close_command_transport(self) -> None:
        if self._protocol is not None:
            with suppress(Exception):
                self._protocol.close()
        self._protocol = None
        self._transport = None
        self._command_instance_key = None

    def _monitor_device_connection(self) -> None:
        """Reflect unplug/replug changes without polling vendor commands."""

        if self.mock:
            return
        try:
            candidates = [item for item in discover_linux_hidraw() if item.is_vaydeer]
            interface = select_command_interface(candidates) if candidates else None
        except Exception as error:
            LOGGER.warning("Vaydeer connection health check failed: %s", error)
            interface = None
        if interface is None:
            was_connected = bool(self._connection["connected"]) or self._protocol is not None
            self._close_command_transport()
            self._refresh_service_status(inspect_unit=False)
            if was_connected:
                self._set_connection(
                    "device_disconnected",
                    "Vaydeer keypad disconnected",
                    "The command interface disappeared from Linux.",
                    "Reconnect the keypad; Vaydeer Studio will retry automatically.",
                    False,
                )
                self._status = "Vaydeer keypad disconnected; waiting for reconnect"
            self._ensure_connection_polling()
            self.changed.emit()
            self.statusChanged.emit()
            return
        if self._protocol is None or interface.instance_key != self._command_instance_key:
            self._attempt_connection(inspect_service=False)
            self.changed.emit()
            self.statusChanged.emit()
            return
        previous_keepalive = self._service_keepalive
        self._refresh_service_status(inspect_unit=False)
        if previous_keepalive != self._service_keepalive:
            self.changed.emit()

    def _refresh_service_status(self, *, inspect_unit: bool = True) -> None:
        service = self._inspect_user_service() if inspect_unit else dict(self._service_status)
        reachable = False
        if self.mock:
            self._service_keepalive = "Mock active"
        else:
            try:
                response = service_request(default_socket_path(), {"method": "status"})
                keepalive = response.get("result", {}).get("keepalive", {})
                self._service_keepalive = str(keepalive.get("state", "Service unavailable"))
                reachable = bool(response.get("ok"))
            except OSError:
                self._service_keepalive = "Service unavailable"
        if self.mock:
            try:
                response = service_request(default_socket_path(), {"method": "status"})
                reachable = bool(response.get("ok"))
            except OSError:
                reachable = False
        service["reachable"] = reachable
        if not bool(service["installed"]):
            service["detail"] = "The Vaydeer Studio user service is not installed on this host."
        elif bool(service["running"]) and reachable:
            service["detail"] = "The user service is running and reachable."
        elif bool(service["running"]):
            service["detail"] = "The user service is active, but its local control socket is not reachable."
        elif bool(service["startup"]):
            service["detail"] = "The user service is installed and enabled for login, but is not running now."
        else:
            service["detail"] = "The user service is installed but not enabled for login."
        self._service_status = service

    @staticmethod
    def _user_service_unit_path() -> Path:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return config_home / "systemd" / "user" / _SERVICE_UNIT

    def _inspect_user_service(self) -> dict[str, str | bool]:
        """Inspect the local per-user systemd unit without relying on device HID state."""

        unit_path = self._user_service_unit_path()
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "show",
                    _SERVICE_UNIT,
                    "--property=LoadState",
                    "--property=ActiveState",
                    "--property=UnitFileState",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {
                "host": socket.gethostname(),
                "installed": unit_path.exists(),
                "running": False,
                "startup": False,
                "reachable": False,
                "detail": "systemd user service status is unavailable on this host.",
            }
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        load_state = values.get("LoadState", "not-found")
        active_state = values.get("ActiveState", "inactive")
        unit_file_state = values.get("UnitFileState", "disabled")
        installed = load_state not in {"not-found", ""} or unit_path.exists()
        return {
            "host": socket.gethostname(),
            "installed": installed,
            "running": active_state == "active",
            "startup": unit_file_state.startswith("enabled"),
            "reachable": False,
            "detail": "",
        }

    @Slot()
    def installUserService(self) -> None:
        """Install only the current user's service unit; udev remains explicit."""

        unit_path = self._user_service_unit_path()
        executable = str(Path(sys.executable).resolve())
        unit_contents = "\n".join(
            (
                "[Unit]",
                "Description=Vaydeer Studio read-only keypad keepalive and binding service",
                "After=graphical-session.target",
                "Wants=graphical-session.target",
                "PartOf=graphical-session.target",
                "",
                "[Service]",
                "Type=simple",
                f"ExecStart={executable} -m vaydeer_studio.service.daemon --log-level info",
                "Restart=on-failure",
                "RestartSec=3",
                "Environment=PYTHONUNBUFFERED=1",
                "Environment=VAYDEER_STUDIO_LOG_LEVEL=INFO",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "StandardOutput=journal",
                "StandardError=journal",
                "",
                "[Install]",
                "WantedBy=default.target",
                "",
            )
        )
        try:
            unit_path.parent.mkdir(parents=True, exist_ok=True)
            unit_path.write_text(unit_contents, encoding="utf-8")
            reload_result = subprocess.run(
                ["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True, timeout=8
            )
            enable_result = subprocess.run(
                ["systemctl", "--user", "enable", "--now", _SERVICE_UNIT],
                check=False,
                capture_output=True,
                text=True,
                timeout=12,
            )
            self._refresh_service_status()
            if reload_result.returncode == 0 and enable_result.returncode == 0:
                self._status = "Installed, enabled, and started the local Vaydeer Studio service"
            else:
                detail = enable_result.stderr.strip() or reload_result.stderr.strip() or "systemctl returned an error"
                self._status = f"The user service unit was written, but could not start: {detail}"
        except (OSError, subprocess.TimeoutExpired) as error:
            self._refresh_service_status()
            self._status = f"Could not install the user service: {error}"
        self.changed.emit()
        self.statusChanged.emit()

    def _sync_service_bindings(self) -> None:
        if self.mock:
            return
        bindings = self.profile.linux_bindings if self.profileSupportsLinuxBindings else []
        try:
            service_request(
                default_socket_path(),
                {
                    "method": "set_bindings",
                    "bindings": [item.model_dump(mode="json") for item in bindings],
                },
            )
            self._refresh_service_status()
        except OSError:
            self._service_keepalive = "Service unavailable; bindings saved with the profile"

    def _load_snapshot(self) -> DeviceSnapshot:
        if self._protocol is not None:
            try:
                snapshot = self._protocol.read_snapshot()
                if not self.dirty:
                    self._adopt_device_layers(snapshot)
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
                self._log_connection_failure("Vaydeer protocol initialization failed", message)
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
            "writable": capability.writable,
            "warning": (
                ""
                if self._service_keepalive in {"active_readonly", "Mock active"}
                else (
                    f"Interface-2 keepalive is {self._service_keepalive}. "
                    "Normal Linux keyboard activation may be unavailable. "
                    "Open Diagnostics or run ./scripts/install.sh to repair it."
                )
            )
            if capability.writable
            else capability.reason,
        }

    @Property(dict, notify=changed)
    def service(self) -> dict[str, str | bool]:
        """Host-local status for the user-managed vaydeer-studiod unit."""

        return self._service_status

    @Property(dict, notify=changed)
    def connection(self) -> dict[str, str | bool]:
        return self._connection

    @Property(str, notify=changed)
    def diagnosticSummary(self) -> str:
        return self._diagnostic_summary

    @Property(list, notify=changed)
    def setupChecks(self) -> list[dict[str, str]]:
        return self._setup_checks

    @Property(list, notify=changed)
    def keys(self) -> list[dict[str, Any]]:
        if not bool(self._connection["connected"]):
            return []
        layer = self._current_layer()
        device_layer = self._snapshot_layer(layer.index)
        layout = layout_for_key_count(self._snapshot.device.key_count)
        values: list[dict[str, Any]] = []
        for item in layout.keys:
            assignment = layer.assignment_for(item.index)
            device_assignment = device_layer.assignment_for(item.index) if device_layer is not None else None
            pending = device_assignment is None or assignment != device_assignment
            values.append(
                {
                    "index": item.index,
                    "physicalLabel": item.label,
                    "label": assignment.display_name,
                    "value": self._assignment_value(assignment),
                    "kind": assignment.kind.value,
                    "support": assignment.support.value,
                    "selected": item.index == self._selected_key,
                    "pending": pending,
                    "syncState": "pending" if pending else "device",
                    "deviceLabel": (
                        device_assignment.display_name if device_assignment is not None else "No mapping on device"
                    ),
                    "deviceValue": self._assignment_value(device_assignment) if device_assignment is not None else "",
                }
            )
        return values

    @Property(list, notify=changed)
    def layers(self) -> list[dict[str, Any]]:
        if not bool(self._connection["connected"]):
            return []
        return [
            {
                "index": layer.index,
                "name": layer.name,
                "displayName": (
                    f"Layer {layer.index + 1}"
                    if layer.name == str(layer.index)
                    else f"Layer {layer.index + 1} - {layer.name}"
                ),
                "selected": layer.index == self._selected_layer,
            }
            for layer in self.profile.layers
        ]

    @Property(dict, notify=selectedKeyChanged)
    def selectedKey(self) -> dict[str, Any]:
        assignment = self._current_layer().assignment_for(self._selected_key)
        device_layer = self._snapshot_layer(self._selected_layer)
        device_assignment = device_layer.assignment_for(self._selected_key) if device_layer is not None else None
        pending = device_assignment is None or assignment != device_assignment
        return {
            "index": assignment.key_index,
            "label": assignment.label,
            "kind": assignment.kind.value,
            "category": self._category_for_assignment(assignment),
            "codes": display_key_codes(assignment.key_codes),
            "value": display_key_codes(assignment.key_codes),
            "actionData": assignment.action_data,
            "macroSteps": [step.display_name for step in assignment.macro_steps],
            "support": assignment.support.value,
            "notes": assignment.notes,
            "pending": pending,
            "syncState": "Pending sync" if pending else "Current on device",
            "deviceLabel": device_assignment.display_name if device_assignment is not None else "No mapping on device",
            "deviceValue": self._assignment_value(device_assignment) if device_assignment is not None else "",
            "deviceCategory": self._category_for_assignment(device_assignment) if device_assignment is not None else "",
        }

    @Property(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status

    @Property(bool, notify=changed)
    def dirty(self) -> bool:
        return self.profile.layers != self._snapshot.layers

    @Property(int, notify=changed)
    def pendingMappingCount(self) -> int:
        if not bool(self._connection["connected"]):
            return 0
        pending = 0
        for layer in self.profile.layers:
            device_layer = self._snapshot_layer(layer.index)
            if device_layer is None:
                pending += self._snapshot.device.key_count + 1
                continue
            if layer.name != device_layer.name:
                pending += 1
            for key_index in range(self._snapshot.device.key_count):
                if layer.assignment_for(key_index) != device_layer.assignment_for(key_index):
                    pending += 1
        pending += sum(1 for layer in self._snapshot.layers if self._profile_layer(layer.index) is None)
        return pending

    @Property(str, notify=changed)
    def deviceBaseline(self) -> str:
        timestamp = self._snapshot.captured_at.astimezone(UTC).strftime("%H:%M:%S UTC")
        return f"Read from device at {timestamp}"

    @Property(str, notify=changed)
    def profileName(self) -> str:
        return self.profile.name

    @Property(str, notify=changed)
    def profileOrigin(self) -> str:
        return self._profile_origin

    @Property(str, notify=changed)
    def profileTargetPlatform(self) -> str:
        return self.profile.target_platform.value

    @Property(str, notify=changed)
    def profileTargetPlatformLabel(self) -> str:
        return {
            ProfileTargetPlatform.LINUX: "Linux",
            ProfileTargetPlatform.MACOS: "macOS",
            ProfileTargetPlatform.WINDOWS: "Windows",
        }[self.profile.target_platform]

    @Property(str, notify=changed)
    def profileTargetApplication(self) -> str:
        return self.profile.target_application or "General"

    @Property(bool, notify=changed)
    def profileSupportsLinuxBindings(self) -> bool:
        return self.profile.target_platform == ProfileTargetPlatform.LINUX

    @Property(list, constant=True)
    def profilePlatforms(self) -> list[dict[str, str]]:
        return [
            {"id": ProfileTargetPlatform.LINUX.value, "label": "Linux"},
            {"id": ProfileTargetPlatform.MACOS.value, "label": "macOS"},
            {"id": ProfileTargetPlatform.WINDOWS.value, "label": "Windows"},
        ]

    @Property(list, constant=True)
    def profileTemplates(self) -> list[dict[str, str]]:
        return profile_template_summaries()

    @Property(bool, notify=changed)
    def profileDirty(self) -> bool:
        return self._saved_profile is None or self.profile != self._saved_profile

    @Property(list, notify=previewChanged)
    def previewLines(self) -> list[str]:
        return [] if self._preview is None else [item.describe() for item in self._preview.diff]

    @Property(str, notify=previewChanged)
    def backupPath(self) -> str:
        return "" if self._preview is None else str(self._preview.backup_path)

    @Property(list, notify=testerChanged)
    def testerEvents(self) -> list[dict[str, str | int]]:
        return self._tester_events

    @Property(str, notify=testerChanged)
    def testerStatus(self) -> str:
        return self._tester_status

    @Property(list, notify=testerChanged)
    def testerPressedKeys(self) -> list[int]:
        """Zero-based physical keys currently held according to vendor events."""

        return sorted(self._tester_pressed_keys)

    @Property(str, notify=selectedKeyChanged)
    def keyCaptureValue(self) -> str:
        return self._captured_key_value

    @Property(bool, notify=selectedKeyChanged)
    def keyCaptureActive(self) -> bool:
        return self._key_capture_active

    @Property(str, notify=selectedKeyChanged)
    def keyCaptureHint(self) -> str:
        return self._key_capture_hint

    @Property(str, notify=changed)
    def mappingKeySelectionStatus(self) -> str:
        if self.mock:
            return "Click a key in the layout to select it."
        if self._mapping_key_selection_active:
            return "Press a physical keypad key to select it in this editor."
        return "Open On-device mappings to select keys from the physical keypad."

    @Property(bool, notify=selectedKeyChanged)
    def macroRecording(self) -> bool:
        return self._macro_recording

    @Property(list, notify=selectedKeyChanged)
    def macroSteps(self) -> list[dict[str, str]]:
        return [{"label": step.display_name, "event": step.event.value} for step in self._macro_steps]

    @Property(bool, constant=True)
    def mockMode(self) -> bool:
        return self.mock

    @Property(list, notify=changed)
    def bindings(self) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for index, binding in enumerate(self.profile.linux_bindings):
            value = binding.model_dump(mode="json")
            value.update(
                {
                    "index": index,
                    "keyLabel": f"K{binding.key_index + 1}",
                    "layerLabel": f"Layer {binding.layer_index + 1}",
                    "argumentsText": shlex.join(binding.arguments),
                    "supported": binding.trigger in {TriggerKind.PRESS, TriggerKind.RELEASE},
                    "selected": index == self._selected_binding_index,
                }
            )
            values.append(value)
        return values

    @Property(dict, notify=changed)
    def bindingEditor(self) -> dict[str, Any]:
        if 0 <= self._selected_binding_index < len(self.profile.linux_bindings):
            binding = self.profile.linux_bindings[self._selected_binding_index]
            return {
                "editing": True,
                "index": self._selected_binding_index,
                "keyIndex": binding.key_index,
                "layerIndex": binding.layer_index,
                "action": binding.action.value,
                "target": binding.target,
                "arguments": shlex.join(binding.arguments),
                "trigger": binding.trigger.value,
                "allowShell": binding.allow_shell,
                "activeWindowPattern": binding.active_window_pattern or "",
                "supported": binding.trigger in {TriggerKind.PRESS, TriggerKind.RELEASE},
            }
        return {
            "editing": False,
            "index": -1,
            "keyIndex": self._selected_key,
            "layerIndex": self._selected_layer,
            "action": LinuxActionKind.APPLICATION.value,
            "target": "",
            "arguments": "",
            "trigger": TriggerKind.PRESS.value,
            "allowShell": False,
            "activeWindowPattern": "",
            "supported": True,
        }

    @Property(list, notify=changed)
    def backups(self) -> list[str]:
        return [str(path) for path in BackupStore().list()[:8]]

    @Property(list, notify=changed)
    def savedProfiles(self) -> list[dict[str, str | bool]]:
        return [
            {
                "id": item.id,
                "name": item.name,
                "layers": str(len(item.layers)),
                "bindings": str(len(item.linux_bindings)),
                "platform": self._platform_label(item.target_platform),
                "application": item.target_application or "General",
                "updated": item.updated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                "active": item.id == self.profile.id,
            }
            for item in ProfileStore().list()
        ]

    @Property(int, notify=changed)
    def layoutColumns(self) -> int:
        return layout_for_key_count(self._snapshot.device.key_count).columns if self._connection["connected"] else 3

    @Slot(int)
    def selectKey(self, index: int) -> None:
        self._selected_key = index
        self._captured_key_value = ""
        self._key_capture_active = False
        self._key_capture_hint = "Choose a value or start capture to record one explicit keyboard key."
        assignment = self._current_layer().assignment_for(index)
        self._macro_steps = list(assignment.macro_steps)
        self._macro_recording = False
        self._macro_held_codes.clear()
        self._macro_last_input_at = None
        self.selectedKeyChanged.emit()
        self.changed.emit()

    @Slot(int)
    def selectLayer(self, index: int) -> None:
        if not any(layer.index == index for layer in self.profile.layers):
            return
        self._selected_layer = index
        assignment = self._current_layer().assignment_for(self._selected_key)
        self._macro_steps = list(assignment.macro_steps)
        self._macro_recording = False
        self._macro_held_codes.clear()
        self._macro_last_input_at = None
        self._key_capture_active = False
        self._key_capture_hint = "Choose a value or start capture to record one explicit keyboard key."
        self.changed.emit()
        self.selectedKeyChanged.emit()

    @Slot(str, str, str, str)
    def saveKey(self, category: str, label: str, code_text: str, action_data: str = "") -> None:
        try:
            kind, support = self._kind_from_category(category)
            stable_key_kinds = {
                AssignmentKind.KEYBOARD,
                AssignmentKind.MODIFIER,
                AssignmentKind.COMBINATION,
                AssignmentKind.MEDIA,
                AssignmentKind.SYSTEM,
            }
            codes = self._parse_codes(code_text) if kind in stable_key_kinds else []
            macro_steps: list[MacroStep] = []
            if kind == AssignmentKind.MACRO:
                macro_steps = self._parse_macro_spec(action_data) if action_data.strip() else list(self._macro_steps)
                if not macro_steps:
                    raise ValueError("Record a macro or enter steps such as Ctrl+C; Wait 120; V")
            assignment = KeyAssignment(
                key_index=self._selected_key,
                label=label.strip(),
                kind=kind,
                key_codes=codes if support == SupportLevel.ON_DEVICE else [],
                action_data="" if kind == AssignmentKind.DISABLED else action_data.strip(),
                macro_steps=macro_steps,
                support=support,
                notes=self._assignment_notes(category, support),
            )
            layer = self._current_layer().with_assignment(assignment)
            self._replace_layer(layer)
            self._macro_steps = list(macro_steps)
            self._macro_recording = False
            self._macro_held_codes.clear()
            self._macro_last_input_at = None
            self._key_capture_active = False
            self._status = f"Key {self._selected_key + 1} updated in profile"
            self.changed.emit()
            self.selectedKeyChanged.emit()
            self.statusChanged.emit()
        except Exception as error:
            self._status = f"Could not update key: {error}"
            self.statusChanged.emit()

    @Slot()
    def beginKeyCapture(self) -> None:
        self._key_capture_active = True
        self._captured_key_value = ""
        self._key_capture_hint = (
            "Listening now. Press one key on your keyboard; numeric keypad digits stay as Num 0 through Num 9."
        )
        self.selectedKeyChanged.emit()

    @Slot()
    def cancelKeyCapture(self) -> None:
        self._key_capture_active = False
        self._key_capture_hint = "Capture cancelled. You can type a value or choose a standard key."
        self.selectedKeyChanged.emit()

    @Slot(int, int)
    def captureKeyInput(self, key: int, modifiers: int) -> None:
        """Populate the editor with a value captured from the physical keyboard."""

        try:
            codes = self._codes_from_qt(key, modifiers)
            self._captured_key_value = display_key_codes(codes)
            self._key_capture_active = False
            self._key_capture_hint = self._capture_description(codes, modifiers)
            self.selectedKeyChanged.emit()
        except ValueError as error:
            self._status = f"That key cannot be represented by the JP-1011 protocol: {error}"
            self._key_capture_hint = "That key is not supported by the documented JP-1011 mapping protocol."
            self.statusChanged.emit()
            self.selectedKeyChanged.emit()

    @Slot(str, result=list)
    def keyChoices(self, category: str) -> list[str]:
        """Provide safe, readable choices for the on-device key editor."""

        navigation = [
            "Enter",
            "Tab",
            "Esc",
            "Space",
            "Backspace",
            "Delete",
            "Insert",
            "Home",
            "End",
            "Page Up",
            "Page Down",
            "Left",
            "Up",
            "Right",
            "Down",
        ]
        keyboard = [
            *[chr(value) for value in range(ord("A"), ord("Z") + 1)],
            *[str(value) for value in range(10)],
            *[f"F{value}" for value in range(1, 25)],
            *[f"Num {value}" for value in range(10)],
            *navigation,
        ]
        choices = {
            "Keyboard key": keyboard,
            "Modifier": ["Ctrl", "Shift", "Alt", "Meta"],
            "Key combination": keyboard,
            "Media": ["Play/Pause", "Volume Mute", "Volume Down", "Volume Up"],
        }
        return choices.get(category, [])

    @Slot()
    def startMacroRecording(self) -> None:
        self._macro_steps = []
        self._macro_recording = True
        self._macro_held_codes.clear()
        self._macro_last_input_at = None
        self._status = "Macro recording is armed. Type in the focused capture area, then stop recording."
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def stopMacroRecording(self) -> None:
        self._macro_recording = False
        self._macro_held_codes.clear()
        self._macro_last_input_at = None
        self._status = f"Captured {len(self._macro_steps)} macro step(s)"
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def clearMacroRecording(self) -> None:
        self._macro_steps = []
        self._macro_recording = False
        self._macro_held_codes.clear()
        self._macro_last_input_at = None
        self.selectedKeyChanged.emit()

    @Slot(int, int, bool)
    def recordMacroInput(self, key: int, modifiers: int, pressed: bool) -> None:
        """Collect key press/release steps without emitting them to the desktop."""

        if not self._macro_recording:
            return
        try:
            codes = self._codes_from_qt(key, modifiers)
        except ValueError:
            return
        now = monotonic()
        if pressed and self._macro_last_input_at is not None:
            delay_ms = int((now - self._macro_last_input_at) * 1_000)
            if delay_ms >= 50:
                self._macro_steps.append(MacroStep(event=MacroEventKind.DELAY, delay_ms=min(delay_ms, 60_000)))
        if pressed:
            for code in codes:
                if code not in self._macro_held_codes:
                    self._macro_steps.append(MacroStep(event=MacroEventKind.PRESS, key_code=code))
                    self._macro_held_codes.add(code)
        else:
            primary = codes[-1]
            if primary in self._macro_held_codes:
                self._macro_steps.append(MacroStep(event=MacroEventKind.RELEASE, key_code=primary))
                self._macro_held_codes.discard(primary)
        self._macro_last_input_at = now
        self.selectedKeyChanged.emit()

    @Slot()
    def addLayer(self) -> None:
        used = {layer.index for layer in self.profile.layers}
        maximum = self._snapshot.device.max_layers
        next_index = next((index for index in range(maximum) if index not in used), None)
        if next_index is None:
            self._status = f"This device supports at most {maximum} layers"
            self.statusChanged.emit()
            return
        assignments = [KeyAssignment(key_index=index) for index in range(self.profile.key_count)]
        layer = Layer(index=next_index, name=str(next_index), assignments=assignments)
        layers = sorted([*self.profile.layers, layer], key=lambda item: item.index)
        self.profile = self.profile.model_copy(update={"layers": layers})
        self._selected_layer = next_index
        self._status = f"Layer {next_index + 1} added to the profile"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def duplicateLayer(self) -> None:
        used = {layer.index for layer in self.profile.layers}
        maximum = self._snapshot.device.max_layers
        next_index = next((index for index in range(maximum) if index not in used), None)
        if next_index is None:
            self._status = f"This device supports at most {maximum} layers"
            self.statusChanged.emit()
            return
        source = self._current_layer()
        duplicate = source.model_copy(update={"index": next_index, "name": f"{source.name} copy"[:28]})
        self.profile = self.profile.model_copy(
            update={"layers": sorted([*self.profile.layers, duplicate], key=lambda item: item.index)}
        )
        self._selected_layer = next_index
        self._status = f"Layer {source.index + 1} duplicated"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def deleteLayer(self) -> None:
        if len(self.profile.layers) <= 1:
            self._status = "A profile must keep at least one layer"
            self.statusChanged.emit()
            return
        deleted = self._selected_layer
        remaining = [layer for layer in self.profile.layers if layer.index != deleted]
        self.profile = self.profile.model_copy(update={"layers": remaining})
        self._selected_layer = remaining[0].index
        self._status = f"Layer {deleted + 1} removed from the profile"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot(str)
    def renameLayer(self, name: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            self._status = "Layer names cannot be empty"
            self.statusChanged.emit()
            return
        self._replace_layer(self._current_layer().model_copy(update={"name": clean_name[:28]}))
        self._status = "Layer renamed in the profile"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def discardChanges(self) -> None:
        self._adopt_device_layers(self._snapshot)
        self._preview = None
        self._status = "Pending on-device mapping changes discarded; showing the current device state"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.previewChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def readFromDevice(self) -> None:
        if self._protocol is None:
            self._status = "No device is available to read; retrying detection"
            self._attempt_connection()
        else:
            try:
                has_pending_changes = self.dirty
                self._snapshot = self._protocol.read_snapshot()
                if has_pending_changes:
                    self._status = (
                        "Device baseline refreshed; keeping "
                        f"{self.pendingMappingCount} pending mapping change(s) in the draft"
                    )
                else:
                    self._adopt_device_layers(self._snapshot)
                    self._status = "Read current mappings from device into the workspace"
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
                self._attempt_connection()
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def reconnectDevice(self) -> None:
        if self.mock:
            self.readFromDevice()
            return
        self._status = "Retrying Vaydeer device detection"
        self._attempt_connection()
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def retryDetection(self) -> None:
        if self.mock:
            return
        self._attempt_connection()
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def refreshDiagnostics(self) -> None:
        if self.mock:
            self._setup_checks = [
                {"label": label, "status": "pass"}
                for label in (
                    "Mock keypad",
                    "Command interface",
                    "Keepalive interface",
                    "Command access",
                    "Keepalive access",
                    "udev rule",
                    "User service",
                    "Protocol read",
                )
            ]
            self._diagnostic_summary = "Mock JP-1011 diagnostics are ready; no physical HID device was opened."
            self._status = "Mock diagnostics complete"
            self.changed.emit()
            self.statusChanged.emit()
            return
        report = collect_diagnostics(verbose=False)
        self._setup_checks = self._setup_checks_from_report(report)
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
        try:
            result = subprocess.run(
                ["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True, timeout=8
            )
            if result.returncode == 0:
                result = subprocess.run(
                    ["systemctl", "--user", "restart", _SERVICE_UNIT],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=12,
                )
        except (OSError, subprocess.TimeoutExpired) as error:
            self._refresh_service_status()
            self._status = f"Could not reload the user service: {error}"
            self.changed.emit()
            self.statusChanged.emit()
            return
        self._refresh_service_status()
        self._status = (
            "Keepalive service reloaded"
            if result.returncode == 0
            else result.stderr.strip() or "Could not reload service"
        )
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def refreshServiceStatus(self) -> None:
        self._refresh_service_status()
        self._status = "Refreshed local Vaydeer service status"
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
    def applyConfirmedPreview(self) -> None:
        """Apply a reviewed preview after the QML confirmation dialog is accepted."""

        if self._preview is None:
            self._status = "Create and review a diff first"
        elif self._protocol is None:
            self._preview = None
            self._status = (
                "The device disconnected before the write. No change was sent; prepare a new diff after reconnecting."
            )
            self.previewChanged.emit()
        else:
            try:
                result = apply_prepared(self._protocol, self._preview, confirmed=True)
                self._snapshot = result.verified
                self._adopt_device_layers(result.verified)
                write_target = "Mock write" if self.mock else "Device write"
                self._status = f"{write_target} verified. Backup preserved at {result.preview.backup_path}"
                self._preview = None
                self.changed.emit()
                self.previewChanged.emit()
            except Exception as error:
                # A failure may follow a partial write, so never leave a stale
                # preview available for a retry against an unknown device state.
                self._snapshot = self._load_snapshot()
                self._preview = None
                self._status = f"Apply failed: {error}"
                self.changed.emit()
                self.previewChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def newBinding(self) -> None:
        self._selected_binding_index = -1
        self._status = f"Creating a Linux binding for K{self._selected_key + 1} on layer {self._selected_layer + 1}"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot(int)
    def editBinding(self, index: int) -> None:
        if not 0 <= index < len(self.profile.linux_bindings):
            return
        binding = self.profile.linux_bindings[index]
        self._selected_binding_index = index
        self._selected_key = binding.key_index
        self._selected_layer = binding.layer_index
        self._status = f"Editing Linux binding for K{binding.key_index + 1} on layer {binding.layer_index + 1}"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot(str, str, str, str, bool, str)
    def addBinding(
        self,
        action: str,
        target: str,
        arguments: str,
        trigger: str = "press",
        allow_shell: bool = False,
        active_window_pattern: str = "",
    ) -> None:
        self._save_binding(
            action,
            target,
            arguments,
            trigger,
            allow_shell,
            active_window_pattern,
            replace_selected=False,
        )

    @Slot(str, str, str, str, bool, str)
    def saveBinding(
        self,
        action: str,
        target: str,
        arguments: str,
        trigger: str = "press",
        allow_shell: bool = False,
        active_window_pattern: str = "",
    ) -> None:
        self._save_binding(
            action,
            target,
            arguments,
            trigger,
            allow_shell,
            active_window_pattern,
            replace_selected=True,
        )

    def _save_binding(
        self,
        action: str,
        target: str,
        arguments: str,
        trigger: str,
        allow_shell: bool,
        active_window_pattern: str,
        *,
        replace_selected: bool,
    ) -> None:
        try:
            if not self.profileSupportsLinuxBindings:
                raise ValueError(
                    f"This profile targets {self.profileTargetPlatformLabel}; Linux-side bindings are available only "
                    "for Linux profiles"
                )
            trigger_kind = TriggerKind(trigger)
            if trigger_kind not in {TriggerKind.PRESS, TriggerKind.RELEASE}:
                raise ValueError("Only Press and Release triggers are implemented by the Linux service")
            action_kind = LinuxActionKind(action)
            if action_kind in {LinuxActionKind.NOTIFICATION, LinuxActionKind.TEXT} and not target.strip():
                raise ValueError(f"{action_kind.value.title()} bindings need a target")
            binding = LinuxBinding(
                key_index=self._selected_key,
                layer_index=self._selected_layer,
                action=action_kind,
                target=target.strip(),
                arguments=shlex.split(arguments),
                trigger=trigger_kind,
                allow_shell=allow_shell,
                active_window_pattern=active_window_pattern.strip() or None,
            )
            bindings = list(self.profile.linux_bindings)
            if replace_selected and 0 <= self._selected_binding_index < len(bindings):
                binding = binding.model_copy(update={"id": bindings[self._selected_binding_index].id})
                bindings[self._selected_binding_index] = binding
                self._status = "Linux-side binding updated"
            else:
                bindings.append(binding)
                self._selected_binding_index = len(bindings) - 1
                self._status = "Linux-side binding added"
            self.profile = self.profile.model_copy(update={"linux_bindings": bindings})
            self._sync_service_bindings()
            self.changed.emit()
            self.statusChanged.emit()
        except Exception as error:
            self._status = f"Could not add binding: {error}"
            self.statusChanged.emit()

    @Slot(int)
    def removeBinding(self, index: int) -> None:
        if not 0 <= index < len(self.profile.linux_bindings):
            return
        bindings = list(self.profile.linux_bindings)
        del bindings[index]
        self.profile = self.profile.model_copy(update={"linux_bindings": bindings})
        if self._selected_binding_index == index:
            self._selected_binding_index = -1
        elif self._selected_binding_index > index:
            self._selected_binding_index -= 1
        self._sync_service_bindings()
        self._status = "Linux-side binding removed"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot(int, bool)
    def setBindingEnabled(self, index: int, enabled: bool) -> None:
        if not 0 <= index < len(self.profile.linux_bindings):
            return
        bindings = list(self.profile.linux_bindings)
        bindings[index] = bindings[index].model_copy(update={"enabled": enabled})
        self.profile = self.profile.model_copy(update={"linux_bindings": bindings})
        self._sync_service_bindings()
        self.changed.emit()

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
            update={
                "id": f"{self.profile.id}-copy",
                "name": f"{self.profile.name} copy",
                "updated_at": datetime.now(UTC),
            }
        )
        store = ProfileStore()
        store.save(self.profile)
        store.set_active(self.profile.id)
        self._saved_profile = self.profile.model_copy(deep=True)
        self._profile_origin = "Local profile"
        self._sync_service_bindings()
        self._status = "Profile duplicated and saved to the local profile library"
        self.changed.emit()
        self.statusChanged.emit()

    @Slot()
    def createProfile(self) -> None:
        self.profile = factory_jp1011_profile().model_copy(update={"name": "Untitled profile"})
        self._saved_profile = None
        self._profile_origin = "New profile"
        self._selected_key = 0
        self._selected_layer = self.profile.layers[0].index
        self._selected_binding_index = -1
        self._macro_steps = []
        self._sync_service_bindings()
        self._status = "New JP-1011 profile created"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot(str)
    def setProfileTargetPlatform(self, platform: str) -> None:
        try:
            target = ProfileTargetPlatform(platform)
        except ValueError:
            self._status = f"Unknown profile target platform: {platform}"
            self.statusChanged.emit()
            return
        if target == self.profile.target_platform:
            return
        self.profile = self.profile.model_copy(update={"target_platform": target, "updated_at": datetime.now(UTC)})
        self._sync_service_bindings()
        if target == ProfileTargetPlatform.LINUX:
            self._status = "Profile targets Linux; its Linux-side bindings can run through the local service"
        else:
            self._status = (
                f"Profile targets {self._platform_label(target)}; Linux-side bindings are retained but not loaded "
                "into this Linux service"
            )
        self.changed.emit()
        self.statusChanged.emit()

    @Slot(str, str)
    def createProfileFromTemplate(self, template_id: str, platform: str) -> None:
        try:
            target = ProfileTargetPlatform(platform)
            self.profile = create_profile_from_template(template_id, target)
            self._saved_profile = None
            self._profile_origin = "Application preset"
            self._selected_key = 0
            self._selected_layer = self.profile.layers[0].index
            self._selected_binding_index = -1
            self._macro_steps = []
            self._macro_recording = False
            self._macro_held_codes.clear()
            self._macro_last_input_at = None
            self._sync_service_bindings()
            self._status = f"Created {self.profile.name!r}. Review its mappings before applying them to a device."
            self.changed.emit()
            self.selectedKeyChanged.emit()
        except Exception as error:
            self._status = f"Could not create profile preset: {error}"
        self.statusChanged.emit()

    @Slot(str)
    def renameProfile(self, name: str) -> None:
        if name.strip():
            self.profile = self.profile.model_copy(update={"name": name.strip(), "updated_at": datetime.now(UTC)})
            self._status = "Profile name changed; save it to retain the local copy"
            self.changed.emit()
            self.statusChanged.emit()

    @Slot(str)
    def importProfile(self, source: str) -> None:
        try:
            profile = load_profile(Path(source).expanduser())
            if profile.key_count != self._snapshot.device.key_count:
                raise ValueError(
                    f"Profile expects {profile.key_count} keys; this keypad has {self._snapshot.device.key_count}"
                )
            self.profile = profile
            self._saved_profile = profile.model_copy(deep=True)
            self._profile_origin = "Imported profile"
            self._selected_layer = profile.layers[0].index if profile.layers else 0
            self._selected_binding_index = -1
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
        self._saved_profile = None
        self._profile_origin = "New profile"
        self._selected_key = 0
        self._selected_layer = 0
        self._selected_binding_index = -1
        self._status = "Current profile cleared"
        self.changed.emit()
        self.selectedKeyChanged.emit()
        self.statusChanged.emit()

    @Slot()
    def saveProfile(self) -> None:
        store = ProfileStore()
        self.profile = self.profile.model_copy(update={"updated_at": datetime.now(UTC)})
        path = store.save(self.profile)
        store.set_active(self.profile.id)
        self._saved_profile = self.profile.model_copy(deep=True)
        self._profile_origin = "Local profile"
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
            self._saved_profile = profile.model_copy(deep=True)
            self._profile_origin = "Local profile"
            self._selected_layer = profile.layers[0].index if profile.layers else 0
            self._selected_binding_index = -1
            ProfileStore().set_active(profile.id)
            self._sync_service_bindings()
            self._status = f"Loaded profile {profile.name!r}"
            self.changed.emit()
            self.selectedKeyChanged.emit()
        except Exception as error:
            self._status = f"Could not load profile: {error}"
            self.statusChanged.emit()

    @Slot(str)
    def exportProfile(self, format_name: str = "json") -> None:
        root = user_data_path("Vaydeer Studio", "Vaydeer Studio") / "profiles"
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = ".yaml" if format_name.lower() in {"yaml", "yml"} else ".json"
        path = root / f"{self.profile.name.lower().replace(' ', '-')}-{timestamp}{suffix}"
        save_profile(self.profile, path)
        self._status = f"Profile exported to {path}"
        self.statusChanged.emit()

    @Slot(int)
    def setActivePage(self, index: int) -> None:
        """Align vendor-event listening with the visible screen in one transition."""

        self._set_event_listener_mode(tester_open=index == 4, mapping_selection_open=index == 1)

    @Slot(bool)
    def setTesterOpen(self, opened: bool) -> None:
        self._set_event_listener_mode(tester_open=opened, mapping_selection_open=self._mapping_key_selection_active)

    @Slot(bool)
    def setMappingKeySelectionActive(self, opened: bool) -> None:
        self._set_event_listener_mode(tester_open=self._tester_open, mapping_selection_open=opened)

    def _set_event_listener_mode(self, *, tester_open: bool, mapping_selection_open: bool) -> None:
        previous_tester_open = self._tester_open
        self._tester_open = tester_open
        self._mapping_key_selection_active = mapping_selection_open
        active = tester_open or mapping_selection_open
        if self.mock:
            if tester_open:
                self._tester_status = "Click a keypad button to generate mock press and release reports."
        elif active:
            self._set_service_tester(True)
            if self._tester_timer is not None and not self._tester_timer.isActive():
                self._tester_timer.start()
        else:
            if self._tester_timer is not None and self._tester_timer.isActive():
                self._tester_timer.stop()
            self._set_service_tester(False)
            self._tester_status = "Tester closed; vendor events are no longer recorded for this screen."
        if previous_tester_open and not tester_open:
            self._tester_events = []
            self._tester_pressed_keys.clear()
            self._tester_press_started.clear()
            self._tester_press_generations.clear()
        self.testerChanged.emit()
        self.changed.emit()

    def _set_service_tester(self, enabled: bool) -> None:
        try:
            response = service_request(default_socket_path(), {"method": "set_tester", "enabled": enabled})
            result = response.get("result", {})
            keepalive = result.get("keepalive", {})
            self._service_keepalive = str(keepalive.get("state", self._service_keepalive))
            if not response.get("ok"):
                raise OSError(str(response.get("error", "tester service request failed")))
            self._tester_status = (
                "Listening on the read-only vendor event interface. Press a physical keypad key."
                if enabled
                else "Tester closed; vendor events are no longer recorded for this screen."
            )
        except OSError as error:
            self._tester_status = f"Live event service unavailable: {error}"
            self._service_keepalive = "Service unavailable"
            LOGGER.warning("Vaydeer live tester service request failed: %s", error)
        self.changed.emit()

    def _poll_tester_events(self) -> None:
        if self.mock or not (self._tester_open or self._mapping_key_selection_active):
            return
        try:
            response = service_request(default_socket_path(), {"method": "drain_tester_events"})
            if not response.get("ok"):
                raise OSError(str(response.get("error", "tester event request failed")))
            result = response.get("result", {})
            keepalive = result.get("keepalive", {})
            self._service_keepalive = str(keepalive.get("state", self._service_keepalive))
            events = result.get("events", [])
            if events:
                for item in events:
                    key_index = item.get("key_index")
                    layer_index = item.get("layer_index")
                    pressed = item.get("pressed")
                    valid_key_index = key_index if isinstance(key_index, int) else None
                    valid_layer_index = layer_index if isinstance(layer_index, int) else None
                    valid_pressed = pressed if isinstance(pressed, bool) else None
                    if (
                        self._mapping_key_selection_active
                        and valid_pressed is True
                        and valid_key_index is not None
                        and 0 <= valid_key_index < self._snapshot.device.key_count
                    ):
                        self.selectKey(valid_key_index)
                        self._status = f"Selected K{valid_key_index + 1} from a physical keypad press"
                        self.statusChanged.emit()
                    if self._tester_open:
                        self._append_tester_event(
                            key_index=valid_key_index,
                            layer_index=valid_layer_index,
                            pressed=valid_pressed,
                            timestamp=str(item.get("timestamp", "")),
                            raw=str(item.get("raw", "")),
                        )
                if self._tester_open:
                    self._tester_status = "Receiving vendor key events."
                    self.testerChanged.emit()
            self.changed.emit()
        except OSError as error:
            self._tester_status = f"Live event service unavailable: {error}"
            self._service_keepalive = "Service unavailable"
            self.testerChanged.emit()
            self.changed.emit()

    @Slot(int)
    def simulateKey(self, key_index: int) -> None:
        if not isinstance(self._transport, MockJP1011Transport) or not self._tester_open:
            return
        self._record_mock_tester_event(key_index, True)
        if QGuiApplication.instance() is None:
            self._record_mock_tester_event(key_index, False)
        else:
            QTimer.singleShot(140, lambda: self._record_mock_tester_event(key_index, False))
        self.testerChanged.emit()

    def _record_mock_tester_event(self, key_index: int, pressed: bool) -> None:
        if not isinstance(self._transport, MockJP1011Transport) or not self._tester_open:
            return
        raw = self._transport.queue_event(key_index, pressed, self._selected_layer)
        self._append_tester_event(
            key_index=key_index,
            layer_index=self._selected_layer,
            pressed=pressed,
            timestamp=datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3],
            raw=raw[:6].hex(" "),
        )
        self.testerChanged.emit()

    def _append_tester_event(
        self,
        *,
        key_index: int | None,
        layer_index: int | None,
        pressed: bool | None,
        timestamp: str,
        raw: str,
    ) -> None:
        if key_index is not None:
            if pressed is True:
                self._tester_pressed_keys.add(key_index)
                self._tester_press_started[key_index] = monotonic()
                self._tester_press_generations[key_index] = self._tester_press_generations.get(key_index, 0) + 1
            elif pressed is False:
                self._release_tester_key(key_index)
        self._tester_events.insert(
            0,
            {
                "timestamp": timestamp,
                "key": key_index + 1 if key_index is not None else 0,
                "event": "Press" if pressed is True else "Release" if pressed is False else "Unknown",
                "layer": layer_index + 1 if layer_index is not None else 0,
                "source": "Keypad",
                "raw": raw,
            },
        )
        self._tester_events = self._tester_events[:30]

    @Slot()
    def clearTesterEvents(self) -> None:
        """Clear the UI-only event history without changing service state."""

        self._tester_events = []
        self._status = "Live tester events cleared"
        self.testerChanged.emit()
        self.statusChanged.emit()

    @Slot(int)
    def copyTesterEvent(self, index: int) -> None:
        """Copy a readable event summary instead of exposing raw reports by default."""

        if not 0 <= index < len(self._tester_events):
            self._status = "Select a live tester event to copy"
            self.statusChanged.emit()
            return
        event = self._tester_events[index]
        key = f"K{event['key']}" if event["key"] else "Unknown key"
        layer = f"Layer {event['layer']}" if event["layer"] else "Unknown layer"
        QGuiApplication.clipboard().setText(
            f"{event['timestamp']}  {key}  {event['event']}  {layer}  {event['source']}"
        )
        self._status = "Live tester event copied"
        self.statusChanged.emit()

    @Slot()
    def exportTesterSession(self) -> None:
        """Export the bounded, UI-visible tester session to the XDG data directory."""

        root = user_data_path("Vaydeer Studio", "Vaydeer Studio") / "tester-sessions"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"tester-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        capability = capability_for(self._snapshot.device)
        payload = {
            "schema_version": 1,
            "captured_at": datetime.now(UTC).isoformat(),
            "device": "Vaydeer JP-1011" if self._snapshot.device.key_count == 9 else capability.model,
            "events": self._tester_events,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._status = f"Live tester session exported to {path}"
        self.statusChanged.emit()

    def _release_tester_key(self, key_index: int) -> None:
        """Keep batched physical press/release reports visible for one render frame."""

        if key_index not in self._tester_pressed_keys:
            return
        started = self._tester_press_started.get(key_index, monotonic())
        remaining_ms = _TESTER_MINIMUM_PRESS_MS - int((monotonic() - started) * 1_000)
        generation = self._tester_press_generations.get(key_index, 0)
        if remaining_ms <= 0 or QGuiApplication.instance() is None:
            self._finish_tester_release(key_index, generation)
            return
        QTimer.singleShot(
            remaining_ms,
            lambda: self._finish_tester_release(key_index, generation),
        )

    def _finish_tester_release(self, key_index: int, generation: int) -> None:
        if self._tester_press_generations.get(key_index) != generation:
            return
        self._tester_pressed_keys.discard(key_index)
        self._tester_press_started.pop(key_index, None)
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
        layer = self._profile_layer(self._selected_layer)
        if layer is not None:
            return layer
        return self.profile.layers[0]

    def _profile_layer(self, index: int) -> Layer | None:
        return next((layer for layer in self.profile.layers if layer.index == index), None)

    def _snapshot_layer(self, index: int) -> Layer | None:
        return next((layer for layer in self._snapshot.layers if layer.index == index), None)

    def _adopt_device_layers(self, snapshot: DeviceSnapshot) -> None:
        """Use a fresh device snapshot only when there is no staged device diff."""

        self.profile = self.profile.model_copy(update={"layers": snapshot.layers})
        if self._profile_layer(self._selected_layer) is None:
            self._selected_layer = snapshot.layers[0].index if snapshot.layers else 0
        self._selected_key = min(self._selected_key, max(0, snapshot.device.key_count - 1))
        self._profile_origin = "Device snapshot"

    @staticmethod
    def _assignment_value(assignment: KeyAssignment) -> str:
        if assignment.key_codes:
            return display_key_codes(assignment.key_codes)
        return assignment.display_name

    def _replace_layer(self, replacement: Layer) -> None:
        layers = [replacement if layer.index == replacement.index else layer for layer in self.profile.layers]
        self.profile = self.profile.model_copy(update={"layers": layers})

    @staticmethod
    def _default_setup_checks() -> list[dict[str, str]]:
        return [
            {"label": label, "status": "warn"}
            for label in (
                "Vaydeer device",
                "Command interface 0",
                "Keepalive interface 2",
                "Command access",
                "Keepalive access",
                "udev rule",
                "User service",
                "Protocol read",
            )
        ]

    @staticmethod
    def _setup_checks_from_report(report: Any) -> list[dict[str, str]]:
        labels = {
            "device": "Vaydeer device",
            "command_interface": "Command interface 0",
            "keepalive_interface": "Keepalive interface 2",
            "command_access": "Command access",
            "keepalive_access": "Keepalive access",
            "udev_rule": "udev rule",
            "user_service": "User service",
            "protocol": "Protocol read",
        }
        statuses = {check.id: check.status for check in report.checks}
        return [{"label": label, "status": statuses.get(identifier, "warn")} for identifier, label in labels.items()]

    @staticmethod
    def _parse_codes(text: str) -> list[int]:
        return parse_key_codes(text)

    @staticmethod
    def _codes_from_qt(key: int, modifiers: int) -> list[int]:
        """Translate a Qt key event into the byte values used by profiles."""

        primary: int | None
        if _QT_KEY_0 <= key <= _QT_KEY_9 and modifiers & _QT_KEYPAD_MODIFIER:
            # Qt reports both the top-row and numeric-pad digits as Key_0..Key_9.
            # The modifier is the only reliable distinction, and Vaydeer's byte
            # protocol stores them as the virtual-key NUMPAD0..NUMPAD9 range.
            primary = 96 + (key - _QT_KEY_0)
        elif _QT_KEY_A <= key <= _QT_KEY_Z or _QT_KEY_0 <= key <= _QT_KEY_9:
            primary = ord(chr(key))
        elif _QT_KEY_F1 <= key <= _QT_KEY_F24:
            primary = 112 + (key - _QT_KEY_F1)
        else:
            primary = _QT_TO_VAYDEER_CODES.get(key)
        if primary is None:
            raise ValueError(f"Qt key {key}")
        modifier_codes = [code for mask, code in _QT_MODIFIER_CODES if modifiers & mask and code != primary]
        return [*modifier_codes, primary]

    @staticmethod
    def _capture_description(codes: list[int], modifiers: int) -> str:
        value = display_key_codes(codes)
        primary = codes[-1]
        if 96 <= primary <= 105 and modifiers & _QT_KEYPAD_MODIFIER:
            return f"Captured numeric keypad {primary - 96} as {value} (Vaydeer code {primary})."
        return f"Captured {value} as the explicit JP-1011 key value."

    @staticmethod
    def _platform_label(platform: ProfileTargetPlatform) -> str:
        return {
            ProfileTargetPlatform.LINUX: "Linux",
            ProfileTargetPlatform.MACOS: "macOS",
            ProfileTargetPlatform.WINDOWS: "Windows",
        }[platform]

    @staticmethod
    def _parse_macro_spec(text: str) -> list[MacroStep]:
        """Parse a compact portable macro notation without claiming device support.

        Each semicolon-separated shortcut is pressed then released.  ``Wait 120``
        adds a delay.  These steps are stored in the profile and never emitted to
        a physical keypad until the vendor macro payload is independently known.
        """

        steps: list[MacroStep] = []
        for part in (item.strip() for item in re.split(r"[;\n]", text)):
            if not part:
                continue
            delay = re.fullmatch(r"(?:wait|delay)\s+(\d+)\s*(?:ms)?", part, re.IGNORECASE)
            if delay:
                steps.append(MacroStep(event=MacroEventKind.DELAY, delay_ms=int(delay.group(1))))
                continue
            codes = parse_key_codes(part)
            steps.extend(MacroStep(event=MacroEventKind.PRESS, key_code=code) for code in codes)
            steps.extend(MacroStep(event=MacroEventKind.RELEASE, key_code=code) for code in reversed(codes))
        return steps

    @staticmethod
    def _assignment_notes(category: str, support: SupportLevel) -> str:
        if support == SupportLevel.ON_DEVICE:
            return "Stored on the keypad and eligible for a verified write."
        if support == SupportLevel.SERVICE:
            return f"{category} is handled by Vaydeer Studio's Linux service; it is not sent to the keypad."
        return f"{category} is retained in this profile for research and mock workflows; it is never sent to hardware."

    @staticmethod
    def _category_for_assignment(assignment: KeyAssignment) -> str:
        categories = {
            AssignmentKind.KEYBOARD: "Keyboard key",
            AssignmentKind.MODIFIER: "Modifier",
            AssignmentKind.COMBINATION: "Key combination",
            AssignmentKind.MEDIA: "Media",
            AssignmentKind.SYSTEM: "System control",
            AssignmentKind.MOUSE: "Mouse",
            AssignmentKind.MACRO: "Macro",
            AssignmentKind.TEXT: "Text",
            AssignmentKind.VAYDEER: "Vaydeer action",
            AssignmentKind.LINUX_HOST: "Linux host action",
            AssignmentKind.DISABLED: "Disabled",
        }
        if assignment.kind == AssignmentKind.SPECIAL:
            return "Layer action"
        return categories.get(assignment.kind, "Vaydeer action")

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
            "Layer action": AssignmentKind.SPECIAL,
            "Vaydeer action": AssignmentKind.VAYDEER,
            "Linux host action": AssignmentKind.LINUX_HOST,
        }
        kind = experimental.get(category, AssignmentKind.SPECIAL)
        service_managed = {AssignmentKind.TEXT, AssignmentKind.LINUX_HOST}
        return kind, SupportLevel.SERVICE if kind in service_managed else SupportLevel.EXPERIMENTAL
