# Mapping, Binding, and Profile Interaction Design

## Scope

This document defines the desktop workflows for on-device mappings, Linux-side
bindings, and portable profiles. The primary target is the Vaydeer JP-1011,
but the interaction model must scale to every supported physical layout.

The design keeps three states separate:

- **Device baseline**: the last configuration read from the keypad.
- **Mapping draft**: the profile's on-device mapping changes that have not
  been synchronized to the keypad.
- **Linux bindings**: host-side actions owned by `vaydeer-studiod`, never
  serialized into the keypad's configuration reports.

## Research Inputs

Keychron Launcher uses a direct keymap workflow: select a key on the virtual
keyboard, then choose an action from categories such as basic keys, media,
macros, special keys, and layers. It also treats layers as a first-class
dimension of the keymap. This is the primary interaction model adopted for the
on-device page. Source: [How to Remap a Key on Launcher](https://www.keychron.com/blogs/news/how-to-remap-a-key-on-launcher), retrieved 2026-07-16.

Elgato Stream Deck profiles make device model and operating system compatibility
visible, and describe a profile as a portable layout of actions rather than as
a hardware write. Vaydeer Studio adopts this distinction: local profiles are
portable workspaces, while an explicit reviewed apply is the only route to a
hardware change. Source: [Elgato Stream Deck Profiles](https://docs.elgato.com/stream-deck/profiles/getting-started/), retrieved 2026-07-16.

Logi Options+ models automation as a trigger plus one or more actions, with
editing and removal available from the action list. Vaydeer Studio therefore
uses a selected binding editor instead of an append-only form. Source:
[Creating Smart Actions](https://support.logi.com/hc/en-001/articles/14307858722327-How-to-create-a-new-Smart-Actions-on-Logi-Options), retrieved 2026-07-16.

The ChatGPT web experience documents `Ctrl+K` on Windows/Linux and `Cmd+K` on
macOS for chat-history search. The ChatGPT preset uses that documented action
and otherwise limits itself to universal browser navigation rather than
claiming undocumented product commands. Source: [OpenAI Help: Search chat
history](https://help.openai.com/en/articles/10056348), retrieved 2026-07-16.

Adobe's shortcut references confirm the Photoshop undo/redo modifiers and the
Illustrator tool-key set used by the bundled presets. Sources: [Photoshop undo
and redo](https://helpx.adobe.com/photoshop/desktop/get-started/set-up-toolbars-panels/use-undo-redo-commands.html)
and [Illustrator default keyboard
shortcuts](https://helpx.adobe.com/ca/illustrator/using/default-keyboard-shortcuts.html),
retrieved 2026-07-16.

## On-Device Mappings

### Page Structure

1. A context bar selects the layer and shows the last device-read baseline.
2. The physical keypad is the primary selector. It always uses the actual
   physical layout and vendor key order.
3. A property inspector edits the selected key. It keeps action type, keypad
   label, key value, draft/device comparison, and save action together.
4. Review, restore, discard, and device-refresh commands remain separate from
   individual key editing.

### Key State

Every key is rendered from the current mapping draft. A teal indicator means
the draft equals the last device read. An amber indicator and amber outline
mean the draft differs and needs a reviewed synchronization. Hover and
accessibility text include both values when they differ.

Refreshing the device updates the baseline. It only replaces the draft when
there are no pending on-device mapping changes. When a draft exists, it is
kept and re-compared against the newly read baseline. `Use device state` or
`Discard` explicitly replaces the draft with the device configuration.

### Value Entry

Keyboard, modifier, shortcut, and media actions provide readable choices and a
keyboard-capture control. Capture is an explicit armed state with a clear
result message: numeric keypad digits are stored as `Num 0` through `Num 9`,
while top-row digits remain their ordinary values. Shortcut editing adds
explicit modifier controls and a primary-key chooser while retaining text entry
for advanced values. Labels are optional and only affect the keypad legend; the
selected key value is the actual on-device behavior. While this page is open,
physical keypad presses select their corresponding editor key without creating
a tester log or changing the device.

Unvalidated vendor payload categories remain distinct from supported mapping
types and must not be represented as writable hardware actions.

## Linux Bindings

The page has three steps in a single working view:

1. Select a physical key and layer on the visual keypad.
2. Create or edit a host action with a typed action selector, target, parsed
   argument array, trigger, optional active-window condition, and explicit
   shell opt-in.
3. Review saved bindings in a selectable list with enable, edit, test-in-mock,
   and remove controls.

The local service's running, login-start, and socket-reachability state remain
visible at the top of the page. Only `press` and `release` appear as creatable
triggers because those are the triggers currently dispatched by the service.
Existing unsupported trigger records are retained for portability but marked
as not executed rather than silently behaving incorrectly.

Application, URL, file, directory, command, notification, and script actions
use structured targets and argument arrays. Shell execution is hidden unless
the action is a command and the user opts in. Text injection remains explicitly
backend-dependent on real desktops and is useful in mock mode without claiming
universal Linux support.

## Profiles

Profiles are local, portable workspaces that contain on-device mapping drafts,
layers, and Linux bindings. The profile page presents:

- the workspace name and source (`Device snapshot`, local, imported, or new),
- independent mapping-sync and local-save status,
- local save, duplicate, import, JSON/YAML export, and delete commands,
- the last device baseline with non-destructive refresh and explicit discard,
- device key-count, layer-count, and binding-count compatibility context, and
- saved-profile metadata including layers, bindings, last update, and current
  selection.

Each profile declares its target operating system: Linux, macOS, or Windows.
The target changes only portable shortcut encoding (`Ctrl` versus Command/
`Meta`) and never changes a connected device automatically. Bundled presets
for Codex, ChatGPT, Photoshop, and Illustrator create a nine-key mapping
starter with a reviewable target. Linux-side bindings are only synchronized to
`vaydeer-studiod` for Linux-targeted profiles. This prevents a profile prepared
for another operating system from accidentally acquiring host-specific behavior
on the Linux machine where it is edited.

Recorded macros retain typed press, release, and meaningful timing steps in the
portable profile. Their vendor encoding remains unknown, so the editor makes
their experimental/profile-only state visible and the safety layer refuses to
send them to a physical keypad.

Saving a profile is local and synchronizes its Linux bindings to the service
when reachable. It never writes to the keypad. Applying on-device mappings
still requires the existing backup, diff review, terminal confirmation for
real hardware, write, and read-back verification sequence.

## Future Work

- Add a dedicated conflict-review dialog when a refreshed device baseline and
  a draft differ on the same key.
- Add verified layer-action and system-control pickers only after their
  read/write payloads are independently validated.
- Add an optional desktop text-injection backend selection with clear Wayland
  and X11 capability checks.
- Support deliberate bulk key assignment once multi-selection and undo can be
  made safe and understandable.
