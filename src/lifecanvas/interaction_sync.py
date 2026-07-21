from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLineEdit, QWidget


class DetailedSettingsInteractionSync(QObject):
    """Keep dynamically-created detailed-setting controls in the recalculation loop.

    Editors add/remove table rows after the main window has connected its original
    signals. This event filter catches those later controls as well, without relying
    on every editor to remember to emit a custom changed signal.
    """

    def __init__(self, window, detailed_page: QWidget):
        super().__init__(window)
        self.window = window
        self.detailed_page = detailed_page
        self._pending = False
        detailed_page.installEventFilter(self)
        for child in detailed_page.findChildren(QWidget):
            child.installEventFilter(self)

    def _inside_details(self, widget: QWidget) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is self.detailed_page:
                return True
            current = current.parentWidget()
        return False

    def _schedule(self) -> None:
        if self._pending:
            return
        self._pending = True

        def run() -> None:
            self._pending = False
            schedule = getattr(self.window, "_schedule_refresh", None)
            if callable(schedule):
                schedule()
            else:
                recalculate = getattr(self.window, "recalculate", None)
                if callable(recalculate):
                    recalculate()

        # Run after the clicked button has finished adding/removing/editing rows.
        QTimer.singleShot(0, run)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                child.installEventFilter(self)
                for descendant in child.findChildren(QWidget):
                    descendant.installEventFilter(self)
            return False

        if not isinstance(watched, QWidget) or not self._inside_details(watched):
            return False

        if event.type() == QEvent.FocusOut and isinstance(watched, (QLineEdit, QComboBox)):
            self._schedule()
        elif event.type() == QEvent.MouseButtonRelease and isinstance(
            watched, (QAbstractButton, QComboBox)
        ):
            self._schedule()
        return False


def install_detailed_settings_interaction_sync(window, detailed_page: QWidget):
    return DetailedSettingsInteractionSync(window, detailed_page)
