"""Non-destructive Linux hardware diagnostics for Vaydeer Studio."""

from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from vaydeer_studio import __version__
from vaydeer_studio.core.errors import DeviceError
from vaydeer_studio.protocol.client import VaydeerProtocol
from vaydeer_studio.service.daemon import default_socket_path
from vaydeer_studio.service.daemon import request as service_request

from .capabilities import capability_for
from .discovery import HidInterface, discover_linux_hidraw, select_command_interface, select_keepalive_interface
from .transport import open_command_transport

UDEV_RULE_PATH = Path("/etc/udev/rules.d/99-vaydeer-studio.rules")
USER_UNIT_PATH = Path.home() / ".config/systemd/user/vaydeer-studio.service"


@dataclass(frozen=True)
class DiagnosticCheck:
    id: str
    status: str
    summary: str
    detail: str = ""


@dataclass(frozen=True)
class InterfaceDiagnostic:
    node: str
    interface_number: int | None
    usage_page: int | None
    usage: int | None
    role: str
    mode: str | None
    owner: str | None
    group: str | None
    acl_present: bool | None
    readable: bool | None
    writable: bool | None
    descriptor: str | None


@dataclass(frozen=True)
class DiagnosticReport:
    app_version: str
    host: dict[str, str]
    interfaces: list[InterfaceDiagnostic]
    checks: list[DiagnosticCheck]
    service: dict[str, Any]
    protocol: dict[str, Any]
    root_cause: str
    recommended_actions: list[str]
    ready: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


ProtocolFactory = Callable[[str], Any]
Discovery = Callable[[], list[HidInterface]]


def collect_diagnostics(
    *,
    discover: Discovery = discover_linux_hidraw,
    transport_factory: ProtocolFactory = open_command_transport,
    include_protocol: bool = True,
    verbose: bool = False,
) -> DiagnosticReport:
    """Inspect only known Vaydeer interfaces and optionally send a safe `0x60` read."""

    interfaces = [item for item in discover() if item.is_vaydeer]
    command = select_command_interface(interfaces)
    keepalive = select_keepalive_interface(interfaces)
    reports = [_interface_diagnostic(item, verbose=verbose) for item in interfaces]
    checks: list[DiagnosticCheck] = []
    checks.append(
        DiagnosticCheck(
            "device",
            "pass" if interfaces else "fail",
            "Vaydeer VID:PID is visible" if interfaces else "No Vaydeer 0483:5752 device is visible",
        )
    )
    checks.extend(_interface_checks(command, keepalive, reports))
    udev_installed = UDEV_RULE_PATH.exists()
    unit_installed = USER_UNIT_PATH.exists()
    checks.append(
        DiagnosticCheck(
            "udev_rule",
            "pass" if udev_installed else "warn",
            "Vaydeer udev rule is installed" if udev_installed else "Vaydeer udev rule is not installed",
        )
    )
    service = _service_status(unit_installed)
    checks.append(
        DiagnosticCheck(
            "user_service",
            "pass" if service["available"] else "warn",
            "Vaydeer keepalive service is reachable"
            if service["available"]
            else service["summary"],
        )
    )
    protocol = _probe_protocol(command, reports, transport_factory) if include_protocol else {"attempted": False}
    if include_protocol:
        checks.append(
            DiagnosticCheck(
                "protocol",
                "pass" if protocol.get("ok") else "fail",
                (
                    "Device information read succeeded"
                    if protocol.get("ok")
                    else str(protocol.get("error", "Not attempted"))
                ),
            )
        )
        if protocol.get("ok"):
            checks.append(
                DiagnosticCheck(
                    "firmware",
                    "pass" if protocol["writable"] else "warn",
                    str(protocol["capability_reason"]),
                )
            )
    root_cause = _root_cause(command, keepalive, reports, service, protocol)
    recommendations = _recommended_actions(root_cause)
    required = {
        "device",
        "command_interface",
        "keepalive_interface",
        "command_access",
        "keepalive_access",
        "user_service",
        "protocol",
    }
    ready = all(check.status == "pass" for check in checks if check.id in required)
    return DiagnosticReport(
        app_version=__version__,
        host={
            "system": platform.system(),
            "kernel": platform.release(),
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            "mock_mode_environment": "set" if os.environ.get("VAYDEER_STUDIO_MOCK") else "not_set",
        },
        interfaces=reports,
        checks=checks,
        service=service,
        protocol=protocol,
        root_cause=root_cause,
        recommended_actions=recommendations,
        ready=ready,
    )


