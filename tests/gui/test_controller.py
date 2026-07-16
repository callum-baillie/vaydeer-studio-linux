from __future__ import annotations

from subprocess import CompletedProcess

from vaydeer_studio.core.errors import DeviceError
from vaydeer_studio.core.models import AssignmentKind, SupportLevel
from vaydeer_studio.devices.discovery import COMMAND_USAGE, EVENT_USAGE, VENDOR_USAGE_PAGE, HidInterface
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.ui import controller as controller_module
from vaydeer_studio.ui.controller import StudioController


def _interfaces(instance: str) -> list[HidInterface]:
    return [
        HidInterface(
            "/dev/hidraw17",
            0x0483,
            0x5752,
            0,
            VENDOR_USAGE_PAGE,
            COMMAND_USAGE,
            sysfs_path=f"/sys/devices/usb/{instance}/interface0",
        ),
        HidInterface(
            "/dev/hidraw23",
            0x0483,
            0x5752,
            2,
            VENDOR_USAGE_PAGE,
            EVENT_USAGE,
            sysfs_path=f"/sys/devices/usb/{instance}/interface2",
        ),
    ]


def _active_service(_path, _request):
    return {"ok": True, "result": {"keepalive": {"state": "active_readonly"}}}


def test_mock_controller_exposes_verified_three_by_three_layout() -> None:
    controller = StudioController(mock=True)
    assert controller.layoutColumns == 3
    assert [item["physicalLabel"] for item in controller.keys] == [
        "Top left",
        "Top center",
        "Top right",
        "Middle left",
        "Middle center",
        "Middle right",
        "Bottom left",
        "Bottom center",
        "Bottom right",
    ]


def test_mock_tester_reports_one_based_layer_numbers() -> None:
    controller = StudioController(mock=True)
    controller.setTesterOpen(True)
    controller.simulateKey(0)

    assert [event["event"] for event in controller.testerEvents] == ["Release", "Press"]
    assert all(event["layer"] == 1 for event in controller.testerEvents)


def test_controller_edits_profile_and_generates_diff() -> None:
    controller = StudioController(mock=True)
    controller.selectKey(0)
    controller.saveKey("Keyboard key", "A", "A")
    assert controller.dirty
    controller.previewApply()
    assert any("Num 7 -> A" in line for line in controller.previewLines)


def test_controller_uses_readable_key_values_and_typed_macro_steps() -> None:
    controller = StudioController(mock=True)
    controller.saveKey("Key combination", "", "CTRL+P", "")

    assert controller.selectedKey["codes"] == "Ctrl + P"
    assert controller.keys[0]["label"] == "Ctrl + P"

    controller.startMacroRecording()
    controller.recordMacroInput(ord("A"), 0, True)
    controller.recordMacroInput(ord("A"), 0, False)
    controller.saveKey("Macro", "Clipboard", "", "")

    assignment = controller.profile.layers[0].assignment_for(0)
    assert assignment.kind == AssignmentKind.MACRO
    assert assignment.support == SupportLevel.EXPERIMENTAL
    assert [step.display_name for step in assignment.macro_steps] == ["Press A", "Release A"]


def test_all_editor_action_categories_create_a_safe_profile_assignment() -> None:
    controller = StudioController(mock=True)
    expected = {
        "Mouse": (AssignmentKind.MOUSE, SupportLevel.EXPERIMENTAL),
        "Text": (AssignmentKind.TEXT, SupportLevel.SERVICE),
        "Layer action": (AssignmentKind.SPECIAL, SupportLevel.EXPERIMENTAL),
        "Vaydeer action": (AssignmentKind.VAYDEER, SupportLevel.EXPERIMENTAL),
        "Linux host action": (AssignmentKind.LINUX_HOST, SupportLevel.SERVICE),
        "Disabled": (AssignmentKind.DISABLED, SupportLevel.ON_DEVICE),
    }
    for category, (kind, support) in expected.items():
        controller.saveKey(category, category, "", "draft detail")
        assignment = controller.profile.layers[0].assignment_for(0)
        assert assignment.kind == kind
        assert assignment.support == support
        assert assignment.transmit_supported is (kind == AssignmentKind.DISABLED)

    controller.saveKey("Macro", "Macro", "", "Ctrl+C; Wait 120; Ctrl+V")
    assert controller.profile.layers[0].assignment_for(0).kind == AssignmentKind.MACRO


