from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from . import complete_ui as complete_ui_module
from . import final_ui as final_ui_module
from . import plan_review as plan_review_module
from . import revision_ui as revision_ui_module
from .detailed_settings import DetailedSettingsPage
from .guided_input import GuidedInputPage
from .personal_debt_editor import PersonalDebtEditor
from .plan_review import check_plan, impact_ranking, scenario_summaries
from .policy_engine import SimulationEngine, recommend_monthly_contributions
from .quick_policy_editor import QuickPolicyEditor
from .revision_ui import LifeCanvasWindow as BaseLifeCanvasWindow
from .models import SocialInsuranceMode
from .tax import estimate_net_salary
from .ui import man
from .wheel_guard import install_input_wheel_guard


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """LifeCanvas with guided input and categorized compact detailed settings."""

    def __init__(self):
        self.guided_input: GuidedInputPage | None = None
        self.quick_policy: QuickPolicyEditor | None = None
        self.personal_debt_editor: PersonalDebtEditor | None = None
        self.detailed_settings: DetailedSettingsPage | None = None
        revision_ui_module.SimulationEngine = SimulationEngine
        revision_ui_module.recommend_monthly_contributions = recommend_monthly_contributions
        complete_ui_module.SimulationEngine = SimulationEngine
        final_ui_module.SimulationEngine = SimulationEngine
        plan_review_module.SimulationEngine = SimulationEngine
        super().__init__()

        # Add debt editing to the existing setup first, then reorganize all groups.
        legacy_detail = self.tabs.widget(1)
        if hasattr(legacy_detail, "widget") and legacy_detail.widget() is not None:
            legacy_layout = legacy_detail.widget().layout()
            self.personal_debt_editor = PersonalDebtEditor(self.plan)
            legacy_layout.insertWidget(max(0, legacy_layout.count() - 1), self.personal_debt_editor)
            self.personal_debt_editor.changed.connect(self._schedule_refresh)

        self.detailed_settings = DetailedSettingsPage(legacy_detail)
        self.tabs.removeTab(1)
        self.tabs.insertTab(1, self.detailed_settings, "詳細設定")

        self.guided_input = GuidedInputPage(self.plan)
        self.quick_policy = QuickPolicyEditor(self.plan)
        guided_layout = self.guided_input.widget().layout()
        # The final three items are review, actions, and stretch.
        guided_layout.insertWidget(max(0, guided_layout.count() - 3), self.quick_policy)
        self._simplify_guided_investment_group()
        self.guided_input.changed.connect(self._refresh_guided_policy_preview)
        self.quick_policy.changed.connect(self._refresh_guided_policy_preview)
        self.guided_input.applyRequested.connect(self._apply_guided_input)
        self.tabs.insertTab(1, self.guided_input, "かんたん入力")

        labels = [
            "結果",
            "かんたん入力",
            "詳細設定",
            "ライフイベント",
            "年別",
            "比較",
        ]
        for index, label in enumerate(labels):
            if index < self.tabs.count():
                self.tabs.setTabText(index, label)
        self.tabs.setCurrentIndex(1)
        self._refresh_guided_policy_preview()
        self._input_wheel_guard = install_input_wheel_guard(self)

    def _simplify_guided_investment_group(self) -> None:
        if self.guided_input is None:
            return
        group = self.guided_input.husband_household.parentWidget()
        if hasattr(group, "setTitle"):
            group.setTitle("3. 基本NISA")
        form = group.layout()
        for field in (
            self.guided_input.husband_household,
            self.guided_input.husband_child_increment,
            self.guided_input.shortfall_husband_percent,
            self.guided_input.shortfall_wife_label,
            self.guided_input.minimum_cash,
        ):
            label = form.labelForField(field) if hasattr(form, "labelForField") else None
            field.hide()
            if label is not None:
                label.hide()
        wife_label = form.labelForField(self.guided_input.wife_household) if hasattr(form, "labelForField") else None
        if wife_label is not None:
            wife_label.setText("妻の家計負担上限")

    def _refresh_guided_policy_preview(self, *_args) -> None:
        if self.guided_input is None or self.quick_policy is None:
            return
        husband_net = estimate_net_salary(
            self.guided_input.husband_income.value(),
            SocialInsuranceMode.EMPLOYEE,
            self.plan.rules,
        ).net / 12
        wife_net = estimate_net_salary(
            self.guided_input.wife_income.value(),
            SocialInsuranceMode.EMPLOYEE,
            self.plan.rules,
        ).net / 12
        includes_personal = self.guided_input.includes_personal.isChecked()
        husband_personal = 0 if includes_personal else self.guided_input.husband_personal.value()
        wife_personal = 0 if includes_personal else self.guided_input.wife_personal.value()
        wife_after_priority = max(
            0.0,
            wife_net - wife_personal - self.guided_input.wife_nisa.value(),
        )
        wife_household = min(
            self.quick_policy.wife_cap.value(),
            max(0.0, wife_after_priority - self.quick_policy.wife_threshold.value()),
            self.guided_input.living_monthly.value(),
        )
        husband_household = max(0.0, self.guided_input.living_monthly.value() - wife_household)
        husband_change = (
            husband_net
            - husband_household
            - husband_personal
            - self.guided_input.husband_nisa.value()
        )
        wife_change = (
            wife_net
            - wife_household
            - wife_personal
            - self.guided_input.wife_nisa.value()
        )
        self.guided_input.husband_flow.setText(
            "<b>夫</b><br>"
            f"手取り 約{husband_net/10_000:,.1f}万円 − 家計残額{husband_household/10_000:,.1f}万円 "
            f"− 個人{husband_personal/10_000:,.1f}万円 − NISA{self.guided_input.husband_nisa.value()/10_000:,.1f}万円"
            f"<br><b>毎月の預金増減 {self.guided_input._signed_money(husband_change)}</b>"
        )
        self.guided_input.wife_flow.setText(
            "<b>妻</b><br>"
            f"手取り 約{wife_net/10_000:,.1f}万円 − 家計{wife_household/10_000:,.1f}万円 "
            f"− 個人{wife_personal/10_000:,.1f}万円 − NISA{self.guided_input.wife_nisa.value()/10_000:,.1f}万円"
            f"<br><b>毎月の預金増減 {self.guided_input._signed_money(wife_change)}</b>"
        )
        self.guided_input.household_flow.setText(
            f"家族の生活費 月{self.guided_input.living_monthly.value()/10_000:,.1f}万円／"
            f"妻は月{self.quick_policy.wife_threshold.value()/10_000:,.1f}万円を残し、"
            f"上限{self.quick_policy.wife_cap.value()/10_000:,.1f}万円まで拠出／残額は夫負担"
        )

    def _apply_guided_input(self) -> None:
        if self.guided_input is None:
            return
        try:
            self.guided_input.apply_to(self.plan)
            if self.quick_policy is not None:
                self.quick_policy.apply_to(self.plan)
            self._sync_inputs_from_plan()
            self.h_nisa_after.set_value(self.h_nisa_before.value())
            self.recalculate()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "入力内容を確認してください", str(exc))
            return
        self.tabs.setCurrentIndex(0)

    def _apply_inputs(self) -> None:
        super()._apply_inputs()
        if self.personal_debt_editor is not None:
            self.plan.personal_debts = self.personal_debt_editor.debts()

    def _sync_inputs_from_plan(self) -> None:
        super()._sync_inputs_from_plan()
        if self.guided_input is not None:
            self.guided_input.load(self.plan)
        if self.quick_policy is not None:
            self.quick_policy.load(self.plan)
        if self.personal_debt_editor is not None:
            self.personal_debt_editor.load(self.plan)

    def _refresh_dashboard(self) -> None:
        super()._refresh_dashboard()
        if not getattr(self, "results", None):
            return

        checks = check_plan(self.plan)
        impacts = impact_ranking(self.plan, self.results)
        additions: list[str] = []

        additions.append("【入力内容のチェック】")
        if checks:
            for check in checks[:5]:
                additions.append(f"・{check.title}：{check.suggestion}")
        else:
            additions.append("・大きな矛盾や二重計上は見つかりませんでした。")

        unmet = sum(row.unmet_amount for row in self.results)
        if unmet > 1:
            additions.append(
                f"・全期間の未充足額：{unmet/10_000:,.0f}万円。現金残高とは分けて表示しています。"
            )

        additions.append("")
        additions.append("【将来資産へ影響が大きい項目】")
        if impacts:
            for index, item in enumerate(impacts, start=1):
                additions.append(
                    f"{index}. {item.label}　約{item.improvement/10_000:,.0f}万円"
                    f"（{item.note}）"
                )
        else:
            additions.append("・比較できる大きな任意支出はありません。")

        current = self.dashboard_summary.toPlainText().rstrip()
        self.dashboard_summary.setPlainText(current + "\n\n" + "\n".join(additions))
        self.dashboard_summary.setMinimumHeight(315)
        self.dashboard_summary.setMaximumHeight(430)

    def _refresh_compare(self) -> None:
        summaries = scenario_summaries(self.plan)
        headers = [
            "シナリオ",
            "夫の定年時純資産",
            "最低手元現金",
            "最終純資産",
            "警告年数",
            "前提",
        ]
        self.compare_table.setColumnCount(len(headers))
        self.compare_table.setHorizontalHeaderLabels(headers)
        self.compare_table.setRowCount(len(summaries))
        for row, summary in enumerate(summaries):
            values = [
                summary.label,
                man(summary.retirement_net_worth),
                man(summary.minimum_cash),
                man(summary.final_net_worth),
                str(summary.warning_years),
                summary.note,
            ]
            for column, value in enumerate(values):
                self.compare_table.setItem(row, column, QTableWidgetItem(value))


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