def render_report(report: DiagnosticReport, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(report.as_dict(), indent=2, sort_keys=True)
    lines = [f"Vaydeer Studio {report.app_version} diagnostics", f"Root cause: {report.root_cause}"]
    for check in report.checks:
        lines.append(f"[{check.status.upper()}] {check.summary}")
    if report.protocol.get("ok"):
        lines.append(
            "Device: {model}, firmware {firmware}, bootloader {bootloader}".format(
                model=report.protocol["model"],
                firmware=report.protocol["firmware"],
                bootloader=report.protocol["bootloader"],
            )
        )
    if report.recommended_actions:
        lines.append("Recommended recovery:")
        lines.extend(f"  {action}" for action in report.recommended_actions)
    return "\n".join(lines)


def _interface_diagnostic(interface: HidInterface, *, verbose: bool) -> InterfaceDiagnostic:
    mode: str | None
    owner: str | None
    group: str | None
    try:
        metadata = os.stat(interface.path)
        mode = stat.filemode(metadata.st_mode)
        owner = _name_for_uid(metadata.st_uid)
        group = _name_for_gid(metadata.st_gid)
        acl_present = _has_extended_acl(interface.path)
    except OSError:
        mode = owner = group = None
        acl_present = None
    read_flags = os.O_RDONLY | os.O_CLOEXEC
    readable = _can_open(interface.path, read_flags)
    writable = _can_open(interface.path, os.O_RDWR | os.O_CLOEXEC) if interface.interface_number == 0 else None
    role = _role_for(interface)
    return InterfaceDiagnostic(
        node=interface.path,
        interface_number=interface.interface_number,
        usage_page=interface.usage_page,
        usage=interface.usage,
        role=role,
        mode=mode,
        owner=owner,
        group=group,
        acl_present=acl_present,
        readable=readable,
        writable=writable,
        descriptor=interface.report_descriptor.hex() if verbose else None,
    )


def _interface_checks(
    command: HidInterface | None,
    keepalive: HidInterface | None,
    reports: list[InterfaceDiagnostic],
) -> list[DiagnosticCheck]:
    lookup = {item.node: item for item in reports}
    command_report = lookup.get(command.path) if command else None
    keepalive_report = lookup.get(keepalive.path) if keepalive else None
    return [
        DiagnosticCheck(
            "command_interface",
            "pass" if command else "fail",
            "Vendor command interface 0 is matched" if command else "Vendor command interface 0 is missing",
        ),
        DiagnosticCheck(
            "keepalive_interface",
            "pass" if keepalive else "fail",
            "Vendor event interface 2 is matched" if keepalive else "Vendor event interface 2 is missing",
        ),
        DiagnosticCheck(
            "command_access",
            "pass" if command_report and command_report.writable else "fail",
            "Normal-user read/write access to command interface is available"
            if command_report and command_report.writable
            else "Normal-user access to command interface is unavailable",
        ),
        DiagnosticCheck(
            "keepalive_access",
            "pass" if keepalive_report and keepalive_report.readable else "fail",
            "Normal-user read-only access to keepalive interface is available"
            if keepalive_report and keepalive_report.readable
            else "Normal-user access to keepalive interface is unavailable",
        ),
    ]


def _probe_protocol(
    command: HidInterface | None,
    reports: list[InterfaceDiagnostic],
    transport_factory: ProtocolFactory,
) -> dict[str, Any]:
    report_lookup = {item.node: item for item in reports}
    if command is None:
        return {"attempted": False, "ok": False, "error": "Command interface is not matched"}
    if not report_lookup[command.path].writable:
        return {"attempted": False, "ok": False, "error": "Command interface is not accessible"}
    transport: Any | None = None
    try:
        transport = transport_factory(command.path)
        protocol = VaydeerProtocol(transport)
        info = protocol.read_device_info()
        capability = capability_for(info)
        return {
            "attempted": True,
            "ok": True,
            "model": capability.model,
            "firmware": info.firmware_version,
            "bootloader": info.bootloader_version,
            "key_count": info.key_count,
            "writable": capability.writable,
            "capability_reason": capability.reason,
            "transport": "linux_hidraw",
        }
    except (DeviceError, OSError) as error:
        return {"attempted": True, "ok": False, "error": str(error), "transport": "linux_hidraw"}
    finally:
        if transport is not None:
            transport.close()


def _service_status(unit_installed: bool) -> dict[str, Any]:
    status: dict[str, Any] = {
        "unit_installed": unit_installed,
        "available": False,
        "socket": "unavailable",
        "summary": (
            "Vaydeer keepalive service is not installed"
            if not unit_installed
            else "Vaydeer keepalive service is unavailable"
        ),
    }
    try:
        response = service_request(default_socket_path(), {"method": "status"})
        if response.get("ok"):
            status.update({"available": True, "socket": "connected", "summary": "Keepalive service is reachable"})
            status["runtime"] = response.get("result", {})
    except OSError:
        pass
    return status


def _root_cause(
    command: HidInterface | None,
    keepalive: HidInterface | None,
    reports: list[InterfaceDiagnostic],
    service: dict[str, Any],
    protocol: dict[str, Any],
) -> str:
    if not reports:
        return "no_vaydeer_device"
    lookup = {item.node: item for item in reports}
    if command is None:
        return "command_interface_missing"
    if keepalive is None:
        return "keepalive_interface_missing"
    if not lookup[command.path].writable:
        return "command_permission_denied"
    if not lookup[keepalive.path].readable:
        return "keepalive_permission_denied"
    if protocol.get("attempted") and not protocol.get("ok"):
        return "protocol_initialization_failed"
    if not service["unit_installed"]:
        return "keepalive_service_not_installed"
    if not service["available"]:
        return "keepalive_service_unavailable"
    if protocol.get("ok") and not protocol.get("writable"):
        return "unsupported_firmware_read_only"
    return "ready"


def _recommended_actions(root_cause: str) -> list[str]:
    actions = {
        "no_vaydeer_device": ["Reconnect the keypad, then run: vaydeer-studio-cli doctor"],
        "command_interface_missing": ["Reconnect the keypad; verify USB interface 0 in diagnostics."],
        "keepalive_interface_missing": ["Reconnect the keypad; verify USB interface 2 in diagnostics."],
        "command_permission_denied": [
            "Run ./scripts/install.sh, reconnect the keypad, then log out and back in if needed."
        ],
        "keepalive_permission_denied": [
            "Run ./scripts/install.sh, reconnect the keypad, then log out and back in if needed."
        ],
        "protocol_initialization_failed": [
            "Run vaydeer-studio-cli diagnostics --verbose and inspect the USB connection."
        ],
        "keepalive_service_not_installed": [
            "Run ./scripts/install.sh",
            "Then run: systemctl --user status vaydeer-studio.service",
        ],
        "keepalive_service_unavailable": ["Run: systemctl --user restart vaydeer-studio.service"],
        "unsupported_firmware_read_only": [
            "Inspection and export are safe; hardware writes remain disabled for this firmware."
        ],
    }
    return actions.get(root_cause, [])


def _role_for(interface: HidInterface) -> str:
    if interface.interface_number == 0:
        return "vendor_command"
    if interface.interface_number == 2:
        return "vendor_keepalive"
    if interface.interface_number == 1:
        return "keyboard"
    if interface.interface_number == 3:
        return "mouse_consumer_system"
    return "unknown"


def _can_open(path: str, flags: int) -> bool:
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return False
    os.close(descriptor)
    return True


def _has_extended_acl(path: str) -> bool | None:
    try:
        result = subprocess.run(["getfacl", "-cp", path], check=False, capture_output=True, text=True)
    except OSError:
        return None
    entries = result.stdout.splitlines()
    return result.returncode == 0 and any(
        line.startswith("user:") and not line.startswith("user::") for line in entries
    )


def _name_for_uid(value: int) -> str:
    import pwd

    try:
        return pwd.getpwuid(value).pw_name
    except KeyError:
        return str(value)


def _name_for_gid(value: int) -> str:
    import grp

    try:
        return grp.getgrgid(value).gr_name
    except KeyError:
        return str(value)