def test_controller_layer_controls_and_tester_pressed_state() -> None:
    controller = StudioController(mock=True)
    controller.addLayer()
    assert [layer.index for layer in controller.profile.layers] == [0, 1]
    assert controller.layers[-1]["selected"]

    controller.renameLayer("Editing")
    assert controller.profile.layers[-1].name == "Editing"
    controller.duplicateLayer()
    assert len(controller.profile.layers) == 3
    controller.deleteLayer()
    assert len(controller.profile.layers) == 2

    controller.setTesterOpen(True)
    controller._append_tester_event(
        key_index=4,
        layer_index=1,
        pressed=True,
        timestamp="12:00:00.000",
        raw="fb 03 01 04 01 fc",
    )
    assert controller.testerPressedKeys == [4]
    controller._append_tester_event(
        key_index=4,
        layer_index=1,
        pressed=False,
        timestamp="12:00:00.100",
        raw="fb 03 01 04 00 fd",
    )
    assert controller.testerPressedKeys == []


def test_batched_tester_release_keeps_a_visual_press_until_the_timer_runs(monkeypatch) -> None:
    callbacks: list[tuple[int, object]] = []

    class FakeGuiApplication:
        @staticmethod
        def instance() -> object:
            return object()

    class FakeTimer:
        @staticmethod
        def singleShot(delay: int, callback: object) -> None:
            callbacks.append((delay, callback))

    monkeypatch.setattr(controller_module, "QGuiApplication", FakeGuiApplication)
    monkeypatch.setattr(controller_module, "QTimer", FakeTimer)
    controller = StudioController(mock=True)
    controller.setTesterOpen(True)

    controller._append_tester_event(
        key_index=6,
        layer_index=0,
        pressed=True,
        timestamp="12:00:00.000",
        raw="fb 03 00 06 00 fe",
    )
    controller._append_tester_event(
        key_index=6,
        layer_index=0,
        pressed=False,
        timestamp="12:00:00.001",
        raw="fb 03 00 06 02 fc",
    )

    assert controller.testerPressedKeys == [6]
    assert callbacks and callbacks[0][0] > 0
    callback = callbacks[0][1]
    assert callable(callback)
    callback()
    assert controller.testerPressedKeys == []


def test_controller_reports_and_installs_host_local_user_service(monkeypatch, tmp_path) -> None:
    def fake_run(command, **_kwargs):
        if "show" in command:
            return CompletedProcess(command, 0, "LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n", "")
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(controller_module.subprocess, "run", fake_run)
    monkeypatch.setattr(controller_module, "service_request", _active_service)
    unit_path = tmp_path / "systemd" / "user" / "vaydeer-studio.service"
    monkeypatch.setattr(StudioController, "_user_service_unit_path", staticmethod(lambda: unit_path))

    controller = StudioController(mock=True)
    assert controller.service["installed"] is True
    assert controller.service["running"] is True
    assert controller.service["startup"] is True
    assert controller.service["reachable"] is True

    controller.installUserService()
    assert unit_path.exists()
    assert "vaydeer_studio.service.daemon" in unit_path.read_text(encoding="utf-8")


def test_controller_exposes_a_real_disconnected_state(monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "discover_linux_hidraw", lambda: [])
    controller = StudioController(mock=False)

    assert controller.connection["state"] == "no_device"
    assert controller.device["model"] == "No Vaydeer device detected"
    assert controller.keys == []


