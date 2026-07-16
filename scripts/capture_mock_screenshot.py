#!/usr/bin/env python3
"""Render the JP-1011 mock UI to a PNG for visual regression inspection."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from importlib.resources import files

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from vaydeer_studio.ui.controller import StudioController

_refs: list[StudioController] = []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", type=int, default=0, choices=range(6))
    parser.add_argument("--output", type=Path, default=Path("screenshots/mock-jp1011.png"))
    parser.add_argument("--live", action="store_true", help="Render the connected keypad without writing to it")
    parser.add_argument("--press-key", type=int, choices=range(9), help="Capture a mock tester key while pressed")
    parser.add_argument("--pending-key", type=int, choices=range(9), help="Stage a visible mock mapping change")
    parser.add_argument("--width", type=int, default=1440, help="Window width used for the rendered capture")
    parser.add_argument("--height", type=int, default=900, help="Window height used for the rendered capture")
    args = parser.parse_args()
    target = args.output
    target.parent.mkdir(parents=True, exist_ok=True)
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
    window.setProperty("navIndex", args.page)
    if args.pending_key is not None:
        controller.selectKey(args.pending_key)
        controller.saveKey("Keyboard key", "Draft", "F13")
    controller.setActivePage(args.page)

    def capture() -> None:
        image = application.primaryScreen().grabWindow(window.winId())
        if not image.save(str(target)):
            application.exit(1)
            return
        application.quit()

    capture_delay_ms = 1_500
    if args.press_key is not None:
        QTimer.singleShot(capture_delay_ms - 75, lambda: controller.simulateKey(args.press_key))
    QTimer.singleShot(capture_delay_ms, capture)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
