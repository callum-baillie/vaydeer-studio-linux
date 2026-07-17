# UI and UX Audit

## Scope

This audit covers the PySide6/QML desktop application as shipped in 0.1.13.
The protocol, device discovery, backup, and verified-write paths are outside
the scope of this polish pass and remain unchanged.

## Problems found

### Terminology and mental model

- The app used both "Linux bindings" and "local Vaydeer service" without
  consistently explaining that host actions are distinct from mappings stored
  in keypad memory.
- `vaydeer-studiod` appeared in ordinary UI copy where "Background service"
  is clearer for most users.
- Profiles showed a mix of device state, local profile state, platform target,
  and binding counts as independent badges. This made it hard to tell what a
  profile selection actually changes.

### Visual hierarchy

- The top bar, sidebar, page header, panels, and footer repeated connection
  and draft status. The result was visually dense despite a small amount of
  actual information.
- Major pages used many equal-weight bordered rectangles, especially Devices,
  Profiles, and Diagnostics. Important actions did not read as primary.
- Controls varied in height, spacing, and emphasis. A device write, a local
  refresh, and a non-destructive profile operation could appear as peers.

### Workflow clarity

- The on-device workflow did not consistently present the sequence: read,
  edit draft, review, then write to keypad.
- Linux-action forms exposed several implementation-oriented fields before a
  user selected an action type.
- The tester’s default event panel was mostly empty and showed raw vendor data
  even when it was not useful.
- Setup information was embedded in the Devices page rather than presented as
  a first-run checklist with individual recovery actions.

### Accessibility and responsive behavior

- Small 10–11 px secondary text reduced readability on laptop screens.
- Focus styling was inherited inconsistently across controls.
- The narrow window layout had no reusable page header/empty-state pattern,
  which made clipping and empty space more likely as screens grew.

## Design direction

- Keep Vaydeer Studio a compact desktop utility, not a dashboard.
- Use a small design-token set, 8 px spacing rhythm, standard 36 px controls,
  one teal on-device identity, and a blue host-action identity.
- Use "On-device keys" for portable keypad memory and "Linux actions" for
  host-side behavior. Refer to the daemon as "Background service" in Basic
  mode.
- Make Basic mode the default and confine HID paths, raw reports, and protocol
  details to Advanced mode.
- Keep a compact device/service summary in the application bar. Show detailed
  state only on Overview, Setup, or Diagnostics.

## Implemented fixes

- Added reusable page headers, information banners, health rows, empty states,
  and a compact status treatment built from shared QML primitives.
- Added persistent Basic/Advanced mode and theme selection.
- Simplified the application shell and navigation, including a dedicated Setup
  screen and direct navigation to the two principal workflows.
- Reworked each screen to distinguish keypad-memory content from Linux-only
  actions with language, labels, and color-independent text.
- Reduced raw technical detail in Basic mode and added helpful empty, loading,
  disconnected, and service-stopped states.
- Persist normal window size, position, and maximized state. Restored geometry
  is clamped to an available display so a changed DPI, moved panel, or
  disconnected external monitor cannot reopen Studio off-screen.
- Make the Profiles page explicitly vertically scrollable, with an always
  visible scrollbar at constrained laptop heights.
- Added responsive mock rendering coverage and refreshed documented screenshots.

## Deferred ideas

- Native file-picker dialogs for profile import/export and application paths.
  The current backend accepts explicit paths and preserves its existing schema;
  adding platform-specific picker integration needs a separate interaction and
  test pass.
- Full undo/redo history for profile drafts. The current discard-to-device
  baseline path remains the reliable recovery mechanism.

## Window and responsive follow-up

The 0.1.17 follow-up used fresh mock captures at 1280x720 and 960x620 plus a
native X11/LXQt launch on a 1920x1080 display with 1920x1039 usable geometry.

### Problems confirmed

- The first geometry implementation stored QWindow client dimensions. The
  observed 1031x1037 client rectangle did not include the native title bar and
  borders, so restoring it could place the decorated frame below the usable
  desktop.
- The application also set an initial position before the Linux window manager
  had created the native frame, overriding normal desktop placement behavior.
- On-device keys, Linux actions, and Help had content below the viewport but
  relied on implicit ScrollView sizing, leaving the lower content clipped with
  no visible scroll affordance.
- At 960x620, Live Tester controls overlapped the event count and its empty-state
  copy exceeded the available panel width. The on-device layout title also
  competed horizontally with its state legend.

### Fixes verified

- Window state now has a versioned frame-geometry schema. Legacy client-only
  values are ignored. New windows are sized conservatively and positioned by
  the window manager; saved frames are restored only after native decorations
  exist and are clamped to current usable displays.
- A native restore of a saved 1100x730 frame at 200,120 produced the expected
  1098x697 client area and retained the requested outer-frame placement.
- All long pages share one keyboard-accessible Flickable and visible scrollbar.
  The minimum-size GUI test proves lower content is reachable on On-device
  keys, Linux actions, Profiles, and Help.
- Live Tester uses a two-row event header at narrow widths, constrains empty
  copy to the panel, and the on-device legend now sits below its heading.