def test_controller_recovers_after_startup_race_and_same_node_replug(monkeypatch) -> None:
    visible: list[HidInterface] = []
    monkeypatch.setattr(controller_module, "discover_linux_hidraw", lambda: visible)
    monkeypatch.setattr(controller_module, "open_command_transport", lambda _path: MockJP1011Transport())
    monkeypatch.setattr(controller_module, "service_request", _active_service)
    controller = StudioController(mock=False)
    if controller._health_timer is not None:
        controller._health_timer.stop()

    assert controller.connection["state"] == "no_device"
    visible[:] = _interfaces("1-2:1.0")
    controller._monitor_device_connection()
    assert controller.connection["state"] == "connected"

    visible.clear()
    controller._monitor_device_connection()
    assert controller.connection["state"] == "device_disconnected"
    assert controller.keys == []

    visible[:] = _interfaces("1-2:1.1")
    controller._monitor_device_connection()
    assert controller.connection["state"] == "connected"
    assert [item["label"] for item in controller.keys][:3] == ["Num 7", "Num 8", "Num 9"]


def test_controller_distinguishes_command_permission_and_protocol_failures(monkeypatch) -> None:
    visible = _interfaces("1-2:1.0")
    monkeypatch.setattr(controller_module, "discover_linux_hidraw", lambda: visible)
    monkeypatch.setattr(controller_module, "service_request", _active_service)
    monkeypatch.setattr(
        controller_module,
        "open_command_transport",
        lambda _path: (_ for _ in ()).throw(DeviceError("Permission denied opening Vaydeer command interface")),
    )
    denied = StudioController(mock=False)
    if denied._health_timer is not None:
        denied._health_timer.stop()
    assert denied.connection["state"] == "permission_denied"

    class BrokenTransport:
        def transact(self, _report: bytes, _timeout_ms: int) -> bytes:
            return b""

        def close(self) -> None:
            return None

    monkeypatch.setattr(controller_module, "open_command_transport", lambda _path: BrokenTransport())
    failed = StudioController(mock=False)
    if failed._health_timer is not None:
        failed._health_timer.stop()
    assert failed.connection["state"] == "protocol_failed"


def test_connected_controller_explains_keepalive_service_failure(monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "discover_linux_hidraw", lambda: _interfaces("1-2:1.0"))
    monkeypatch.setattr(controller_module, "open_command_transport", lambda _path: MockJP1011Transport())
    monkeypatch.setattr(
        controller_module,
        "service_request",
        lambda _path, _request: (_ for _ in ()).throw(OSError("service unavailable")),
    )
    controller = StudioController(mock=False)
    if controller._health_timer is not None:
        controller._health_timer.stop()

    assert controller.connection["state"] == "connected"
    assert "Interface-2 keepalive is Service unavailable" in controller.device["warning"]


def test_real_controller_relays_tester_events_from_service(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    responses = iter(
        [
            {"ok": True, "result": {"keepalive": {"state": "active_readonly"}}},
            {"ok": True, "result": {"keepalive": {"state": "active_readonly"}, "tester_active": True}},
            {
                "ok": True,
                "result": {
                    "keepalive": {"state": "active_readonly"},
                    "events": [
                        {
                            "timestamp": "12:34:56.789",
                            "key_index": 4,
                            "layer_index": 0,
                            "pressed": True,
                            "raw": "fb 03 00 04 00 fc",
                        }
                    ],
                },
            },
            {"ok": True, "result": {"keepalive": {"state": "active_readonly"}, "tester_active": False}},
        ]
    )
    monkeypatch.setattr(controller_module, "discover_linux_hidraw", lambda: _interfaces("1-2:1.0"))
    monkeypatch.setattr(controller_module, "open_command_transport", lambda _path: MockJP1011Transport())

    def service_request(_path, payload):
        calls.append(payload)
        return next(responses)

    monkeypatch.setattr(controller_module, "service_request", service_request)
    controller = StudioController(mock=False)
    if controller._health_timer is not None:
        controller._health_timer.stop()
    controller.setTesterOpen(True)
    controller._poll_tester_events()

    assert controller.testerEvents[0] == {
        "timestamp": "12:34:56.789",
        "key": 5,
        "event": "Press",
        "layer": 1,
        "raw": "fb 03 00 04 00 fc",
    }
    controller.setTesterOpen(False)
    assert controller.testerEvents == []
    assert [item["method"] for item in calls] == ["status", "set_tester", "drain_tester_events", "set_tester"]
