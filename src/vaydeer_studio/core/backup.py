"""XDG-backed, open JSON backup persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_data_path

from .models import DeviceSnapshot

BACKUP_SCHEMA_VERSION = 1


class BackupStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (user_data_path("Vaydeer Studio", "Vaydeer Studio") / "backups")

    def create(self, snapshot: DeviceSnapshot) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        name = f"jp-{snapshot.device.key_count}key-{snapshot.device.firmware_version}-{timestamp}.json"
        path = self.root / name
        suffix = 1
        while path.exists():
            path = self.root / f"{path.stem}-{suffix}{path.suffix}"
            suffix += 1
        payload = {"backup_schema_version": BACKUP_SCHEMA_VERSION, "snapshot": snapshot.model_dump(mode="json")}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def load(self, path: Path) -> DeviceSnapshot:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("backup_schema_version") != BACKUP_SCHEMA_VERSION:
            raise ValueError("Unsupported backup schema version")
        return DeviceSnapshot.model_validate(payload["snapshot"])

    def list(self) -> list[Path]:
        return sorted(self.root.glob("*.json"), reverse=True) if self.root.exists() else []
