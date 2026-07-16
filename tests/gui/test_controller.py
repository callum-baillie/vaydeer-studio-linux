from __future__ import annotations

from vaydeer_studio.ui.controller import StudioController


def test_mock_controller_exposes_verified_three_by_three_layout() -> None:
    controller = StudioController(mock=True)
    assert controller.layoutColumns == 3
    assert [item["physicalLabel"] for item in controller.keys] == [
        "Top left",
        "Top center",
        "Top right",
        "Middle left",
        "Middle center",
        "Middle right",
        "Bottom left",
        "Bottom center",
        "Bottom right",
    ]


def test_controller_edits_profile_and_generates_diff() -> None:
    controller = StudioController(mock=True)
    controller.selectKey(0)
    controller.saveKey("Keyboard key", "A", "A")
    assert controller.dirty
    controller.previewApply()
    assert any("Num 7 -> A" in line for line in controller.previewLines)
