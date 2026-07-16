"""Linux-side action execution with secure argv defaults and mock observability."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from vaydeer_studio.core.models import LinuxActionKind, LinuxBinding


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    argv: tuple[str, ...]
    message: str


class BindingExecutor:
    def __init__(self, *, mock_mode: bool = False, launcher: Callable[..., object] = subprocess.Popen) -> None:
        self.mock_mode = mock_mode
        self._launcher = launcher
        self.history: list[ExecutionResult] = []

    def execute(self, binding: LinuxBinding) -> ExecutionResult:
        argv = self.argv_for(binding)
        if self.mock_mode:
            result = ExecutionResult(True, tuple(argv), "Mock execution recorded")
            self.history.append(result)
            return result
        try:
            self._launcher(argv, start_new_session=True)
        except OSError as error:
            result = ExecutionResult(False, tuple(argv), str(error))
            self.history.append(result)
            return result
        result = ExecutionResult(True, tuple(argv), "Started")
        self.history.append(result)
        return result

    def argv_for(self, binding: LinuxBinding) -> list[str]:
        if binding.action == LinuxActionKind.APPLICATION:
            return [binding.target, *binding.arguments]
        if binding.action in {LinuxActionKind.URL, LinuxActionKind.FILE, LinuxActionKind.DIRECTORY}:
            return ["xdg-open", binding.target]
        if binding.action == LinuxActionKind.COMMAND:
            if binding.allow_shell:
                return ["/bin/sh", "-lc", binding.target]
            return [binding.target, *binding.arguments] if binding.target else list(binding.arguments)
        if binding.action == LinuxActionKind.NOTIFICATION:
            return ["notify-send", binding.target, *binding.arguments]
        if binding.action == LinuxActionKind.SCRIPT:
            return [binding.target, *binding.arguments]
        if binding.action == LinuxActionKind.TEXT:
            # Clipboard/type injection needs desktop-specific backends; mock mode remains useful for profiles.
            return ["vaydeer-studio-text", binding.target]
        raise ValueError(f"Unsupported Linux binding action: {binding.action}")


@dataclass(frozen=True)
class VendorKeyEvent:
    layer_index: int
    key_index: int
    pressed: bool
    raw: bytes


def parse_vendor_event(report: bytes) -> VendorKeyEvent | None:
    if len(report) < 6 or report[0] != 0xFB or report[1] != 0x03:
        return None
    if report[5] != (report[0] ^ report[1] ^ report[2] ^ report[3] ^ report[4]):
        return None
    if report[4] not in {0x00, 0x02}:
        return None
    return VendorKeyEvent(layer_index=report[2], key_index=report[3], pressed=report[4] == 0x00, raw=report)
