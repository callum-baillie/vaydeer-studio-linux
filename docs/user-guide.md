# User Guide

Open **Devices** to inspect the detected keypad. The JP-1011 diagram follows
vendor indexes `0` through `8`: top-left to bottom-right.

When no keypad is present, **Devices** shows a disconnected state instead of
mock data. Select **Retry detection** after connecting it. The **Local Vaydeer
service** panel names the host running the desktop app and shows whether the
user service is installed, running, reachable, and enabled at login. Select
**Install user service** only to create and enable `vaydeer-studiod` for the
current user. It never invokes `sudo`; **Setup** remains the explicit source
installation path for the scoped udev rule. **Export diagnostics** writes a
sanitized report.

## On-device mappings

Choose a layer, select a key on the physical diagram, choose a stable action
category, then capture a value from a physical keyboard or enter it manually.
`A`, `F13`, and `CTRL+ALT+P` are accepted forms and render as readable values.
Select **Capture a key** before pressing a computer key. A physical numeric-pad
digit is stored as `Num 0` through `Num 9`, matching the JP-1011's existing
virtual-key mappings; a top-row digit remains `0` through `9`. The capture
message names the resulting explicit device value. While the mapping page is
open, pressing a physical keypad key selects it in the editor without changing
the device. Macro recording captures computer-keyboard press/release timing
and keeps it as portable experimental profile data until its device payload is
independently verified. It is never sent to the keypad. Select **Preview
apply** to read the device, create a backup, and populate the diff. In mock
mode Apply commits and verifies the change. With a physical keypad, copy the
indicated CLI command and perform the typed terminal confirmation.

## Profiles

Profiles use schema-versioned JSON or YAML. Save to the local profile library,
duplicate, import, export, or clear a profile from **Profiles**. Imports are
validated against the connected key count. A profile can contain onboard layers
and Linux-side bindings without mixing their execution boundary. Select Linux,
macOS, or Windows as its target before saving or exporting. The bundled Codex,
ChatGPT, Photoshop, and Illustrator starters adapt `Ctrl` versus `Meta`
(Command) shortcuts for the selected target. Only Linux-targeted profiles load
their host bindings into the Linux user service; macOS and Windows profiles
remain portable onboard mapping workspaces.

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
