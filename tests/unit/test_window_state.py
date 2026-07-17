"""Tests for safe window geometry restoration."""

from PySide6.QtCore import QRect, QSize

from vaydeer_studio.ui.window_state import WindowGeometry, clamp_window_geometry


def test_missing_geometry_uses_a_centered_fitting_default() -> None:
    geometry = clamp_window_geometry(
        None,
        [QRect(0, 0, 1366, 768)],
        QSize(960, 620),
    )

    assert geometry.width == 1280
    assert geometry.height == 720
    assert geometry.x == 43
    assert geometry.y == 24


def test_removed_external_display_restores_on_primary_display() -> None:
    geometry = clamp_window_geometry(
        WindowGeometry(2100, 120, 1440, 900),
        [QRect(0, 0, 1280, 720)],
        QSize(960, 620),
    )

    assert geometry == WindowGeometry(0, 0, 1280, 720)


def test_visible_geometry_is_clamped_to_the_current_display_bounds() -> None:
    geometry = clamp_window_geometry(
        WindowGeometry(1100, 620, 1100, 800),
        [QRect(0, 0, 1366, 768)],
        QSize(960, 620),
    )

    assert geometry == WindowGeometry(266, 0, 1100, 768)


def test_geometry_stays_on_the_matching_secondary_display() -> None:
    geometry = clamp_window_geometry(
        WindowGeometry(2100, 40, 1000, 700),
        [QRect(0, 0, 1920, 1080), QRect(1920, 0, 1280, 1024)],
        QSize(960, 620),
    )

    assert geometry == WindowGeometry(2100, 40, 1000, 700)
