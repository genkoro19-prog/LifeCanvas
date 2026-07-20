import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lifecanvas.detailed_settings import CollapsibleSection, DetailedSettingsPage
from lifecanvas.guided_ui import LifeCanvasWindow
from lifecanvas.models import PersonalDebt
from lifecanvas.personal_debt_editor import PersonalDebtEditor
from lifecanvas.sample import build_genki_family_plan
from lifecanvas.wheel_guard import InputWheelGuard


def test_guided_window_exposes_compact_detail_and_policy_editors():
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    try:
        assert window.tabs.tabText(1) == "かんたん入力"
        assert window.tabs.tabText(2) == "詳細設定"
        assert isinstance(window.detailed_settings, DetailedSettingsPage)
        assert window.detailed_settings.categories.count() == 9
        assert window.detailed_settings.recalculate_button.isVisibleTo(window.detailed_settings)
        assert window.detailed_settings.findChildren(CollapsibleSection)
        assert window.quick_policy is not None
        assert window.personal_debt_editor is not None
        assert isinstance(app.property("lifecanvasInputWheelGuard"), InputWheelGuard)
    finally:
        window.close()


def test_debt_quick_editor_preserves_detailed_assumptions():
    app = QApplication.instance() or QApplication([])
    plan = build_genki_family_plan()
    plan.personal_debts = [
        PersonalDebt(
            debt_id="student-loan",
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=96,
            current_balance=1_200_000,
            principal=1_500_000,
            annual_interest_rate=1.25,
            repayment_method="equal_payment",
            bonus_payment=20_000,
            payment_source="spouse",
            notes="育休中は夫が補填",
        )
    ]
    editor = PersonalDebtEditor(plan)
    try:
        restored = editor.debts()[0]
        assert restored.current_balance == 1_200_000
        assert restored.principal == 1_500_000
        assert restored.annual_interest_rate == 1.25
        assert restored.repayment_method == "equal_payment"
        assert restored.bonus_payment == 20_000
        assert restored.payment_source == "spouse"
        assert restored.notes == "育休中は夫が補填"
    finally:
        editor.close()
