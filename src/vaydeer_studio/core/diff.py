"""Human-readable configuration differences for confirmation screens."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DeviceSnapshot, Layer


@dataclass(frozen=True)
class DiffItem:
    layer_index: int
    key_index: int | None
    before: str
    after: str
    kind: str

    def describe(self) -> str:
        location = f"Layer {self.layer_index}"
        if self.key_index is not None:
            location += f", key {self.key_index + 1}"
        return f"{location}: {self.before} -> {self.after}"


def snapshot_diff(before: DeviceSnapshot, after: DeviceSnapshot) -> list[DiffItem]:
    """Compare layers by vendor index and keys by zero-based physical index."""

    changes: list[DiffItem] = []
    before_layers = {layer.index: layer for layer in before.layers}
    after_layers = {layer.index: layer for layer in after.layers}
    for layer_index in sorted(set(before_layers) | set(after_layers)):
        old = before_layers.get(layer_index)
        new = after_layers.get(layer_index)
        changes.extend(_layer_diff(layer_index, old, new))
    return changes


def _layer_diff(layer_index: int, before: Layer | None, after: Layer | None) -> list[DiffItem]:
    if before is None:
        return [DiffItem(layer_index, None, "Absent", after.name if after else "Absent", "layer")]
    if after is None:
        return [DiffItem(layer_index, None, before.name, "Absent", "layer")]
    output: list[DiffItem] = []
    if before.name != after.name:
        output.append(DiffItem(layer_index, None, before.name, after.name, "layer_name"))
    before_keys = {item.key_index: item for item in before.assignments}
    after_keys = {item.key_index: item for item in after.assignments}
    for key_index in sorted(set(before_keys) | set(after_keys)):
        old = before_keys.get(key_index)
        new = after_keys.get(key_index)
        old_name = old.display_name if old else "Disabled"
        new_name = new.display_name if new else "Disabled"
        if old is None or new is None or old.model_dump() != new.model_dump():
            output.append(DiffItem(layer_index, key_index, old_name, new_name, "assignment"))
    return output


def format_diff(changes: list[DiffItem]) -> str:
    return "No changes." if not changes else "\n".join(item.describe() for item in changes)
