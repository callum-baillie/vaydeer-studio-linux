# Contributing

Vaydeer Studio accepts focused bug fixes, tests, documentation improvements,
and evidence-based device support. Open an issue before a large protocol or UI
change so its safety and compatibility boundary can be agreed first.

## Development Setup

```bash
git clone https://github.com/callum-baillie/vaydeer-studio-linux.git
cd vaydeer-studio-linux
make setup
uv run vaydeer-studio --mock jp1011
```

Before submitting a pull request:

```bash
make lint
make typecheck
make test
make build
make docs
```

Keep commits scoped and describe user-visible behavior in `CHANGELOG.md`.
Include tests for protocol, profile, service, or UI changes. Hardware tests are
read-only, opt-in, and require `VAYDEER_HARDWARE_TESTS=1`.

## Hardware and Research Rules

- Never add firmware flashing, command scanning, raw packet senders, or a path
  that can emit command `0xFC`.
- Do not guess a payload format on a physical device.
- Keep unknown firmware and unverified mappings read-only.
- Do not commit vendor firmware, installers, extracted applications,
  disassembly databases, captures containing private data, USB serial numbers,
  usernames, or host-specific paths.
- Document protocol evidence, source URLs, exact revisions, and uncertainty.
- Code from a source without a compatible license must not be copied.

Diagnostics attached to an issue must be generated with the app's sanitized
export and reviewed by the submitter before publication.

By participating, contributors agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
