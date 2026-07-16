# User Guide

Open **Devices** to inspect the detected keypad. The JP-1011 diagram follows
vendor indexes `0` through `8`: top-left to bottom-right.

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

The live tester displays only while explicitly open and clears events when it
closes. Diagnostics include matched interfaces, permission state, keepalive
state, device information, and recent UI status. Exported diagnostic bundles are
intended to be shareable after a final personal-data review.
