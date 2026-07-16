"""Curated, portable starting points for common application workflows.

The templates intentionally contain only documented, on-device keyboard
shortcuts.  Linux-side launch actions stay out of them so a profile created on
Linux remains useful when exported for macOS or Windows.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import AssignmentKind, KeyAssignment, Layer, Profile, ProfileTargetPlatform


@dataclass(frozen=True)
class ProfileTemplate:
    """A named profile starter that can adapt its primary modifier by platform."""

    id: str
    name: str
    application: str
    summary: str
    build_assignments: Callable[[ProfileTargetPlatform], list[KeyAssignment]]


def profile_template_summaries() -> list[dict[str, str]]:
    """Return QML-friendly metadata without exposing mutable template state."""

    return [
        {
            "id": template.id,
            "name": template.name,
            "application": template.application,
            "summary": template.summary,
        }
        for template in _TEMPLATES
    ]


def create_profile_from_template(template_id: str, platform: ProfileTargetPlatform) -> Profile:
    """Materialize a new JP-1011 profile for the requested target operating system."""

    template = next((item for item in _TEMPLATES if item.id == template_id), None)
    if template is None:
        raise ValueError(f"Unknown profile preset {template_id!r}")
    platform_name = _platform_label(platform)
    return Profile(
        name=f"{template.name} ({platform_name})",
        target_platform=platform,
        target_application=template.application,
        layers=[Layer(index=0, name="Default", assignments=template.build_assignments(platform))],
    )


def _platform_label(platform: ProfileTargetPlatform) -> str:
    return {
        ProfileTargetPlatform.LINUX: "Linux",
        ProfileTargetPlatform.MACOS: "macOS",
        ProfileTargetPlatform.WINDOWS: "Windows",
    }[platform]


def _primary_modifier(platform: ProfileTargetPlatform) -> int:
    if platform == ProfileTargetPlatform.MACOS:
        return 91
    return 17


def _key(index: int, label: str, code: int) -> KeyAssignment:
    return KeyAssignment(key_index=index, label=label, kind=AssignmentKind.KEYBOARD, key_codes=[code])


def _shortcut(index: int, label: str, codes: list[int]) -> KeyAssignment:
    return KeyAssignment(key_index=index, label=label, kind=AssignmentKind.COMBINATION, key_codes=codes)


def _mod_shortcut(index: int, label: str, primary: int, key: str, *, shift: bool = False) -> KeyAssignment:
    codes = [primary]
    if shift:
        codes.append(16)
    codes.append(ord(key))
    return _shortcut(index, label, codes)


def _codex_assignments(platform: ProfileTargetPlatform) -> list[KeyAssignment]:
    primary = _primary_modifier(platform)
    return [
        _mod_shortcut(0, "Command palette", primary, "P", shift=True),
        _mod_shortcut(1, "Quick open", primary, "P"),
        _mod_shortcut(2, "Save", primary, "S"),
        _mod_shortcut(3, "Find files", primary, "F", shift=True),
        _mod_shortcut(4, "Sidebar", primary, "B"),
        _mod_shortcut(5, "Go to line", primary, "G"),
        _mod_shortcut(6, "Undo", primary, "Z"),
        _mod_shortcut(7, "Redo", primary, "Z", shift=True),
        _mod_shortcut(8, "Close editor", primary, "W"),
    ]


def _chatgpt_assignments(platform: ProfileTargetPlatform) -> list[KeyAssignment]:
    primary = _primary_modifier(platform)
    return [
        _mod_shortcut(0, "Search chats", primary, "K"),
        _mod_shortcut(1, "New browser tab", primary, "T"),
        _mod_shortcut(2, "Address bar", primary, "L"),
        _mod_shortcut(3, "Find on page", primary, "F"),
        _key(4, "Page down", 34),
        _key(5, "Page up", 33),
        _key(6, "Enter", 13),
        _key(7, "Escape", 27),
        _mod_shortcut(8, "Reload page", primary, "R"),
    ]


def _photoshop_assignments(platform: ProfileTargetPlatform) -> list[KeyAssignment]:
    primary = _primary_modifier(platform)
    return [
        _key(0, "Move tool", ord("V")),
        _key(1, "Marquee", ord("M")),
        _key(2, "Brush", ord("B")),
        _key(3, "Eraser", ord("E")),
        _key(4, "Eyedropper", ord("I")),
        _mod_shortcut(5, "Save", primary, "S"),
        _mod_shortcut(6, "Undo", primary, "Z"),
        _mod_shortcut(7, "Redo", primary, "Z", shift=True),
        _key(8, "Hand", ord("H")),
    ]


def _illustrator_assignments(platform: ProfileTargetPlatform) -> list[KeyAssignment]:
    primary = _primary_modifier(platform)
    return [
        _key(0, "Selection", ord("V")),
        _key(1, "Direct select", ord("A")),
        _key(2, "Pen", ord("P")),
        _key(3, "Type", ord("T")),
        _key(4, "Paintbrush", ord("B")),
        _key(5, "Gradient", ord("G")),
        _mod_shortcut(6, "Save", primary, "S"),
        _mod_shortcut(7, "Undo", primary, "Z"),
        _mod_shortcut(8, "Redo", primary, "Z", shift=True),
    ]


_TEMPLATES: tuple[ProfileTemplate, ...] = (
    ProfileTemplate(
        id="codex",
        name="Codex workspace",
        application="Codex / VS Code",
        summary="Portable editor commands for a Codex development workspace.",
        build_assignments=_codex_assignments,
    ),
    ProfileTemplate(
        id="chatgpt",
        name="ChatGPT browser",
        application="ChatGPT",
        summary="Chat history search plus universal browser navigation.",
        build_assignments=_chatgpt_assignments,
    ),
    ProfileTemplate(
        id="photoshop",
        name="Photoshop tools",
        application="Adobe Photoshop",
        summary="Common Photoshop tools, save, undo, and redo.",
        build_assignments=_photoshop_assignments,
    ),
    ProfileTemplate(
        id="illustrator",
        name="Illustrator tools",
        application="Adobe Illustrator",
        summary="Common Illustrator tools, save, undo, and redo.",
        build_assignments=_illustrator_assignments,
    ),
)
