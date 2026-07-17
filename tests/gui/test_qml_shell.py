"""Smoke tests for the application shell's persistent UI state."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine

from vaydeer_studio.ui.controller import StudioController
from vaydeer_studio.ui.window_state import WindowState


def _stop_controller_timers(controller: StudioController) -> None:
    for timer in (controller._connection_timer, controller._health_timer, controller._tester_timer):
        if timer is not None:
            timer.stop()


def test_qml_shell_switches_modes_and_keeps_the_app_bar_visible(qtbot, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    QCoreApplication.setOrganizationName("Vaydeer Studio Tests")
    QCoreApplication.setOrganizationDomain("tests.vaydeer-studio.local")
    QCoreApplication.setApplicationName("Vaydeer Studio Tests")
    controller = StudioController(mock=True)
    window_state = WindowState(enabled=False)
    _stop_controller_timers(controller)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vaydeerBridge", controller)
    engine.rootContext().setContextProperty("windowState", window_state)
    qml_path = files("vaydeer_studio.resources.qml").joinpath("Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    qtbot.waitUntil(lambda: window.property("visible"), timeout=2_000)
    pages = window.findChild(QObject, "mainPages")
    app_bar = window.findChild(QObject, "appBar")
    preferences = window.findChild(QObject, "appPreferences")
    advanced_panel = window.findChild(QObject, "advancedDiagnosticsPanel")

    assert pages is not None
    assert app_bar is not None
    assert preferences is not None
    assert advanced_panel is not None
    assert app_bar.property("height") == 64

    window.setProperty("navIndex", 5)
    qtbot.waitUntil(lambda: pages.property("currentIndex") == 5, timeout=2_000)
    assert advanced_panel.property("visible") is False

    preferences.setProperty("advancedMode", True)
    qtbot.waitUntil(lambda: window.property("advancedMode") is True, timeout=2_000)
    assert advanced_panel.property("visible") is True

    window.setProperty("navIndex", 2)
    qtbot.waitUntil(lambda: pages.property("currentIndex") == 2, timeout=2_000)
    target_field = window.findChild(QObject, "linuxActionTarget")
    assert target_field is not None

    preferences.setProperty("darkMode", True)
    qtbot.waitUntil(lambda: window.property("darkMode") is True, timeout=2_000)
    assert target_field.property("color").name() == "#e8eef2"
    assert target_field.property("placeholderTextColor").name() == "#93a4b0"

    preferences.setProperty("darkMode", False)
    qtbot.waitUntil(lambda: window.property("darkMode") is False, timeout=2_000)
    assert target_field.property("color").name() == "#18242d"
    assert target_field.property("placeholderTextColor").name() == "#687b87"

    window.setProperty("width", 960)
    window.setProperty("height", 620)
    qtbot.wait(50)
    assert app_bar.property("height") == 64

    for page_index, scroll_name, scroll_bar_name in (
        (1, "mappingsScroll", "mappingsScrollBar"),
        (2, "bindingsScroll", "bindingsScrollBar"),
        (3, "profilesScroll", "profilesScrollBar"),
        (7, "helpScroll", "helpScrollBar"),
    ):
        window.setProperty("navIndex", page_index)
        qtbot.waitUntil(lambda expected=page_index: pages.property("currentIndex") == expected, timeout=2_000)
        page_scroll = window.findChild(QObject, scroll_name)
        page_scroll_bar = window.findChild(QObject, scroll_bar_name)
        assert page_scroll is not None
        assert page_scroll_bar is not None
        qtbot.waitUntil(
            lambda target=page_scroll: target.property("contentHeight") > target.property("height"),
            timeout=2_000,
        )
        assert page_scroll_bar.property("visible") is True
        page_scroll.setProperty(
            "contentY",
            page_scroll.property("contentHeight") - page_scroll.property("height"),
        )
        qtbot.waitUntil(lambda target=page_scroll: target.property("contentY") > 0, timeout=2_000)

    window.setProperty("navIndex", 4)
    qtbot.waitUntil(lambda: pages.property("currentIndex") == 4, timeout=2_000)
    tester_event_header = window.findChild(QObject, "testerEventHeader")
    tester_event_controls = window.findChild(QObject, "testerEventControls")
    tester_empty_state = window.findChild(QObject, "testerEmptyState")
    assert tester_event_header is not None
    assert tester_event_controls is not None
    assert tester_empty_state is not None
    assert tester_event_controls.property("y") > 0
    assert tester_empty_state.property("width") <= tester_empty_state.parent().property("width")

    window.close()
