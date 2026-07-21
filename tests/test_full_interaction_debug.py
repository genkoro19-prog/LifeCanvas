from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from lifecanvas.guided_ui import LifeCanvasWindow
from lifecanvas.pdf_report_v2 import _chart_png_bytes, export_pdf


def _app():
    return QApplication.instance() or QApplication([])


def _process(app):
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


def _close(app, window):
    window.close()
    window.deleteLater()
    _process(app)


def test_detail_recalculate_button_applies_field_change():
    app = _app()
    window = LifeCanvasWindow()
    try:
        window.wallet_editor.husband_target_cash.set_value(4_200_000)
        window.detailed_settings.recalculate_button.click()
        _process(app)
        assert window.plan.wallets.husband_target_cash == pytest.approx(4_200_000)
        assert window.detailed_settings.status.text() == "反映済み"
    finally:
        _close(app, window)


def test_dynamic_editor_button_schedules_refresh():
    app = _app()
    window = LifeCanvasWindow()
    try:
        calls = []
        original = window._schedule_refresh

        def tracked(*args):
            calls.append(True)
            return original(*args)

        window._schedule_refresh = tracked
        button = next(
            button
            for button in window.detailed_settings.findChildren(QPushButton)
            if "追加" in button.text() and button.isEnabled()
        )
        # Send a real mouse release without showing the full top-level window.
        QTest.mouseClick(button, Qt.LeftButton)
        _process(app)
        assert calls, f"{button.text()} did not schedule recalculation"
    finally:
        _close(app, window)


def test_pdf_chart_png_is_real_and_embedded(tmp_path: Path):
    app = _app()
    window = LifeCanvasWindow()
    try:
        png = _chart_png_bytes(window.results, window.plan.wallets.mode == "separate")
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(png) > 20_000
        target = export_pdf(window.plan, window.results, tmp_path / "with-chart.pdf")
        raw_pdf = target.read_bytes()
        assert raw_pdf.startswith(b"%PDF")
        assert b"/Image" in raw_pdf
        assert target.stat().st_size > 20_000
    finally:
        _close(app, window)
