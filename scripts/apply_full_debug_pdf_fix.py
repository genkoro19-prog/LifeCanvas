from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1) Reliable PDF image embedding via QTextDocument resource instead of data URI.
pdf = ROOT / "src/lifecanvas/pdf_report_v2.py"
text = pdf.read_text(encoding="utf-8")
text = text.replace("import base64\n", "")
text = text.replace("from PySide6.QtCore import QMarginsF, QSizeF\n", "from PySide6.QtCore import QMarginsF, QSizeF, QUrl\n")
text = text.replace("from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument\n", "from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument\n")
text = text.replace(
    "def _chart_data_uri(results: list[YearResult], separate: bool = False) -> str:\n",
    "def _chart_png_bytes(results: list[YearResult], separate: bool = False) -> bytes:\n",
)
text = text.replace(
    '    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")\n',
    "    return buffer.getvalue()\n",
)
text = text.replace("    chart = _chart_data_uri(results, separate)\n", "    chart_png = _chart_png_bytes(results, separate)\n")
text = text.replace("<img class='chart' src='{chart}' />", "<img class='chart' src='lifecanvas-chart.png' />")
text = text.replace(
    "    document.setDocumentMargin(0)\n    document.setPageSize(QSizeF(writer.width(), writer.height()))\n    document.setHtml(html)\n",
    "    document.setDocumentMargin(0)\n    document.setPageSize(QSizeF(writer.width(), writer.height()))\n    chart_image = QImage.fromData(chart_png, b'PNG')\n    if chart_image.isNull():\n        raise ValueError('PDF用グラフ画像を生成できませんでした。')\n    document.addResource(\n        QTextDocument.ImageResource,\n        QUrl('lifecanvas-chart.png'),\n        chart_image,\n    )\n    document.setHtml(html)\n",
)
if "_chart_data_uri" in text or "src='{chart}'" in text:
    raise RuntimeError("PDF chart patch was not applied completely")
pdf.write_text(text, encoding="utf-8")

# 2) Central interaction watcher for dynamically created detailed-setting controls.
interaction = ROOT / "src/lifecanvas/interaction_sync.py"
interaction.write_text('''from __future__ import annotations

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
''', encoding="utf-8")

# 3) Install watcher after all pages and dynamic editors have been constructed.
guided = ROOT / "src/lifecanvas/guided_ui.py"
text = guided.read_text(encoding="utf-8")
text = text.replace(
    "from .wheel_guard import install_input_wheel_guard\n",
    "from .wheel_guard import install_input_wheel_guard\nfrom .interaction_sync import install_detailed_settings_interaction_sync\n",
)
text = text.replace(
    "        self._input_wheel_guard = install_input_wheel_guard(self)\n",
    "        self._input_wheel_guard = install_input_wheel_guard(self)\n        self._detail_interaction_sync = install_detailed_settings_interaction_sync(\n            self, self.detailed_settings\n        )\n",
)
if "_detail_interaction_sync" not in text:
    raise RuntimeError("guided UI interaction sync patch failed")
guided.write_text(text, encoding="utf-8")

# 4) Make the detail-page button use one explicit signal path and show feedback.
details = ROOT / "src/lifecanvas/detailed_settings.py"
text = details.read_text(encoding="utf-8")
text = text.replace("        status = QLabel(\"変更内容は自動計算されます\")\n", "        self.status = QLabel(\"変更内容は自動計算されます\")\n")
text = text.replace("        status.setStyleSheet(\"color:#667085;\")\n", "        self.status.setStyleSheet(\"color:#667085;\")\n")
text = text.replace("        toolbar.addWidget(status)\n", "        toolbar.addWidget(self.status)\n")
text = text.replace(
    "    def _request_recalculation(self) -> None:\n        self.recalculateRequested.emit()\n        top_level = self.window()\n        recalculate = getattr(top_level, \"recalculate\", None)\n        if callable(recalculate):\n            recalculate()\n",
    "    def _request_recalculation(self) -> None:\n        self.status.setText(\"再計算しています…\")\n        self.recalculateRequested.emit()\n        top_level = self.window()\n        recalculate = getattr(top_level, \"recalculate\", None)\n        if callable(recalculate):\n            recalculate()\n        self.status.setText(\"反映済み\")\n",
)
details.write_text(text, encoding="utf-8")

# 5) Add regression tests for button reflection, dynamic controls, and PDF chart resource.
test_path = ROOT / "tests/test_full_interaction_debug.py"
test_path.write_text('''from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
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
    window.wallet_editor.husband_target_cash.set_value(4_200_000)
    window.detailed_settings.recalculate_button.click()
    _process(app)
    assert window.plan.wallets.husband_target_cash == pytest.approx(4_200_000)
    assert window.detailed_settings.status.text() == "反映済み"
    _close(app, window)


def test_dynamic_editor_button_schedules_refresh():
    app = _app()
    window = LifeCanvasWindow()
    calls = []
    original = window._schedule_refresh

    def tracked(*args):
        calls.append(True)
        return original(*args)

    window._schedule_refresh = tracked
    button = next(
        button
        for button in window.detailed_settings.findChildren(QPushButton)
        if "追加" in button.text()
    )
    button.click()
    _process(app)
    assert calls, f"{button.text()} did not schedule recalculation"
    _close(app, window)


def test_pdf_chart_png_is_real_and_embedded(tmp_path: Path):
    app = _app()
    window = LifeCanvasWindow()
    png = _chart_png_bytes(window.results, window.plan.wallets.mode == "separate")
    assert png.startswith(b"\\x89PNG\\r\\n\\x1a\\n")
    assert len(png) > 20_000
    target = export_pdf(window.plan, window.results, tmp_path / "with-chart.pdf")
    assert target.exists()
    # A report with the high-resolution chart should be substantially larger than text-only output.
    assert target.stat().st_size > 80_000
    _close(app, window)
''', encoding="utf-8")
