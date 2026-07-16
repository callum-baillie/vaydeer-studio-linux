from __future__ import annotations

import threading
import time
from pathlib import Path

from vaydeer_studio.core.models import LinuxActionKind, LinuxBinding
from vaydeer_studio.service.bindings import BindingExecutor, parse_vendor_event
from vaydeer_studio.service.daemon import ServiceDaemon, request


def test_linux_binding_actions_work_in_mock_mode() -> None:
    executor = BindingExecutor(mock_mode=True)
    for action, target in [
        (LinuxActionKind.APPLICATION, "code"),
        (LinuxActionKind.URL, "https://example.test"),
        (LinuxActionKind.FILE, "/tmp/report.txt"),
        (LinuxActionKind.DIRECTORY, "/tmp"),
        (LinuxActionKind.COMMAND, "printf"),
    ]:
        result = executor.execute(LinuxBinding(key_index=0, action=action, target=target, arguments=["ok"]))
        assert result.ok
    assert len(executor.history) == 5


def test_vendor_event_parsing_validates_checksum() -> None:
    event = parse_vendor_event(bytes.fromhex("fb03000400fc") + bytes(10))
    assert event is not None
    assert (event.layer_index, event.key_index, event.pressed) == (0, 4, True)
    assert parse_vendor_event(bytes.fromhex("fb0300040000")) is None


def test_service_ipc_dispatches_mock_binding(tmp_path: Path) -> None:
    path = tmp_path / "vaydeer.sock"
    daemon = ServiceDaemon(path, mock=True)
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    for _ in range(50):
        if path.exists():
            break
        time.sleep(0.01)
    assert request(path, {"method": "status"})["ok"]
    binding = LinuxBinding(key_index=2, action=LinuxActionKind.URL, target="https://example.test")
    assert request(path, {"method": "set_bindings", "bindings": [binding.model_dump(mode="json")]})["ok"]
    event = bytes([0xFB, 0x03, 0, 2, 0])
    raw = event + bytes([event[0] ^ event[1] ^ event[2] ^ event[3] ^ event[4]])
    response = request(path, {"method": "vendor_event", "hex": raw.hex()})
    assert response["result"]["executed"][0]["ok"]
    request(path, {"method": "shutdown"})
    thread.join(timeout=1)
