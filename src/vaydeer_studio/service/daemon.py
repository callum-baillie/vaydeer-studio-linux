"""Small Unix-domain-socket companion service for keepalive and Linux bindings."""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_runtime_path

from vaydeer_studio import __version__
from vaydeer_studio.core.logging import configure_logging
from vaydeer_studio.core.models import LinuxBinding, TriggerKind
from vaydeer_studio.core.profiles import ProfileStore
from vaydeer_studio.devices.mock import MockJP1011Transport

from .bindings import BindingExecutor, parse_vendor_event
from .keepalive import KeepaliveManager

MAX_EVENTS_PER_TICK = 32
TESTER_EVENT_LIMIT = 128
TESTER_LEASE_SECONDS = 2.0


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
        self.mock_transport = MockJP1011Transport() if mock else None
        self._tester_expires_at = 0.0
        self._tester_events: deque[dict[str, Any]] = deque(maxlen=TESTER_EVENT_LIMIT)
        self._update_event_listening()
        self._running = threading.Event()

    def status(self) -> dict[str, Any]:
        self._refresh_tester_lease()
        return {
            "keepalive": self.keepalive.status(),
            "mock": self.mock_transport is not None,
            "binding_count": len(self.bindings),
            "tester_active": self._tester_active(),
            "recent_actions": [result.__dict__ for result in self.executor.history[-10:]],
        }

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        if method == "status":
            return {"ok": True, "result": self.status()}
        if method == "set_bindings":
            self.bindings = [LinuxBinding.model_validate(item) for item in request.get("bindings", [])]
            self._update_event_listening()
            return {"ok": True, "result": {"binding_count": len(self.bindings)}}
        if method == "set_tester":
            enabled = bool(request.get("enabled"))
            self._tester_expires_at = time.monotonic() + TESTER_LEASE_SECONDS if enabled else 0.0
            if not enabled:
                self._tester_events.clear()
            self._update_event_listening()
            return {"ok": True, "result": self._tester_result()}
        if method == "drain_tester_events":
            self._refresh_tester_lease()
            if self._tester_active():
                self._tester_expires_at = time.monotonic() + TESTER_LEASE_SECONDS
            self._update_event_listening()
            events = list(self._tester_events)
            self._tester_events.clear()
            return {"ok": True, "result": self._tester_result(events)}
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
        if self._tester_active():
            self._tester_events.append(
                {
                    "timestamp": datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3],
                    "key_index": event.key_index if event is not None else None,
                    "layer_index": event.layer_index if event is not None else None,
                    "pressed": event.pressed if event is not None else None,
                    "raw": raw[:16].hex(" "),
                    "valid": event is not None,
                }
            )
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

    def _tester_active(self) -> bool:
        return time.monotonic() < self._tester_expires_at

    def _refresh_tester_lease(self) -> None:
        if not self._tester_active() and self._tester_expires_at:
            self._tester_expires_at = 0.0
            self._tester_events.clear()
            self._update_event_listening()

    def _update_event_listening(self) -> None:
        self.keepalive.set_event_listening(bool(self.bindings) or self._tester_active())

    def _tester_result(self, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "events": [] if events is None else events,
            "tester_active": self._tester_active(),
            "keepalive": self.keepalive.status(),
        }

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
                self._refresh_tester_lease()
                if self.mock_transport is None:
                    self.keepalive.tick()
                    for _ in range(MAX_EVENTS_PER_TICK):
                        raw_event = self.keepalive.read_event()
                        if not raw_event:
                            break
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
    parser.add_argument("--version", action="version", version=f"vaydeer-studiod {__version__}")
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
