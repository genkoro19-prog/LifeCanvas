from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QPushButton, QWidget


class DetailedSettingsInteractionSync(QObject):
    """Schedule recalculation after detailed-setting action buttons run.

    Add/remove buttons are created with the editors, but many of them do not emit a
    common top-level signal. Connecting the existing buttons directly is safer than
    installing event filters on every Qt child object and still catches the actions
    users reported as not being reflected.
    """

    def __init__(self, window, detailed_page: QWidget):
        super().__init__(window)
        self.window = window
        self.detailed_page = detailed_page
        self._pending = False
        self._buttons: list[QPushButton] = []

        recalculate_button = getattr(detailed_page, "recalculate_button", None)
        for button in detailed_page.findChildren(QPushButton):
            if button is recalculate_button:
                continue
            button.clicked.connect(self._schedule)
            self._buttons.append(button)

    def _schedule(self, *_args) -> None:
        if self._pending:
            return
        self._pending = True

        def run() -> None:
            self._pending = False
            schedule = getattr(self.window, "_schedule_refresh", None)
            if callable(schedule):
                schedule()
                return
            recalculate = getattr(self.window, "recalculate", None)
            if callable(recalculate):
                recalculate()

        # Let the editor finish adding/removing rows before reading all values.
        QTimer.singleShot(0, run)


def install_detailed_settings_interaction_sync(window, detailed_page: QWidget):
    return DetailedSettingsInteractionSync(window, detailed_page)
