"""The single configuration-write path used by both CLI and desktop UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vaydeer_studio.devices.capabilities import DeviceCapability, capability_for
from vaydeer_studio.protocol.client import VaydeerProtocol

from .backup import BackupStore
from .diff import DiffItem, snapshot_diff
from .errors import CapabilityError, PartialWriteError, SafetyConfirmationRequired, VerificationError
from .models import DeviceSnapshot


@dataclass(frozen=True)
class ApplyPreview:
    current: DeviceSnapshot
    proposed: DeviceSnapshot
    backup_path: Path
    capability: DeviceCapability
    diff: tuple[DiffItem, ...]
    packets: tuple[bytes, ...]


@dataclass(frozen=True)
class ApplyResult:
    preview: ApplyPreview
    verified: DeviceSnapshot


def prepare_apply(protocol: VaydeerProtocol, proposed: DeviceSnapshot, backups: BackupStore) -> ApplyPreview:
    """Re-read the device, validate write capability, persist a backup, and build a dry-run."""

    current = protocol.read_snapshot()
    capability = capability_for(current.device)
    if not capability.writable:
        raise CapabilityError(capability.reason)
    if current.device.key_count != proposed.device.key_count:
        raise CapabilityError(
            f"Proposed profile expects {proposed.device.key_count} keys; device reports {current.device.key_count}"
        )
    if proposed.device.firmware != current.device.firmware or proposed.device.bootloader != current.device.bootloader:
        raise CapabilityError("Proposed snapshot does not match the connected firmware capability record")
    if any(not assignment.transmit_supported for layer in proposed.layers for assignment in layer.assignments):
        raise CapabilityError("Profile contains experimental or service-only assignments in the on-device mapping")
    backup_path = backups.create(current)
    packets = protocol.preview_write_packets(proposed)
    return ApplyPreview(
        current=current,
        proposed=proposed,
        backup_path=backup_path,
        capability=capability,
        diff=tuple(snapshot_diff(current, proposed)),
        packets=tuple(packets),
    )


def apply_prepared(protocol: VaydeerProtocol, preview: ApplyPreview, *, confirmed: bool) -> ApplyResult:
    """Apply one previously reviewed plan and prove it by reading it back."""

    if not confirmed:
        raise SafetyConfirmationRequired("Configuration remains a dry run until explicitly confirmed")
    maximum_layer_index = max(0, preview.current.device.max_layers - 1)
    current_layer: int | None = None
    try:
        for layer in preview.proposed.layers:
            current_layer = layer.index
            protocol.write_layer_name(layer.index, maximum_layer_index, layer.name)
            for key_index in range(preview.current.device.key_count):
                protocol.write_key_assignment(layer.index, layer.assignment_for(key_index))
            protocol.commit_layer(layer.index, maximum_layer_index)
    except Exception as error:
        location = "before any layer was committed" if current_layer is None else f"while writing layer {current_layer}"
        raise PartialWriteError(
            f"Configuration write stopped {location}. Backup remains at {preview.backup_path}: {error}"
        ) from error
    verified = protocol.read_snapshot()
    differences = snapshot_diff(preview.proposed, verified)
    if differences:
        detail = "; ".join(change.describe() for change in differences[:4])
        raise VerificationError(
            f"Device read-back did not match the proposed mapping. Backup remains at {preview.backup_path}. {detail}"
        )
    return ApplyResult(preview=preview, verified=verified)


def safe_apply(
    protocol: VaydeerProtocol, proposed: DeviceSnapshot, backups: BackupStore, *, confirmed: bool
) -> ApplyResult | ApplyPreview:
    preview = prepare_apply(protocol, proposed, backups)
    return apply_prepared(protocol, preview, confirmed=True) if confirmed else preview


def packet_lines(packets: tuple[bytes, ...]) -> list[str]:
    """Compact, exact packet display for terminal confirmation without a raw sender."""

    return [" ".join(f"{byte:02x}" for byte in packet.rstrip(bytes([0]))) for packet in packets]
