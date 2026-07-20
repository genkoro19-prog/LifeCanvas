import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lifecanvas.detailed_settings import DetailedSettingsPage
from lifecanvas.guided_ui import LifeCanvasWindow
from lifecanvas.wheel_guard import InputWheelGuard


def test_guided_window_exposes_compact_detail_and_policy_editors():
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    try:
        assert window.tabs.tabText(1) == "かんたん入力"
        assert window.tabs.tabText(2) == "詳細設定"
        assert isinstance(window.detailed_settings, DetailedSettingsPage)
        assert window.detailed_settings.categories.count() == 9
        assert window.quick_policy is not None
        assert window.personal_debt_editor is not None
        assert isinstance(app.property("lifecanvasInputWheelGuard"), InputWheelGuard)
    finally:
        window.close()
