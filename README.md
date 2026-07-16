# Vaydeer Studio

Vaydeer Studio is a Linux-first desktop configurator for Vaydeer macro keypads,
with a safety-first implementation for the JP-1011 nine-key keypad. It keeps
the JP-1011 active by holding its vendor async HID interface open read-only,
separates onboard mappings from Linux-side actions, backs up before writes, and
never implements firmware updates.

The complete installation, safety, device-support, and research documentation is
being added with the application implementation. Until then, use the mock target
for development:

```bash
uv sync --extra dev
uv run vaydeer-studio --mock jp1011
```

This is an original MIT-licensed project. See [ATTRIBUTION.md](ATTRIBUTION.md).
