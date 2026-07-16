"""Human-readable names and parsing helpers for Vaydeer's observed key codes.

The protocol stores byte-sized virtual-key style values.  Keeping the names in
one module means the UI, profiles, and tests show meaningful values instead of
leaking hexadecimal transport details into normal editing workflows.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

KEY_CODES: dict[str, int] = {
    "CTRL": 17,
    "CONTROL": 17,
    "SHIFT": 16,
    "ALT": 18,
    "META": 91,
    "SUPER": 91,
    "SPACE": 32,
    "ENTER": 13,
    "ESC": 27,
    "ESCAPE": 27,
    "TAB": 9,
    "BACKSPACE": 8,
    "DELETE": 46,
    "INSERT": 45,
    "HOME": 36,
    "END": 35,
    "PAGE_UP": 33,
    "PAGE_DOWN": 34,
    "LEFT": 37,
    "UP": 38,
    "RIGHT": 39,
    "DOWN": 40,
    "PLAY_PAUSE": 179,
    "VOLUME_UP": 175,
    "VOLUME_DOWN": 174,
    "VOLUME_MUTE": 173,
}
KEY_CODES.update({chr(value): value for value in range(ord("A"), ord("Z") + 1)})
KEY_CODES.update({str(value): ord(str(value)) for value in range(10)})
KEY_CODES.update({f"F{value}": 111 + value for value in range(1, 25)})
KEY_CODES.update({f"NUM_{value}": 96 + value for value in range(10)})
KEY_CODES.update({f"NUM{value}": 96 + value for value in range(10)})

_PREFERRED_NAMES = {
    8: "Backspace",
    9: "Tab",
    13: "Enter",
    16: "Shift",
    17: "Ctrl",
    18: "Alt",
    27: "Esc",
    32: "Space",
    33: "Page Up",
    34: "Page Down",
    35: "End",
    36: "Home",
    37: "Left",
    38: "Up",
    39: "Right",
    40: "Down",
    45: "Insert",
    46: "Delete",
    91: "Meta",
    173: "Volume Mute",
    174: "Volume Down",
    175: "Volume Up",
    179: "Play/Pause",
}
_PREFERRED_NAMES.update({value: chr(value) for value in range(ord("A"), ord("Z") + 1)})
_PREFERRED_NAMES.update({value: str(value - ord("0")) for value in range(ord("0"), ord("9") + 1)})
_PREFERRED_NAMES.update({111 + value: f"F{value}" for value in range(1, 25)})
_PREFERRED_NAMES.update({96 + value: f"Num {value}" for value in range(10)})


def parse_key_codes(text: str) -> list[int]:
    """Parse UI-friendly names, decimal values, and hexadecimal values."""

    readable_aliases = {
        "PLAY/PAUSE": "PLAY_PAUSE",
        "VOLUME MUTE": "VOLUME_MUTE",
        "VOLUME DOWN": "VOLUME_DOWN",
        "VOLUME UP": "VOLUME_UP",
        "PAGE DOWN": "PAGE_DOWN",
        "PAGE UP": "PAGE_UP",
        "NUM 0": "NUM_0",
        "NUM 1": "NUM_1",
        "NUM 2": "NUM_2",
        "NUM 3": "NUM_3",
        "NUM 4": "NUM_4",
        "NUM 5": "NUM_5",
        "NUM 6": "NUM_6",
        "NUM 7": "NUM_7",
        "NUM 8": "NUM_8",
        "NUM 9": "NUM_9",
    }
    normalized_text = text.upper()
    for readable, canonical in readable_aliases.items():
        normalized_text = re.sub(rf"\b{re.escape(readable)}\b", canonical, normalized_text)

    values: list[int] = []
    for token in normalized_text.replace("+", " ").replace(",", " ").split():
        normalized = token.strip().upper().replace("-", "_")
        value = KEY_CODES.get(normalized)
        if value is None:
            value = int(normalized, 0)
        if not 0 <= value <= 255:
            raise ValueError(f"{token!r} is not a one-byte Vaydeer key code")
        values.append(value)
    if not values:
        raise ValueError("Enter a key value or key name")
    return values


def display_key_code(value: int) -> str:
    """Return the preferred UI name for a known key code."""

    return _PREFERRED_NAMES.get(value, f"0x{value:02X}")


def display_key_codes(values: Iterable[int]) -> str:
    """Render a shortcut using names that remain readable on the keypad."""

    return " + ".join(display_key_code(value) for value in values)
