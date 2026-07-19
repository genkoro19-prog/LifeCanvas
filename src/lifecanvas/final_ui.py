from __future__ import annotations

from copy import deepcopy

from PySide6.QtWidgets import QTableWidgetItem, QWidget

from .child_editor import ChildEditor
from .complete_ui import LifeCanvasWindow as CompleteLifeCanvasWindow
from .engine import SimulationEngine
from .family import apply_work_stages_for_child, infer_work_reference_child
from .models import IncomePeriod
from .ui import man


class LifeCanvasWindow(CompleteLifeCanvasWindow):
    """Desktop UI with flexible family settings and opinionated default retirement plan."""

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
        self._update_work_labels()
        return scroll

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
