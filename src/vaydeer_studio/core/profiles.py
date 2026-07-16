"""Profile import/export with JSON and YAML support."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from platformdirs import user_data_path

from .models import Profile


def load_profile(path: Path) -> Profile:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    return Profile.model_validate(data)


def save_profile(profile: Profile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    if path.suffix.lower() in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_for_device(profile: Profile, *, key_count: int, model: str) -> list[str]:
    issues: list[str] = []
    if profile.key_count != key_count:
        issues.append(f"Profile expects {profile.key_count} keys; device reports {key_count}")
    if profile.device_model not in {model, "Generic"}:
        issues.append(f"Profile targets {profile.device_model}; connected device is {model}")
    return issues


class ProfileStore:
    """Small XDG-backed profile library using the portable profile schema."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or user_data_path("Vaydeer Studio", "Vaydeer Studio") / "profiles"

    def path_for(self, profile_id: str) -> Path:
        safe_id = "".join(character for character in profile_id if character.isalnum() or character in {"-", "_"})
        if not safe_id:
            raise ValueError("Profile id must contain a letter or number")
        return self.root / f"{safe_id}.json"

    def save(self, profile: Profile) -> Path:
        path = self.path_for(profile.id)
        save_profile(profile, path)
        return path

    def load(self, profile_id: str) -> Profile:
        return load_profile(self.path_for(profile_id))

    def delete(self, profile_id: str) -> None:
        self.path_for(profile_id).unlink(missing_ok=True)
        if self.active_id() == profile_id:
            self.active_path.unlink(missing_ok=True)

    def list(self) -> list[Profile]:
        if not self.root.exists():
            return []
        profiles: list[Profile] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                profiles.append(load_profile(path))
            except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError):
                continue
        return profiles

    @property
    def active_path(self) -> Path:
        return self.root / "active-profile"

    def set_active(self, profile_id: str) -> None:
        if not self.path_for(profile_id).exists():
            raise FileNotFoundError(f"Profile {profile_id!r} is not in the local library")
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_path.write_text(f"{profile_id}\n", encoding="utf-8")

    def active_id(self) -> str | None:
        try:
            value = self.active_path.read_text(encoding="utf-8").strip()
            self.path_for(value)
            return value
        except (OSError, ValueError):
            return None

    def load_active(self) -> Profile | None:
        profile_id = self.active_id()
        if profile_id is None:
            return None
        try:
            return self.load(profile_id)
        except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError):
            return None
