from __future__ import annotations

from pathlib import Path

from vaydeer_studio.devices import diagnostics
from vaydeer_studio.devices.diagnostics import InterfaceDiagnostic, collect_diagnostics, render_report
from vaydeer_studio.devices.discovery import COMMAND_USAGE, EVENT_USAGE, VENDOR_USAGE_PAGE, HidInterface


def _interfaces(serial: str = "private-device-serial") -> list[HidInterface]:
    return [
        HidInterface("/dev/hidraw18", 0x0483, 0x5752, 0, VENDOR_USAGE_PAGE, COMMAND_USAGE, serial=serial),
        HidInterface("/dev/hidraw21", 0x0483, 0x5752, 2, VENDOR_USAGE_PAGE, EVENT_USAGE, serial=serial),
    ]


def _interface_report(interface: HidInterface, *, verbose: bool) -> InterfaceDiagnostic:
    return InterfaceDiagnostic(
        node=interface.path,
        interface_number=interface.interface_number,
        usage_page=interface.usage_page,
        usage=interface.usage,
        role="vendor_command" if interface.interface_number == 0 else "vendor_keepalive",
        mode="crw-rw----",
        owner="root",
        group="plugdev",
        acl_present=True,
        readable=True,
        writable=True if interface.interface_number == 0 else None,
        descriptor="0600ff0901" if verbose else None,
    )


def test_diagnostics_reports_missing_device_without_personal_metadata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(diagnostics, "UDEV_RULE_PATH", tmp_path / "missing-rule")
    monkeypatch.setattr(diagnostics, "USER_UNIT_PATH", tmp_path / "missing-unit")
    monkeypatch.setattr(
        diagnostics,
        "_service_status",
        lambda _installed: {"available": False, "unit_installed": False, "summary": "not installed"},
    )

    report = collect_diagnostics(discover=lambda: [], include_protocol=False)

    assert report.root_cause == "no_vaydeer_device"
    assert not report.ready
    assert "private-device-serial" not in render_report(report, as_json=True)
    assert report.recommended_actions == ["Reconnect the keypad, then run: vaydeer-studio-cli doctor"]


def test_diagnostics_marks_unknown_firmware_as_read_only_without_exposing_serial(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "99-vaydeer-studio.rules").touch()
    (tmp_path / "vaydeer-studio.service").touch()
    monkeypatch.setattr(diagnostics, "UDEV_RULE_PATH", tmp_path / "99-vaydeer-studio.rules")
    monkeypatch.setattr(diagnostics, "USER_UNIT_PATH", tmp_path / "vaydeer-studio.service")
    monkeypatch.setattr(diagnostics, "_interface_diagnostic", _interface_report)
    monkeypatch.setattr(
        diagnostics,
        "_service_status",
        lambda _installed: {"available": True, "unit_installed": True, "summary": "reachable"},
    )
    monkeypatch.setattr(
        diagnostics,
        "_probe_protocol",
        lambda *_args: {
            "attempted": True,
            "ok": True,
            "model": "Unknown Vaydeer keypad",
            "firmware": "9.9.9",
            "bootloader": "9.9.9",
            "key_count": 9,
            "writable": False,
            "capability_reason": "Unknown firmware",
            "transport": "linux_hidraw",
        },
    )

    report = collect_diagnostics(discover=_interfaces)

    assert report.root_cause == "unsupported_firmware_read_only"
    assert report.ready
    assert "private-device-serial" not in render_report(report, as_json=True)
    assert "Inspection and export are safe" in render_report(report, as_json=False)
