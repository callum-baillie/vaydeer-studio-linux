# Development

Use `make setup`, `make lint`, `make typecheck`, `make test`, `make build`, and
`make docs`. The test suite uses a stateful mock JP-1011 with the observed
firmware `1.0.2`, bootloader `0.2.1`, nine keys, six maximum layers, event
reports, disconnect/reconnect behavior, permission failures, checksum errors,
and partial writes.

Discovery tests also cover hidapi entries with missing usage metadata, sysfs
descriptor fallback, startup races, permission and protocol failures, unplug
state transitions, changed hidraw nodes, and kernel reuse of the same hidraw
node after reconnect.

Run the UI without hardware using `uv run vaydeer-studio --mock jp1011`. For a
headless QML smoke test use:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run vaydeer-studio --mock jp1011 --smoke
```

Hardware tests require `VAYDEER_HARDWARE_TESTS=1` and are read-only. Never add
firmware commands, command scans, or raw device writes to a test.
