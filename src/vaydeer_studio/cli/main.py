"""Safe command line companion for Vaydeer Studio."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from vaydeer_studio import __version__
from vaydeer_studio.core.backup import BackupStore
from vaydeer_studio.core.diff import format_diff
from vaydeer_studio.core.logging import configure_logging
from vaydeer_studio.core.models import DeviceSnapshot, Profile
from vaydeer_studio.core.profiles import load_profile, validate_for_device
from vaydeer_studio.core.safety import ApplyPreview, apply_prepared, packet_lines, prepare_apply
from vaydeer_studio.devices.capabilities import capability_for
from vaydeer_studio.devices.diagnostics import collect_diagnostics, render_report
from vaydeer_studio.devices.discovery import discover_linux_hidraw, select_command_interface
from vaydeer_studio.devices.mock import MockJP1011Transport
from vaydeer_studio.devices.transport import open_command_transport
from vaydeer_studio.protocol.client import VaydeerProtocol
from vaydeer_studio.service.keepalive import KeepaliveManager


def _protocol(mock: bool) -> VaydeerProtocol:
    if mock:
        return VaydeerProtocol(MockJP1011Transport())
    interface = select_command_interface(discover_linux_hidraw())
    if interface is None:
        raise RuntimeError("No Vaydeer command interface found. Check permissions and reconnect the keypad.")
    return VaydeerProtocol(open_command_transport(interface.path))


def _snapshot_for_profile(profile: Profile, current: DeviceSnapshot) -> DeviceSnapshot:
    return profile.to_snapshot(current.device)


def _print_snapshot(snapshot: DeviceSnapshot) -> None:
    print(json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True))


def _print_preview(preview: ApplyPreview) -> None:
    print(f"Backup: {preview.backup_path}")
    print("Current mapping:")
    print(
        format_diff([]) if not preview.current.layers else json.dumps(preview.current.model_dump(mode="json"), indent=2)
    )
    print("Proposed mapping:")
    print(json.dumps(preview.proposed.model_dump(mode="json"), indent=2))
    print("Diff:")
    print(format_diff(list(preview.diff)))
    print("Exact HID commands:")
    for line in packet_lines(preview.packets):
        print(line)


def cmd_list_devices(args: argparse.Namespace) -> int:
    if args.mock:
        print("mock: Vaydeer JP-1011, 9 keys, firmware 1.0.2, bootloader 0.2.1")
        return 0
    for interface in discover_linux_hidraw():
        if interface.is_vaydeer:
            print(
                f"{interface.path}: interface={interface.interface_number} "
                f"usage=0x{interface.usage_page or 0:04x}/0x{interface.usage or 0:04x}"
            )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    protocol = _protocol(args.mock)
    try:
        snapshot = protocol.read_snapshot()
        capability = capability_for(snapshot.device)
        _print_snapshot(snapshot)
        print(f"write capability: {'enabled' if capability.writable else 'read-only'} ({capability.reason})")
        return 0
    finally:
        protocol.close()


def cmd_backup(args: argparse.Namespace) -> int:
    protocol = _protocol(args.mock)
    try:
        path = BackupStore().create(protocol.read_snapshot())
        print(path)
        return 0
    finally:
        protocol.close()


def cmd_read_config(args: argparse.Namespace) -> int:
    protocol = _protocol(args.mock)
    try:
        _print_snapshot(protocol.read_snapshot())
        return 0
    finally:
        protocol.close()


def cmd_validate_profile(args: argparse.Namespace) -> int:
    profile = load_profile(Path(args.profile))
    protocol = _protocol(args.mock)
    try:
        info = protocol.read_device_info()
        issues = validate_for_device(profile, key_count=info.key_count, model=capability_for(info).model)
    finally:
        protocol.close()
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 2
    print(f"Profile {profile.name!r} is compatible with the detected {info.key_count}-key device.")
    return 0


def _preview_profile(args: argparse.Namespace) -> tuple[VaydeerProtocol, ApplyPreview]:
    profile = load_profile(Path(args.profile))
    protocol = _protocol(args.mock)
    current = protocol.read_snapshot()
    preview = prepare_apply(protocol, _snapshot_for_profile(profile, current), BackupStore())
    return protocol, preview


def cmd_dry_run(args: argparse.Namespace) -> int:
    protocol, preview = _preview_profile(args)
    try:
        _print_preview(preview)
        return 0
    finally:
        protocol.close()


def _confirm_real_write() -> bool:
    try:
        return input("Type APPLY to write the connected Vaydeer keypad: ").strip() == "APPLY"
    except EOFError:
        return False


def cmd_apply_profile(args: argparse.Namespace) -> int:
    protocol, preview = _preview_profile(args)
    try:
        _print_preview(preview)
        if not args.mock:
            if not args.confirm_real_write:
                print(
                    "Real hardware was not changed. Re-run with --confirm-real-write to request terminal confirmation."
                )
                return 3
            if not _confirm_real_write():
                print("Real hardware was not changed.")
                return 3
        result = apply_prepared(protocol, preview, confirmed=True)
        print(f"Write verified. Backup preserved at {result.preview.backup_path}")
        return 0
    finally:
        protocol.close()


def cmd_restore_backup(args: argparse.Namespace) -> int:
    snapshot = BackupStore().load(Path(args.backup))
    protocol = _protocol(args.mock)
    try:
        preview = prepare_apply(protocol, snapshot, BackupStore())
        _print_preview(preview)
        if not args.mock and (not args.confirm_real_write or not _confirm_real_write()):
            print("Real hardware was not changed.")
            return 3
        apply_prepared(protocol, preview, confirmed=True)
        print("Backup restore verified.")
        return 0
    finally:
        protocol.close()


def cmd_keepalive(args: argparse.Namespace) -> int:
    if args.status:
        report = collect_diagnostics(include_protocol=False, verbose=args.verbose)
        print(json.dumps(report.service, indent=2, default=str))
        return 0 if report.service["available"] else 2
    manager = KeepaliveManager()
    manager.run_for(args.seconds)
    print(json.dumps(manager.status(), indent=2))
    return 0


def cmd_diagnostics(args: argparse.Namespace) -> int:
    report = collect_diagnostics(verbose=args.verbose)
    print(render_report(report, as_json=args.json))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report = collect_diagnostics(verbose=args.verbose)
    print(render_report(report, as_json=args.json))
    return 0 if report.ready and report.root_cause in {"ready", "unsupported_firmware_read_only"} else 2


def cmd_service_status(args: argparse.Namespace) -> int:
    report = collect_diagnostics(include_protocol=False, verbose=args.verbose)
    print(json.dumps(report.service, indent=2, default=str) if args.json else report.service["summary"])
    return 0 if report.service["available"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vaydeer-studio-cli", description=__doc__)
    parser.add_argument("--version", action="version", version=f"Vaydeer Studio CLI {__version__}")
    parser.add_argument("--mock", action="store_true", help="Use the in-memory JP-1011 device.")
    parser.add_argument("--verbose", action="store_true", help="Enable safe structured diagnostic logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands: list[tuple[str, Callable[[argparse.Namespace], int], bool]] = [
        ("list-devices", cmd_list_devices, False),
        ("inspect", cmd_inspect, False),
        ("backup", cmd_backup, False),
        ("read-config", cmd_read_config, False),
        ("diagnostics", cmd_diagnostics, False),
        ("doctor", cmd_doctor, False),
        ("service-status", cmd_service_status, False),
        ("keepalive", cmd_keepalive, False),
        ("validate-profile", cmd_validate_profile, True),
        ("dry-run", cmd_dry_run, True),
        ("apply-profile", cmd_apply_profile, True),
        ("restore-backup", cmd_restore_backup, True),
    ]
    for name, handler, needs_path in commands:
        command = subparsers.add_parser(name)
        command.set_defaults(handler=handler)
        if needs_path:
            command.add_argument("profile" if name != "restore-backup" else "backup")
        if name in {"apply-profile", "restore-backup"}:
            command.add_argument("--confirm-real-write", action="store_true")
        if name == "keepalive":
            command.add_argument("--seconds", type=float, default=0.0)
            command.add_argument("--status", action="store_true")
        if name in {"diagnostics", "doctor", "service-status"}:
            command.add_argument("--json", action="store_true", help="Emit sanitized JSON.")
            command.add_argument(
                "--sanitize",
                action="store_true",
                help="Explicitly request sanitized output (the default never includes serials or home paths).",
            )
            command.add_argument(
                "--verbose",
                action="store_true",
                default=argparse.SUPPRESS,
                help="Include report descriptors and debug logging.",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(verbose=bool(args.verbose))
    try:
        return int(args.handler(args))
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
