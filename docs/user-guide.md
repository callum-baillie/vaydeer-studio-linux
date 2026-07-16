# User Guide

Start with **Overview** to inspect the detected keypad and Background service.
The JP-1011 diagram follows vendor indexes `0` through `8`: top-left to
bottom-right. Studio is only needed to configure or inspect the device; the
Background service continues Linux support after the Studio window closes.

When no keypad is present, Overview and **Setup** show a clear disconnected
state and a relevant recovery action. Setup is the place to install or start
the Background service, check permissions, and reconnect the keypad. It never
changes mappings or firmware. The scoped udev rule remains an explicit source
installation step; **Export diagnostics** writes a sanitized report.

## On-device keys

Choose a layer, select a key on the physical diagram, choose a stable action
category, then capture a value from a physical keyboard or enter it manually.
`A`, `F13`, and `CTRL+ALT+P` are accepted forms and render as readable values.
Select **Capture key** before pressing a computer key. A physical numeric-pad
digit is stored as `Num 0` through `Num 9`, matching the JP-1011's existing
virtual-key mappings; a top-row digit remains `0` through `9`. The capture
message names the resulting explicit device value.

While the page is open, pressing a physical keypad key selects it in the editor
without changing the device. Macro recording captures computer-keyboard
press/release timing and keeps it as portable experimental profile data until
its device payload is independently verified. It is never sent to the keypad.

Select **Review changes** to read the device, create a backup, and populate the
diff. With a physical keypad, choose **Write to keypad**, type `APPLY` in the
confirmation dialog, and let the application commit and verify the change. The
CLI retains its separate typed terminal confirmation flow.

On-device keys are stored in keypad memory. Once written, they work on any
compatible computer and do not require the Background service.

## Profiles

Profiles use schema-versioned JSON or YAML. Save to the local profile library,
duplicate, import, export, or clear a profile from **Profiles**. Imports are
validated against the connected key count. A profile can contain onboard layers
and Linux actions without mixing their execution boundary. Select Linux, macOS,
or Windows as its target before saving or exporting.

The bundled Codex, ChatGPT, Photoshop, and Illustrator starters adapt `Ctrl`
versus `Meta` (Command) shortcuts for the selected target. Only Linux-targeted
profiles load their host actions into the Background service; macOS and Windows
profiles remain portable on-device mapping workspaces.

## Linux actions

Linux actions are triggered from the vendor event interface by the Background
service. They are stored in the selected local profile, never in the keypad.
Application, URL, file, directory, command, notification, script, and text
actions are supported in mock mode and use a program plus arguments by default.
Shell execution is not the default path; it is an Advanced-mode opt-in.

Saving an action updates the local profile and synchronizes it to the
Background service when available. The action can be edited while the service
is stopped, but it will not run until the service is started.

## Live tester and diagnostics

The live tester asks the Background service to read the vendor event interface
only while the screen is open. It clears its event queue when it closes, and the
service lease expires automatically if the UI stops polling. Use **Pause** to
stop capture, **Copy** for a selected readable event summary, or **Export** to
save the visible session. Basic mode shows time, key, press/release, layer, and
source. Advanced mode adds raw report information.

Diagnostics starts with a plain-language health summary and directs repairs to
Setup. Advanced mode includes matched interfaces, permission detail, keepalive
state, device information, and raw summary data. Exported bundles omit USB
serial numbers, home paths, raw vendor binaries, and full report descriptors by
default; perform a final personal-data review before sharing.

## Basic and Advanced modes

Basic mode keeps normal tasks focused. It hides HID paths, report bytes,
protocol values, and shell controls. Advanced mode reveals those technical
details without changing the profile, selected key, layer, or device state.
