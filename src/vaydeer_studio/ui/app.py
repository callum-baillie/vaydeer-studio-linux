"""Application bootstrap for the Qt Quick desktop experience."""

from __future__ import annotations

import argparse
import sys
from importlib.resources import files

from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from vaydeer_studio.core.logging import configure_logging

from .controller import StudioController

_controller_refs: list[StudioController] = []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vaydeer Studio desktop application")
    parser.add_argument("--mock", choices=["jp1011"], help="Run against the built-in JP-1011 mock device.")
    parser.add_argument("--smoke", action="store_true", help="Launch QML then exit automatically for validation.")
    parser.add_argument("--debug", action="store_true", help="Enable safe hardware discovery logging.")
    args, qt_args = parser.parse_known_args(argv)
    configure_logging(verbose=args.debug)

    QCoreApplication.setOrganizationName("Vaydeer Studio")
    QCoreApplication.setApplicationName("Vaydeer Studio")
    application = QGuiApplication([sys.argv[0], *qt_args])
    engine = QQmlApplicationEngine()
    controller = StudioController(mock=args.mock == "jp1011")
    # Context properties do not retain Python wrappers while Qt owns the event loop.
    _controller_refs.append(controller)
    engine.rootContext().setContextProperty("vaydeerBridge", controller)
    qml_path = files("vaydeer_studio.resources.qml").joinpath("Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    if args.smoke:
        QTimer.singleShot(900, application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
