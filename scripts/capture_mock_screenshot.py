#!/usr/bin/env python3
"""Render the JP-1011 mock UI to a PNG for visual regression inspection."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from importlib.resources import files

from PySide6.QtCore import QCoreApplication, QObject, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from vaydeer_studio.ui.controller import StudioController

_refs: list[StudioController] = []
_PAGE_KEYPADS = {
    0: "deviceOverviewKeypad",
    1: "mappingKeypad",
    2: "bindingKeypad",
    4: "testerKeypad",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", type=int, default=0, choices=range(8))
    parser.add_argument("--output", type=Path, default=Path("screenshots/mock-jp1011.png"))
    parser.add_argument("--live", action="store_true", help="Render the connected keypad without writing to it")
    parser.add_argument("--press-key", type=int, choices=range(9), help="Capture a mock tester key while pressed")
    parser.add_argument("--pending-key", type=int, choices=range(9), help="Stage a visible mock mapping change")
    parser.add_argument("--review", action="store_true", help="Open the reviewed-diff dialog for visual validation")
    parser.add_argument(
        "--confirm-write", action="store_true", help="Open the in-app write confirmation for visual validation"
    )
    parser.add_argument("--light", action="store_true", help="Render the light theme for visual validation")
    parser.add_argument("--advanced", action="store_true", help="Render Advanced mode for visual validation")
    parser.add_argument("--click-key", type=int, choices=range(9), help="Click a rendered keypad key before capture")
    parser.add_argument("--width", type=int, default=1440, help="Window width used for the rendered capture")
    parser.add_argument("--height", type=int, default=900, help="Window height used for the rendered capture")
    args = parser.parse_args()
    target = args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    QCoreApplication.setOrganizationName("Vaydeer Studio")
    QCoreApplication.setOrganizationDomain("vaydeer-studio.local")
    QCoreApplication.setApplicationName("Vaydeer Studio")
    application = QGuiApplication([])
    engine = QQmlApplicationEngine()
    controller = StudioController(mock=not args.live)
    _refs.append(controller)
    engine.rootContext().setContextProperty("vaydeerBridge", controller)
    engine.load(QUrl.fromLocalFile(str(files("vaydeer_studio.resources.qml").joinpath("Main.qml"))))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    window.setProperty("width", args.width)
    window.setProperty("height", args.height)
    if args.light:
        window.setProperty("darkMode", False)
    if args.advanced:
        window.setProperty("advancedMode", True)
    window.setProperty("navIndex", args.page)
    if args.pending_key is not None:
        controller.selectKey(args.pending_key)
        controller.saveKey("Keyboard key", "Draft", "F13")
    controller.setActivePage(args.page)
    if args.review or args.confirm_write:
        if args.pending_key is None:
            controller.selectKey(0)
            controller.saveKey("Keyboard key", "Draft", "F13")
        controller.previewApply()
        dialog_name = "hardwareWriteDialog" if args.confirm_write else "diffDialog"
        dialog = window.findChild(QObject, dialog_name)
        if dialog is None:
            return 1
        dialog.open()

    def click_key() -> None:
        if args.click_key is None:
            return
        keypad_name = _PAGE_KEYPADS.get(args.page)
        keypad = window.findChild(QQuickItem, keypad_name) if keypad_name else None
        if not isinstance(keypad, QQuickItem) or not keypad.property("interactive"):
            application.exit(1)
            return
        columns = int(keypad.property("columns"))
        rows = math.ceil(len(controller.keys) / columns)
        body_width = min(keypad.width(), keypad.height() * 1.07)
        body_height = body_width / 1.07
        body_x = (keypad.width() - body_width) / 2
        body_y = (keypad.height() - body_height) / 2
        grid_width = body_width * 0.78
        grid_height = body_height * 0.72
        spacing = max(5, grid_width * 0.032)
        key_width = (grid_width - spacing * (columns - 1)) / columns
        key_height = (grid_height - spacing * (rows - 1)) / rows
        column = args.click_key % columns
        row = args.click_key // columns
        point = QPointF(
            body_x + (body_width - grid_width) / 2 + column * (key_width + spacing) + key_width / 2,
            body_y + (body_height - grid_height) / 2 + row * (key_height + spacing) + key_height / 2,
        )
        center = keypad.mapToScene(point).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)

        def verify_click() -> None:
            if controller.selectedKey["index"] != args.click_key:
                application.exit(1)

        QTimer.singleShot(50, verify_click)

    def capture() -> None:
        image = application.primaryScreen().grabWindow(window.winId())
        if not image.save(str(target)):
            application.exit(1)
            return
        application.quit()

    capture_delay_ms = 1_500
    if args.click_key is not None:
        QTimer.singleShot(300, click_key)
    if args.press_key is not None:
        QTimer.singleShot(capture_delay_ms - 75, lambda: controller.simulateKey(args.press_key))
    QTimer.singleShot(capture_delay_ms, capture)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
