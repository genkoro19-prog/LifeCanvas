from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QWidget,
)

from .policy_audit import install_policy_audit

# GuidedUI imports this module before constructing the window, so the audited
# debt lifecycle is active for the very first dashboard calculation.
install_policy_audit()


class InputWheelGuard(QObject):
    """Prevent wheel changes on selectors while preserving page scrolling."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.Wheel:
            return False
        if not isinstance(watched, (QAbstractSpinBox, QComboBox)):
            return False
        parent = watched.parentWidget()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                bar = parent.verticalScrollBar()
                delta = event.angleDelta().y()
                if delta:
                    bar.setValue(bar.value() - delta)
                break
            parent = parent.parentWidget()
        return True


def install_input_wheel_guard(root: QWidget | QApplication) -> InputWheelGuard:
    """Install the guard only on input widgets, never on QApplication itself."""

    app = QApplication.instance()
    if app is None:
        raise RuntimeError("QApplication must exist before installing the wheel guard")
    guard = getattr(app, "_lifecanvas_input_wheel_guard", None)
    if not isinstance(guard, InputWheelGuard):
        guard = InputWheelGuard(app)
        setattr(app, "_lifecanvas_input_wheel_guard", guard)
        app.setProperty("lifecanvasInputWheelGuard", guard)

    roots: list[QWidget]
    if isinstance(root, QApplication):
        roots = list(root.topLevelWidgets())
    else:
        roots = [root]
    for container in roots:
        targets: list[QWidget] = []
        if isinstance(container, (QAbstractSpinBox, QComboBox)):
            targets.append(container)
        targets.extend(container.findChildren(QAbstractSpinBox))
        targets.extend(container.findChildren(QComboBox))
        for target in targets:
            target.installEventFilter(guard)

        # GuidedUI calls this installer after all tabs and editors exist. Hook the
        # completion audit here so the audit remains independent of constructor order.
        if hasattr(container, "guided_input") and hasattr(container, "detailed_settings"):
            from .completion_audit import install_completion_audit

            install_completion_audit(container)
    return guard
