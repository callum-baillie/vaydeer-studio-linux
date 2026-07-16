# User Guide

Open **Devices** to inspect the detected keypad. The JP-1011 diagram follows
vendor indexes `0` through `8`: top-left to bottom-right.

When no keypad is present, **Devices** shows a disconnected state instead of
mock data. Select **Retry detection** after connecting it. **Setup** points to
the source installer, while **Export diagnostics** writes a sanitized report;
the desktop application never invokes `sudo` itself.

## On-device mappings

Choose a layer, select a key, choose a stable action category, enter a label
and key code, and save it to the profile. `A`, `F13`, and `CTRL+ALT+P` are
accepted key-code forms. Select **Preview apply** to read the device, create a
backup, and populate the diff. In mock mode Apply commits and verifies the
change. With a physical keypad, copy the indicated CLI command and perform the
typed terminal confirmation.

## Profiles

Profiles use schema-versioned JSON or YAML. Save to the local profile library,
duplicate, import, export, or clear a profile from **Profiles**. Imports are
validated against the connected key count. A profile can contain onboard layers
and Linux-side bindings without mixing their execution boundary.

## Linux bindings

Linux actions are triggered from the vendor event interface by the user service.
They are not stored in the keypad. Application, URL, file, directory, command,
notification, script, and text actions are supported in mock mode and use a
program plus arguments by default. Shell execution is not the default path.

## Live tester and diagnostics

The live tester asks the user service to read the vendor event interface only
while the screen is open. It clears its event queue when it closes, and the
service lease expires automatically if the UI stops polling. The tester shows
validated press/release reports and preserves an unrecognized raw event as an
`Unknown` row for troubleshooting. Diagnostics include matched interfaces,
permission state, keepalive state, device information, and recent UI status.
The diagnostics page has a refresh control and copyable summary. Exported
bundles omit USB serial numbers, home paths, raw vendor binaries, and full
report descriptors by default; perform a final personal-data review before
sharing.
