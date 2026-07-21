from __future__ import annotations

import os
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLabel

from .guided_ui import LifeCanvasWindow as GuidedLifeCanvasWindow


class LifeCanvasWindow(GuidedLifeCanvasWindow):
    """Release window with defensive guards for Windows tab and table rendering."""

    def __init__(self):
        # These attributes are needed because base-class constructors call the
        # virtual refresh methods before this constructor returns.
        self._annual_refreshing = False
        self._annual_detail_error = False
        super().__init__()

        self._hide_duplicate_wife_cap_input()
        self._configure_safe_annual_table()
        self.tabs.currentChanged.connect(self._on_release_tab_changed)

    def _configure_annual_table(self) -> None:
        """Configure the annual table without expensive Windows size probing."""
        super()._configure_annual_table()
        self._configure_safe_annual_table()

    def _configure_safe_annual_table(self) -> None:
        table = getattr(self, "year_table", None)
        if table is None:
            return

        # ResizeToContents asks Windows/Qt to measure every cell when the page
        # becomes visible. With a long plan and 26 columns that can re-enter
        # painting and selection handlers. Interactive widths keep opening the
        # annual page deterministic and still allow manual resizing.
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(118)
        table.setColumnWidth(0, 76)
        table.setColumnWidth(1, 82)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setSortingEnabled(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def _refresh_table(self) -> None:
        """Populate the annual table without firing half-built selection events."""
        table = getattr(self, "year_table", None)
        if table is None:
            super()._refresh_table()
            return
        if self._annual_refreshing:
            return

        self._annual_refreshing = True
        previous_row = table.currentRow()
        updates_enabled = table.updatesEnabled()
        blocker = QSignalBlocker(table)
        table.setUpdatesEnabled(False)
        try:
            super()._refresh_table()
            if getattr(self, "results", None):
                row = previous_row if 0 <= previous_row < len(self.results) else 0
                table.selectRow(row)
        finally:
            table.setUpdatesEnabled(updates_enabled)
            del blocker
            self._annual_refreshing = False

        if self._annual_tab_is_current():
            QTimer.singleShot(0, self._show_selected_year)

    def _show_selected_year(self) -> None:
        """Show year details only after a complete, valid table selection exists."""
        if self._annual_refreshing:
            return
        table = getattr(self, "year_table", None)
        results = getattr(self, "results", None) or []
        if table is None:
            return
        row = table.currentRow()
        if not 0 <= row < len(results):
            return

        try:
            super()._show_selected_year()
            self._annual_detail_error = False
        except Exception:  # A UI callback must never terminate the packaged app.
            self._annual_detail_error = True
            detail = getattr(self, "year_detail", None)
            if detail is not None:
                detail.setPlainText(
                    "年別詳細の表示中にエラーが発生しました。\n"
                    "入力内容は保持されています。LifeCanvasのログを確認してください。"
                )
            self._write_ui_error("annual-detail")

    def _annual_tab_is_current(self) -> bool:
        table = getattr(self, "year_table", None)
        tabs = getattr(self, "tabs", None)
        return bool(table is not None and tabs is not None and tabs.currentWidget() is table.parentWidget())

    def _on_release_tab_changed(self, _index: int) -> None:
        current = self.tabs.currentWidget()
        table = getattr(self, "year_table", None)
        if table is not None and current is table.parentWidget():
            QTimer.singleShot(0, self._ensure_annual_selection)
            return

        detailed = getattr(self, "detailed_settings", None)
        if detailed is not None and current is detailed:
            if detailed.categories.currentRow() < 0:
                detailed.categories.setCurrentRow(0)

    def _ensure_annual_selection(self) -> None:
        table = getattr(self, "year_table", None)
        results = getattr(self, "results", None) or []
        if table is None or not results:
            return
        if not 0 <= table.currentRow() < len(results):
            blocker = QSignalBlocker(table)
            table.selectRow(0)
            del blocker
        self._show_selected_year()
        table.viewport().update()

    def _hide_duplicate_wife_cap_input(self) -> None:
        """Keep section 4 as the single source of truth for the wife's cap."""
        guided = getattr(self, "guided_input", None)
        quick = getattr(self, "quick_policy", None)
        if guided is None or quick is None:
            return

        duplicate = getattr(guided, "wife_household", None)
        if duplicate is None:
            return
        duplicate.setObjectName("deprecatedGuidedWifeHouseholdCap")
        duplicate.setEnabled(False)
        duplicate.hide()

        parent = duplicate.parentWidget()
        form = parent.layout() if parent is not None else None
        label = form.labelForField(duplicate) if hasattr(form, "labelForField") else None
        if isinstance(label, QLabel):
            label.hide()

        # Preserve compatible values for old save data while section 4 remains
        # the only visible and effective editor.
        duplicate.set_value(quick.wife_cap.value())

    @staticmethod
    def _write_ui_error(context: str) -> None:
        try:
            base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
            log_dir = base / "LifeCanvas" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "ui-errors.log").open("a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] {context}\n")
                handle.write(traceback.format_exc())
        except OSError:
            pass
