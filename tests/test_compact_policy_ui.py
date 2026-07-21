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
        counts = window.detailed_settings.category_widget_counts
        for category in (
            "収入・働き方",
            "家計・預金",
            "NISA・投資",
            "子ども・教育",
            "住宅",
            "車",
            "借入・イベント",
            "年金・計算条件",
        ):
            assert counts[category] > 0, category
        assert window.detailed_settings.recalculate_button.isVisibleTo(window.detailed_settings)
        assert window.detailed_settings.findChildren(CollapsibleSection)
        assert window.quick_policy is not None
        assert window.quick_policy.wife_target.value() == window.plan.wallets.wife_target_cash
        assert window.personal_debt_editor is not None
        assert isinstance(app.property("lifecanvasInputWheelGuard"), InputWheelGuard)

        # A concrete details-page value must reach the plan and results through
        # the same button the user presses in the packaged application.
        previous_results = window.results
        window.wallet_editor.husband_target_cash.set_value(4_200_000)
        window.detailed_settings.recalculate_button.click()
        app.processEvents()
        assert window.plan.wallets.husband_target_cash == 4_200_000
        assert window.results is not previous_results
        assert window.detailed_settings.status.text() == "反映済み"
    finally:
        window.close()


def test_debt_quick_editor_migrates_unsupported_repayment_mode_and_preserves_details():
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
        assert restored.repayment_method == "fixed"
        assert restored.bonus_payment == 20_000
        assert restored.payment_source == "spouse"
        assert restored.notes == "育休中は夫が補填"
    finally:
        editor.close()
