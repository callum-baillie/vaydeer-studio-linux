# Contributing

Use `uv sync --extra dev`, then run `make lint`, `make typecheck`, and `make test`.
Do not add firmware update functionality, raw packet senders, proprietary Vaydeer
binaries, serial numbers, or unredacted host logs. Hardware tests must be opt-in
and must never issue firmware command `0xFC`.
