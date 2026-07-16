"""Declarative physical layouts kept outside the protocol implementation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class LayoutKey:
    index: int
    row: int
    column: int
    label: str


@dataclass(frozen=True)
class KeypadLayout:
    id: str
    title: str
    key_count: int
    rows: int
    columns: int
    verified: bool
    keys: tuple[LayoutKey, ...]


def load_layout(layout_id: str) -> KeypadLayout:
    path = files("vaydeer_studio.resources.layouts").joinpath(f"{layout_id}.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return KeypadLayout(
        id=raw["id"],
        title=raw["title"],
        key_count=raw["key_count"],
        rows=raw["rows"],
        columns=raw["columns"],
        verified=raw["verified"],
        keys=tuple(LayoutKey(**item) for item in raw["keys"]),
    )


def layout_for_key_count(key_count: int) -> KeypadLayout:
    lookup = {1: "generic-1", 4: "generic-4", 6: "generic-6", 9: "jp1011-9"}
    return load_layout(lookup.get(key_count, "generic-1"))
