"""Safe persistence for the main window's normal geometry."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QObject, QPoint, QRect, QSettings, QSize, QTimer, Slot
from PySide6.QtGui import QGuiApplication, QWindow

DEFAULT_WINDOW_SIZE = QSize(1280, 800)


@dataclass(frozen=True)
class WindowGeometry:
    """A normal, non-maximized window rectangle in Qt logical pixels."""

    x: int
    y: int
    width: int
    height: int

    def rect(self) -> QRect:
        return QRect(self.x, self.y, self.width, self.height)

    @classmethod
    def from_rect(cls, rect: QRect) -> WindowGeometry:
        return cls(rect.x(), rect.y(), rect.width(), rect.height())


def clamp_window_geometry(
    saved: WindowGeometry | None,
    displays: Sequence[QRect],
    minimum_size: QSize,
    default_size: QSize = DEFAULT_WINDOW_SIZE,
) -> WindowGeometry:
    """Return geometry that is fully visible on an available display.

    Qt stores geometry in logical pixels. A saved location can become invalid
    when a monitor is disconnected, a panel moves, or a display changes DPI.
    Keep a location on the matching display when possible; otherwise center a
    conservatively sized normal window on the primary available display.
    """

    if not displays:
        return WindowGeometry(0, 0, default_size.width(), default_size.height())

    target = displays[0]
    saved_is_visible = False
    if saved is not None:
        candidates = [
            (saved.rect().intersected(display).width() * saved.rect().intersected(display).height(), display)
            for display in displays
        ]
        best_area, best_display = max(candidates, key=lambda candidate: candidate[0])
        if best_area > 0:
            target = best_display
            saved_is_visible = True

    minimum_width = min(max(1, minimum_size.width()), target.width())
    minimum_height = min(max(1, minimum_size.height()), target.height())
    if saved is None:
        requested_width = min(default_size.width(), max(minimum_width, target.width() - 48))
        requested_height = min(default_size.height(), max(minimum_height, target.height() - 48))
    else:
        requested_width = saved.width
        requested_height = saved.height
    width = min(max(requested_width, minimum_width), target.width())
    height = min(max(requested_height, minimum_height), target.height())

    if saved is None or not saved_is_visible:
        x = target.x() + max(0, (target.width() - width) // 2)
        y = target.y() + max(0, (target.height() - height) // 2)
        return WindowGeometry(x, y, width, height)

    x = min(max(saved.x, target.x()), target.x() + target.width() - width)
    y = min(max(saved.y, target.y()), target.y() + target.height() - height)
    return WindowGeometry(x, y, width, height)


class WindowState(QObject):
    """Restore and persist main-window placement without reopening off-screen."""

    _DEFAULT_SIZE = DEFAULT_WINDOW_SIZE
    _GEOMETRY_VERSION = 2
    _RESTORE_DELAY_MS = 50
    _SAVE_DELAY_MS = 250

    def __init__(self, *, enabled: bool | None = None, settings: QSettings | None = None) -> None:
        super().__init__()
        self._enabled = enabled if enabled is not None else os.environ.get("VAYDEER_STUDIO_DISABLE_WINDOW_STATE") != "1"
        self._settings = settings or QSettings()
        self._normal_geometries: dict[int, WindowGeometry] = {}
        self._save_timers: dict[int, QTimer] = {}

    @Slot(QObject)
    def restore(self, window_object: QObject) -> None:
        """Restore a saved normal geometry, then show the QML window."""

        if not isinstance(window_object, QWindow):
            return
        if self._enabled:
            saved_geometry = self._load_geometry()
            self._set_pre_show_size(window_object, saved_geometry)
            restore_maximized = self._load_maximized()
            window_object.show()
            QTimer.singleShot(
                self._RESTORE_DELAY_MS,
                lambda target=window_object, saved=saved_geometry, maximized=restore_maximized: self._finish_restore(
                    target, saved, maximized
                ),
            )
            return
        window_object.show()

    @Slot(QObject)
    def save(self, window_object: QObject) -> None:
        """Persist the last normal rectangle and maximized state."""

        if not self._enabled or not isinstance(window_object, QWindow):
            return
        identifier = id(window_object)
        visibility = window_object.visibility()
        if visibility == QWindow.Visibility.Minimized:
            return
        maximized = visibility == QWindow.Visibility.Maximized
        if not maximized:
            self._normal_geometries[identifier] = clamp_window_geometry(
                WindowGeometry.from_rect(window_object.frameGeometry()),
                self._available_geometries(),
                self._minimum_frame_size(window_object),
                self._default_frame_size(window_object),
            )
        geometry = self._normal_geometries.get(identifier)
        if geometry is None:
            return
        self._settings.beginGroup("window")
        self._settings.setValue("version", self._GEOMETRY_VERSION)
        self._settings.setValue("x", geometry.x)
        self._settings.setValue("y", geometry.y)
        self._settings.setValue("width", geometry.width)
        self._settings.setValue("height", geometry.height)
        self._settings.setValue("maximized", maximized)
        self._settings.endGroup()
        self._settings.sync()

    def _set_pre_show_size(self, window: QWindow, saved: WindowGeometry | None) -> None:
        available = self._available_geometries()
        if saved is not None:
            geometry = clamp_window_geometry(saved, available, window.minimumSize(), self._DEFAULT_SIZE)
            window.resize(geometry.width, geometry.height)
            return

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            window.resize(self._DEFAULT_SIZE)
            return
        desktop = screen.availableGeometry()
        width = min(self._DEFAULT_SIZE.width(), max(window.minimumWidth(), desktop.width() - 96))
        height = min(self._DEFAULT_SIZE.height(), max(window.minimumHeight(), desktop.height() - 96))
        window.resize(width, height)

    def _finish_restore(self, window: QWindow, saved: WindowGeometry | None, maximized: bool) -> None:
        if not window.isVisible():
            return
        current = WindowGeometry.from_rect(window.frameGeometry())
        geometry = clamp_window_geometry(
            saved or current,
            self._available_geometries(),
            self._minimum_frame_size(window),
            self._default_frame_size(window),
        )
        margins = window.frameMargins()
        client_width = max(window.minimumWidth(), geometry.width - margins.left() - margins.right())
        client_height = max(window.minimumHeight(), geometry.height - margins.top() - margins.bottom())
        window.resize(client_width, client_height)
        window.setFramePosition(QPoint(geometry.x, geometry.y))
        self._normal_geometries[id(window)] = geometry
        self._connect_window(window)
        if maximized:
            window.showMaximized()

    def _available_geometries(self) -> list[QRect]:
        return [screen.availableGeometry() for screen in QGuiApplication.screens()]

    def _minimum_frame_size(self, window: QWindow) -> QSize:
        margins = window.frameMargins()
        return QSize(
            window.minimumWidth() + margins.left() + margins.right(),
            window.minimumHeight() + margins.top() + margins.bottom(),
        )

    def _default_frame_size(self, window: QWindow) -> QSize:
        margins = window.frameMargins()
        return QSize(
            self._DEFAULT_SIZE.width() + margins.left() + margins.right(),
            self._DEFAULT_SIZE.height() + margins.top() + margins.bottom(),
        )

    def _connect_window(self, window: QWindow) -> None:
        identifier = id(window)
        if identifier in self._save_timers:
            return
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._SAVE_DELAY_MS)
        timer.timeout.connect(lambda target=window: self.save(target))
        self._save_timers[identifier] = timer

        for signal_name in ("xChanged", "yChanged", "widthChanged", "heightChanged", "visibilityChanged"):
            signal = getattr(window, signal_name)
            signal.connect(lambda *_, target=window: self._schedule_save(target))

    def _schedule_save(self, window: QWindow) -> None:
        timer = self._save_timers.get(id(window))
        if timer is not None:
            timer.start()

    def _load_geometry(self) -> WindowGeometry | None:
        self._settings.beginGroup("window")
        version = self._integer_value("version")
        width = self._integer_value("width")
        height = self._integer_value("height")
        x = self._integer_value("x")
        y = self._integer_value("y")
        self._settings.endGroup()
        if version != self._GEOMETRY_VERSION or width <= 0 or height <= 0:
            return None
        return WindowGeometry(x, y, width, height)

    def _load_maximized(self) -> bool:
        self._settings.beginGroup("window")
        version = self._integer_value("version")
        maximized = version == self._GEOMETRY_VERSION and bool(
            self._settings.value("maximized", False, type=bool)
        )
        self._settings.endGroup()
        return maximized

    def _integer_value(self, key: str) -> int:
        value = self._settings.value(key, 0)
        if not isinstance(value, (int, float, str, bytes, bytearray)):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
