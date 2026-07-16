"""Smoke tests for the application shell's persistent UI state."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine

from vaydeer_studio.ui.controller import StudioController


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
    _stop_controller_timers(controller)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("vaydeerBridge", controller)
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

    window.setProperty("width", 1_280)
    window.setProperty("height", 720)
    qtbot.wait(50)
    assert app_bar.property("height") == 64

    window.close()
