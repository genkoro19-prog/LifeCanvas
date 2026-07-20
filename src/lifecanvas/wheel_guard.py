from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox


class InputWheelGuard(QObject):
    """Prevent wheel changes on selectors while preserving page scrolling."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Wheel or not isinstance(watched, (QAbstractSpinBox, QComboBox)):
            return False
        parent = watched.parent()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                bar = parent.verticalScrollBar()
                delta = event.angleDelta().y()
                if delta:
                    bar.setValue(bar.value() - delta)
                break
            parent = parent.parent()
        return True


def install_input_wheel_guard(app: QApplication) -> InputWheelGuard:
    existing = app.property("lifecanvasInputWheelGuard")
    if isinstance(existing, InputWheelGuard):
        return existing
    guard = InputWheelGuard(app)
    app.installEventFilter(guard)
    app.setProperty("lifecanvasInputWheelGuard", guard)
    return guard
