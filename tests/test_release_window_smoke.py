import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QHeaderView, QLabel

from lifecanvas.policy_engine import SimulationEngine
from lifecanvas.release_window import LifeCanvasWindow


def _close(app, window):
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


def test_release_window_cycles_tabs_opens_annual_table_and_uses_one_wife_cap():
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    try:
        window.show()
        app.processEvents()

        # The Windows release must not use ResizeToContents on a large table.
        assert window.year_table.horizontalHeader().sectionResizeMode(0) == QHeaderView.Interactive
        assert window.year_table.rowCount() == len(window.results)
        assert window.year_table.columnCount() == 26

        # Reproduce the reported operation: visit every top-level tab repeatedly,
        # including the annual table, and process the same queued paint/signals
        # that the packaged Windows application receives.
        for _ in range(8):
            for index in range(window.tabs.count()):
                window.tabs.setCurrentIndex(index)
                app.processEvents()

        # Detailed settings have their own stacked navigation. Cycle it too.
        window.tabs.setCurrentWidget(window.detailed_settings)
        for _ in range(4):
            for row in range(window.detailed_settings.categories.count()):
                window.detailed_settings.categories.setCurrentRow(row)
                app.processEvents()

        # Open and select multiple years. Detail rendering must remain valid.
        annual_page = window.year_table.parentWidget()
        window.tabs.setCurrentWidget(annual_page)
        for row in (0, len(window.results) // 2, len(window.results) - 1, 0):
            window.year_table.selectRow(row)
            app.processEvents()
            assert str(window.results[row].calendar_year) in window.year_detail.toPlainText()
        assert not window._annual_detail_error

        # Section 3 used to expose a second field with the same name as section 4.
        # Only the section-4 quick-policy field may remain visible/effective.
        duplicate = window.guided_input.wife_household
        assert duplicate.isHidden()
        assert not duplicate.isEnabled()
        visible_cap_labels = [
            label
            for label in window.guided_input.findChildren(QLabel)
            if label.text() == "妻の家計負担上限" and not label.isHidden()
        ]
        assert len(visible_cap_labels) == 1

        duplicate.set_value(250_000)
        window.quick_policy.wife_cap.set_value(80_000)
        window.guided_input.apply_to(window.plan)
        window.quick_policy.apply_to(window.plan)
        assert window.plan.wallets.wife_household_monthly == 80_000

        # The engine must treat the value as a monthly ceiling, never a ratio.
        window.plan.wallets.wife_contribution_threshold_monthly = 0
        results = SimulationEngine(window.plan).run()
        assert results
        for result in results:
            assert result.wife_household_paid <= 80_000 * result.months + 1
    finally:
        _close(app, window)
