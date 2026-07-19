from __future__ import annotations

from copy import deepcopy

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .cashflow_event_editor import CashFlowEventEditor
from .child_editor import ChildEditor
from .complete_ui import LifeCanvasWindow as CompleteLifeCanvasWindow
from .engine import SimulationEngine
from .family import apply_work_stages_for_child, infer_work_reference_child
from .insights import analyze_plan, dominant_expense
from .models import IncomePeriod
from .plotting import configure_japanese_matplotlib
from .ui import MetricCard, man


class LifeCanvasWindow(CompleteLifeCanvasWindow):
    """Desktop UI with flexible family, free events, and local plan analysis."""

    def _build_dashboard(self) -> QWidget:
        configure_japanese_matplotlib()
        page = QWidget()
        layout = QVBoxLayout(page)
        cards = QGridLayout()
        self.card_retirement = MetricCard("夫60歳時点の純資産")
        self.card_cash = MetricCard("最低現預金")
        self.card_shortage = MetricCard("資金ショート")
        self.card_move = MetricCard("住み替え時のローン残高")
        self.card_outlook = MetricCard("将来判定")
        self.card_final = MetricCard("最終年の純資産")
        card_items = [
            self.card_retirement,
            self.card_cash,
            self.card_shortage,
            self.card_move,
            self.card_outlook,
            self.card_final,
        ]
        for index, card in enumerate(card_items):
            cards.addWidget(card, index // 3, index % 3)
        layout.addLayout(cards)

        self.figure = Figure(figsize=(10, 4.4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)

        self.dashboard_summary = QTextEdit()
        self.dashboard_summary.setReadOnly(True)
        self.dashboard_summary.setMaximumHeight(145)
        layout.addWidget(self.dashboard_summary)

        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMaximumHeight(110)
        layout.addWidget(self.dashboard_warnings)
        return page

    def _build_setup(self) -> QWidget:
        scroll = super()._build_setup()
        layout = scroll.widget().layout()

        family_group = self.first_child_offset.parentWidget()
        family_form = family_group.layout()
        for field in (self.first_child_offset, self.second_child_offset):
            label = family_form.labelForField(field) if hasattr(family_form, "labelForField") else None
            if label:
                label.hide()
            field.hide()
        if hasattr(family_group, "setTitle"):
            family_group.setTitle("車のライフイベント")

        self.child_editor = ChildEditor(self.plan)
        insert_at = layout.indexOf(self.husband_income_editor)
        layout.insertWidget(max(0, insert_at), self.child_editor)
        self.cashflow_event_editor = CashFlowEventEditor(self.plan)
        layout.insertWidget(max(0, insert_at + 1), self.cashflow_event_editor)
        self._update_work_labels()
        return scroll

    def _configure_annual_table(self) -> None:
        headers = [
            "年",
            "夫/妻",
            "夫年収",
            "妻年収",
            "年金",
            "退職金等",
            "イベント収入",
            "収入合計",
            "生活費",
            "住宅",
            "教育",
            "車",
            "イベント支出",
            "生活収支",
            "現預金",
            "投資",
            "純資産",
        ]
        self.year_table.setColumnCount(len(headers))
        self.year_table.setHorizontalHeaderLabels(headers)
        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def _update_work_labels(self) -> None:
        work_form = self.w_nursery.parentWidget().layout()
        labels = [
            (self.w_before, "妻・出産前"),
            (self.w_nursery, "妻・基準の子が保育園期"),
            (self.w_elementary, "妻・基準の子が小学生期"),
            (self.w_junior, "妻・基準の子が中学生以降"),
        ]
        for field, text in labels:
            label = work_form.labelForField(field) if hasattr(work_form, "labelForField") else None
            if label:
                label.setText(text)

    def _apply_inputs(self) -> None:
        start_month = self.start_month.int_value()
        if not 1 <= start_month <= 12:
            raise ValueError("開始月は1〜12で入力してください。")

        self.plan.start_month = start_month
        self.plan.initial_cash = self.initial_cash.value()
        self.plan.living_cost.monthly_amount = self.living_monthly.value()
        self.plan.husband.retirement_age = self.h_retire.int_value()
        self.plan.husband.pension_start_age = self.h_pension_age.int_value()
        self.plan.husband.annual_pension = self.h_pension.value()
        self.plan.wife.retirement_age = self.w_retire.int_value()
        self.plan.wife.pension_start_age = self.w_pension_age.int_value()
        self.plan.wife.annual_pension = self.w_pension.value()

        self.plan.children = self.child_editor.children()
        reference_child = self.child_editor.reference_child_name()
        apply_work_stages_for_child(self.plan, reference_child)
        self.plan.cashflow_events = self.cashflow_event_editor.events()

        self.plan.car.purchase_offset = self.car_purchase_offset.int_value()
        cycle = self.car_cycle.int_value()
        self.plan.car.replacement_cycle_years = cycle if cycle > 0 else None

        self.plan.income_periods = [
            period for period in self.plan.income_periods if period.owner != "husband"
        ] + self.husband_income_editor.periods()
        for period in self.plan.income_periods:
            if (
                period.owner == "husband"
                and "継続雇用" in period.label
                and period.start_age == self.plan.husband.retirement_age
            ):
                period.end_age = self.plan.husband.pension_start_age

        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband" and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.plan.husband.annual_gross_income = current_period.annual_gross_income if current_period else 0

        stage_map = {stage.key: stage for stage in self.plan.wife_work_stages}
        stage_map["full_time"].annual_gross_income = self.w_before.value()
        stage_map["nursery"].annual_gross_income = self.w_nursery.value()
        stage_map["elementary"].annual_gross_income = self.w_elementary.value()
        stage_map["junior_high"].annual_gross_income = self.w_junior.value()

        mortgage = self.plan.housing.mortgage
        mortgage.principal = self.loan_amount.value()
        self.plan.housing.purchase_price = mortgage.principal
        mortgage.term_years = self.loan_term.int_value()
        mortgage.initial_rate_percent = self.rate_start.value()
        mortgage.annual_rate_step_percent = self.rate_step.value()
        mortgage.max_rate_percent = self.rate_max.value()
        self.plan.housing.move_offset = self.move_offset.int_value()
        self.plan.housing.new_home_monthly_cost = self.new_home.value()
        self.plan.housing.old_home_net_rent_annual = self.rental_income.value()

        self.plan.nisa_accounts[0].monthly_contribution = self.h_nisa_before.value()
        self.plan.nisa_accounts[0].contribution_changes[5] = self.h_nisa_after.value()
        self.plan.nisa_accounts[1].monthly_contribution = self.w_nisa.value()

        self._upsert_retirement_income(
            "husband",
            "夫の退職金",
            self.plan.husband.retirement_age,
            self.h_retirement_lump.value(),
        )
        self._upsert_retirement_income(
            "wife",
            "妻の退職金",
            self.plan.wife.retirement_age,
            self.w_retirement_lump.value(),
        )
        if hasattr(self, "plan_name_edit"):
            self.plan.name = self.plan_name_edit.text().strip() or "LifeCanvas Plan"

    def _sync_inputs_from_plan(self) -> None:
        self.plan_name_edit.setText(self.plan.name)
        self.start_month.set_value(self.plan.start_month)
        self.initial_cash.set_value(self.plan.initial_cash)
        self.living_monthly.set_value(self.plan.living_cost.monthly_amount)
        self.child_editor.load(self.plan)
        self.cashflow_event_editor.load(self.plan)
        inferred = infer_work_reference_child(self.plan)
        if inferred:
            index = self.child_editor.reference_child.findText(inferred)
            if index >= 0:
                self.child_editor.reference_child.setCurrentIndex(index)

        self.car_purchase_offset.set_value(self.plan.car.purchase_offset)
        self.car_cycle.set_value(self.plan.car.replacement_cycle_years or 0)
        self.husband_income_editor.load(self.plan)
        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband" and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.h_income.set_value(
            current_period.annual_gross_income if current_period else self.plan.husband.annual_gross_income
        )
        self.h_retire.set_value(self.plan.husband.retirement_age)
        self.h_retirement_lump.set_value(self._retirement_amount("husband"))
        self.h_pension_age.set_value(self.plan.husband.pension_start_age)
        self.h_pension.set_value(self.plan.husband.annual_pension)
        self.w_retire.set_value(self.plan.wife.retirement_age)
        self.w_retirement_lump.set_value(self._retirement_amount("wife"))
        self.w_pension_age.set_value(self.plan.wife.pension_start_age)
        self.w_pension.set_value(self.plan.wife.annual_pension)

        stages = {stage.key: stage for stage in self.plan.wife_work_stages}
        self.w_before.set_value(stages["full_time"].annual_gross_income)
        self.w_nursery.set_value(stages["nursery"].annual_gross_income)
        self.w_elementary.set_value(stages["elementary"].annual_gross_income)
        self.w_junior.set_value(stages["junior_high"].annual_gross_income)

        mortgage = self.plan.housing.mortgage
        self.loan_amount.set_value(mortgage.principal)
        self.loan_term.set_value(mortgage.term_years)
        self.rate_start.set_value(mortgage.initial_rate_percent)
        self.rate_step.set_value(mortgage.annual_rate_step_percent)
        self.rate_max.set_value(mortgage.max_rate_percent)
        self.move_offset.set_value(self.plan.housing.move_offset or 0)
        self.new_home.set_value(self.plan.housing.new_home_monthly_cost)
        self.rental_income.set_value(self.plan.housing.old_home_net_rent_annual)
        self.h_nisa_before.set_value(self.plan.nisa_accounts[0].monthly_contribution)
        self.h_nisa_after.set_value(self.plan.nisa_accounts[0].contribution_changes.get(5, 0))
        self.w_nisa.set_value(self.plan.nisa_accounts[1].monthly_contribution)
        self._update_work_labels()

    def _refresh_dashboard(self) -> None:
        configure_japanese_matplotlib()
        retirement = next(
            (row for row in self.results if row.husband_age == self.plan.husband.retirement_age),
            self.results[-1],
        )
        minimum_cash = min(self.results, key=lambda row: row.cash_end)
        shortage = [
            row
            for row in self.results
            if any("資金ショート" in warning for warning in row.warnings)
        ]
        insight = analyze_plan(self.plan, self.results)

        self.card_retirement.value.setText(man(retirement.net_worth))
        self.card_retirement.note.setText(f"{retirement.calendar_year}年")
        self.card_cash.value.setText(man(minimum_cash.cash_end))
        self.card_cash.note.setText(f"最低年: {minimum_cash.calendar_year}年")
        self.card_shortage.value.setText("あり" if shortage else "なし")
        self.card_shortage.note.setText(
            f"{shortage[0].calendar_year}年から" if shortage else "現在の前提では発生しません"
        )
        if self.plan.housing.move_offset is None:
            self.card_move.value.setText("なし")
            self.card_move.note.setText("住み替えを設定していません")
        else:
            move = self.results[min(self.plan.housing.move_offset, len(self.results) - 1)]
            self.card_move.value.setText(man(move.mortgage_balance))
            self.card_move.note.setText(f"住み替え年: {move.calendar_year}年")
        self.card_outlook.value.setText(insight.status)
        self.card_outlook.note.setText(insight.status_note)
        self.card_final.value.setText(man(insight.final_net_worth))
        self.card_final.note.setText(f"{self.results[-1].calendar_year}年")

        self.figure.clear()
        axis = self.figure.add_subplot(111)
        years = [row.calendar_year for row in self.results]
        axis.plot(years, [row.net_worth / 10_000 for row in self.results], label="純資産")
        axis.plot(years, [row.cash_end / 10_000 for row in self.results], label="現預金")
        axis.plot(
            years,
            [row.investments_market_value / 10_000 for row in self.results],
            label="投資資産",
        )
        axis.plot(
            years,
            [-row.mortgage_balance / 10_000 for row in self.results],
            label="住宅ローン（負債）",
            linestyle="--",
        )
        axis.axhline(0, linewidth=1, alpha=0.45)
        axis.set_title("資産・負債の推移")
        axis.set_xlabel("年")
        axis.set_ylabel("万円")
        axis.grid(True, alpha=0.25)
        axis.legend(ncol=4, loc="best")
        self.figure.tight_layout()
        self.canvas.draw()

        difficult_lines = []
        for row in insight.difficult_years:
            difficult_lines.append(
                f"・{row.calendar_year}年　収支 {man(row.living_surplus)}　主な支出: {dominant_expense(row)}"
            )
        summary = [
            f"判定: {insight.status} — {insight.status_note}",
            f"老後期間の最低現預金: {man(insight.retirement_min_cash)}",
            "",
            "収支が厳しい年:",
            *difficult_lines,
        ]
        self.dashboard_summary.setPlainText("\n".join(summary))

        self.dashboard_warnings.clear()
        for result in self.results:
            for warning in result.warnings:
                self.dashboard_warnings.addItem(f"{result.calendar_year}年: {warning}")
        if self.dashboard_warnings.count() == 0:
            self.dashboard_warnings.addItem("重大な資金ショートはありません。")

    def _refresh_table(self) -> None:
        self.year_table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            values = [
                str(result.calendar_year),
                f"{result.husband_age}/{result.wife_age}",
                man(result.husband_gross),
                man(result.wife_gross),
                man(result.pension_income),
                man(result.one_time_income),
                man(result.life_event_income),
                man(result.total_income),
                man(result.core_living_cost),
                man(result.housing_cost),
                man(result.education_cost),
                man(result.car_cost),
                man(result.life_event_expense),
                man(result.living_surplus),
                man(result.cash_end),
                man(result.investments_market_value),
                man(result.net_worth),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.year_table.setItem(row, column, item)
        self.year_table.selectRow(0)

    def _set_year_detail(self, widget: QTextEdit, offset: int, events: list) -> None:
        result = self.results[offset]
        children = "、".join(
            f"{name}{age}歳" for name, age in result.children_ages.items()
        ) or "なし"
        event_lines = [
            f"・{event.title}: {event.detail}" for event in events
        ] or [f"・{event}" for event in result.events] or ["・なし"]
        lines = [
            f"{result.calendar_year}年（夫{result.husband_age}歳・妻{result.wife_age}歳）",
            f"子ども: {children}",
            "",
            "イベント:",
            *event_lines,
            "",
            f"夫年収 {man(result.husband_gross)} / 妻年収 {man(result.wife_gross)}",
            f"給与手取り {man(result.salary_net)} / 年金 {man(result.pension_income)}",
            f"退職金等 {man(result.one_time_income)} / イベント収入 {man(result.life_event_income)}",
            f"給付 {man(result.benefits)} / 家賃 {man(result.rental_income)}",
            f"収入合計 {man(result.total_income)}",
            "",
            f"生活費 {man(result.core_living_cost)} / 住宅 {man(result.housing_cost)}",
            f"教育 {man(result.education_cost)} / 車 {man(result.car_cost)}",
            f"イベント支出 {man(result.life_event_expense)}",
            f"生活収支 {man(result.living_surplus)}",
            f"現預金 {man(result.cash_end)} / 純資産 {man(result.net_worth)}",
        ]
        if result.warnings:
            lines.extend(["", "注意:", *[f"・{warning}" for warning in result.warnings]])
        widget.setPlainText("\n".join(lines))

    def _refresh_compare(self) -> None:
        scenarios = []
        for label, post_income, rate_max, move in [
            ("現在の計画", None, self.rate_max.value(), self.plan.housing.move_offset),
            ("定年後 年220万円", 2_200_000, self.rate_max.value(), self.plan.housing.move_offset),
            ("金利固定", None, self.rate_start.value(), self.plan.housing.move_offset),
            ("住み替えなし", None, self.rate_max.value(), None),
        ]:
            plan = deepcopy(self.plan)
            if post_income is not None:
                period = next(
                    (
                        item
                        for item in plan.income_periods
                        if item.owner == "husband"
                        and item.start_age == plan.husband.retirement_age
                    ),
                    None,
                )
                if period:
                    period.annual_gross_income = post_income
                    period.end_age = plan.husband.pension_start_age
                else:
                    plan.income_periods.append(
                        IncomePeriod(
                            owner="husband",
                            label="定年後の継続雇用",
                            start_age=plan.husband.retirement_age,
                            end_age=plan.husband.pension_start_age,
                            annual_gross_income=post_income,
                        )
                    )
            plan.housing.mortgage.max_rate_percent = rate_max
            plan.housing.move_offset = move
            results = SimulationEngine(plan).run()
            retirement = next(
                (row for row in results if row.husband_age == plan.husband.retirement_age),
                results[-1],
            )
            scenarios.append(
                (
                    label,
                    retirement.net_worth,
                    min(row.cash_end for row in results),
                    sum(row.nisa_sold for row in results),
                    results[-1].net_worth,
                    sum(bool(row.warnings) for row in results),
                )
            )
        self.compare_table.setRowCount(len(scenarios))
        for row, data in enumerate(scenarios):
            for column, value in enumerate(data):
                text = str(value) if column in (0, 5) else man(value)
                self.compare_table.setItem(row, column, QTableWidgetItem(text))


def run_app() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
