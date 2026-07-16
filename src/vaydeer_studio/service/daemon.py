"""Small Unix-domain-socket companion service for keepalive and Linux bindings."""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_runtime_path

from vaydeer_studio.core.logging import configure_logging
from vaydeer_studio.core.models import LinuxBinding, TriggerKind
from vaydeer_studio.core.profiles import ProfileStore
from vaydeer_studio.devices.mock import MockJP1011Transport

from .bindings import BindingExecutor, parse_vendor_event
from .keepalive import KeepaliveManager


def default_socket_path() -> Path:
    return user_runtime_path("vaydeer-studio", "Vaydeer Studio") / "vaydeer-studiod.sock"


@dataclass
class ServiceDaemon:
    socket_path: Path
    keepalive: KeepaliveManager
    executor: BindingExecutor
    bindings: list[LinuxBinding]
    mock_transport: MockJP1011Transport | None = None

    def __init__(
        self,
        socket_path: Path | None = None,
        *,
        mock: bool = False,
        keepalive: KeepaliveManager | None = None,
        executor: BindingExecutor | None = None,
    ) -> None:
        self.socket_path = socket_path or default_socket_path()
        self.keepalive = keepalive or KeepaliveManager()
        self.executor = executor or BindingExecutor(mock_mode=mock)
        active_profile = ProfileStore().load_active()
        self.bindings = [] if active_profile is None else active_profile.linux_bindings
        self.keepalive.set_event_listening(bool(self.bindings))
        self.mock_transport = MockJP1011Transport() if mock else None
        self._running = threading.Event()

    def status(self) -> dict[str, Any]:
        return {
            "keepalive": self.keepalive.status(),
            "mock": self.mock_transport is not None,
            "binding_count": len(self.bindings),
            "recent_actions": [result.__dict__ for result in self.executor.history[-10:]],
        }

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        if method == "status":
            return {"ok": True, "result": self.status()}
        if method == "set_bindings":
            self.bindings = [LinuxBinding.model_validate(item) for item in request.get("bindings", [])]
            self.keepalive.set_event_listening(bool(self.bindings))
            return {"ok": True, "result": {"binding_count": len(self.bindings)}}
        if method == "execute_binding":
            result = self.executor.execute(LinuxBinding.model_validate(request["binding"]))
            return {"ok": result.ok, "result": result.__dict__}
        if method == "vendor_event":
            raw = bytes.fromhex(str(request["hex"]))
            return {"ok": True, "result": self.dispatch_vendor_event(raw)}
        if method == "tick":
            return {
                "ok": True,
                "result": self.keepalive.status() if self.mock_transport else self.keepalive.tick().__dict__,
            }
        if method == "shutdown":
            self._running.clear()
            return {"ok": True, "result": "stopping"}
        return {"ok": False, "error": f"Unknown method {method!r}"}

    def dispatch_vendor_event(self, raw: bytes) -> dict[str, Any]:
        event = parse_vendor_event(raw)
        if event is None:
            return {"accepted": False, "reason": "invalid vendor event"}
        trigger = TriggerKind.PRESS if event.pressed else TriggerKind.RELEASE
        matched = [
            binding
            for binding in self.bindings
            if binding.enabled
            and binding.key_index == event.key_index
            and binding.layer_index == event.layer_index
            and binding.trigger == trigger
        ]
        results = [self.executor.execute(binding).__dict__ for binding in matched]
        return {"accepted": True, "key_index": event.key_index, "pressed": event.pressed, "executed": results}

    def serve_forever(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self.socket_path.exists():
            self.socket_path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        server.listen(8)
        server.settimeout(0.25)
        self._running.set()
        try:
            while self._running.is_set():
                if self.mock_transport is None:
                    self.keepalive.tick()
                    raw_event = self.keepalive.read_event()
                    if raw_event:
                        self.dispatch_vendor_event(raw_event)
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    continue
                with connection:
                    payload = connection.recv(1024 * 1024)
                    try:
                        request = json.loads(payload.decode("utf-8"))
                        response = self.handle(request)
                    except Exception as error:
                        response = {"ok": False, "error": str(error)}
                    connection.sendall(json.dumps(response, default=str).encode("utf-8"))
        finally:
            server.close()
            self.keepalive.stop()
            self.socket_path.unlink(missing_ok=True)


def request(socket_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    last_error: ConnectionRefusedError | None = None
    for attempt in range(3):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(0.25)
            client.connect(str(socket_path))
            client.sendall(json.dumps(payload).encode("utf-8"))
            return json.loads(client.recv(1024 * 1024).decode("utf-8"))
        except ConnectionRefusedError as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.025)
        finally:
            client.close()
    assert last_error is not None
    raise last_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock", action="store_true", help="Run with mock bindings and no physical device.")
    parser.add_argument("--socket", type=Path, default=default_socket_path())
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error"], help="Service log level.")
    args = parser.parse_args(argv)
    configure_logging(level=args.log_level.upper() if args.log_level else None)
    daemon = ServiceDaemon(args.socket, mock=args.mock)
    daemon.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
