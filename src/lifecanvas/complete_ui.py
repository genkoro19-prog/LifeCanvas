from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QTextEdit,
    QWidget,
)

from .compact_timeline import CompactTimelineView
from .engine import SimulationEngine
from .enhanced_ui import LifeCanvasWindow as EnhancedLifeCanvasWindow
from .income_editor import HusbandIncomeEditor
from .models import IncomePeriod, OneTimeIncome
from .persistence import load_plan, save_plan
from .sample import build_genki_family_plan
from .ui import man
from .widgets import NumberEdit


class LifeCanvasWindow(EnhancedLifeCanvasWindow):
    def __init__(self):
        self._complete_ready = False
        self._loading_file = True
        self.current_file: Path | None = None
        super().__init__()

        old_index = self.tabs.indexOf(self.timeline_page)
        if old_index >= 0:
            self.tabs.removeTab(old_index)
        self.timeline_page = self._build_compact_timeline()
        self.tabs.insertTab(2, self.timeline_page, "ライフイベント")

        self._configure_annual_table()
        self._install_file_toolbar()
        self._load_autosave()
        self._sync_inputs_from_plan()
        self._complete_ready = True
        self._loading_file = False
        self.recalculate()

    def _build_setup(self) -> QWidget:
        scroll = super()._build_setup()
        layout = scroll.widget().layout()
        self.h_income.setEnabled(False)
        work_form = self.h_income.parentWidget().layout()
        income_label = (
            work_form.labelForField(self.h_income)
            if hasattr(work_form, "labelForField")
            else None
        )
        if income_label:
            income_label.setText("夫の年収（下の期間表で設定）")
        insertion_index = max(0, layout.count() - 1)

        self.husband_income_editor = HusbandIncomeEditor(self.plan)
        layout.insertWidget(insertion_index, self.husband_income_editor)
        insertion_index += 1

        retirement = QGroupBox("定年・退職金・年金")
        form = QFormLayout(retirement)
        self.h_retirement_lump = NumberEdit(0)
        self.h_pension_age = NumberEdit(
            self.plan.husband.pension_start_age,
            "歳",
            maximum=80,
        )
        self.h_pension = NumberEdit(
            self.plan.husband.annual_pension,
            "円/年",
        )
        self.w_retire = NumberEdit(
            self.plan.wife.retirement_age,
            "歳",
            maximum=80,
        )
        self.w_retirement_lump = NumberEdit(0)
        self.w_pension_age = NumberEdit(
            self.plan.wife.pension_start_age,
            "歳",
            maximum=80,
        )
        self.w_pension = NumberEdit(
            self.plan.wife.annual_pension,
            "円/年",
        )
        form.addRow("夫の退職金", self.h_retirement_lump)
        form.addRow("夫の年金開始", self.h_pension_age)
        form.addRow("夫の年金", self.h_pension)
        form.addRow("妻の退職", self.w_retire)
        form.addRow("妻の退職金", self.w_retirement_lump)
        form.addRow("妻の年金開始", self.w_pension_age)
        form.addRow("妻の年金", self.w_pension)
        layout.insertWidget(insertion_index, retirement)
        return scroll

    def _build_compact_timeline(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        self.compact_timeline = CompactTimelineView()
        self.timeline_detail = QTextEdit()
        self.timeline_detail.setReadOnly(True)
        self.timeline_detail.setMinimumWidth(330)
        self.timeline_detail.setPlainText(
            "イベントの●をクリックすると詳細を表示します。"
        )
        self.compact_timeline.eventSelected.connect(
            self._show_timeline_detail
        )
        layout.addWidget(self.compact_timeline, 3)
        layout.addWidget(self.timeline_detail, 1)
        return page

    def _install_file_toolbar(self) -> None:
        root_layout = self.centralWidget().layout()
        bar = QHBoxLayout()
        self.plan_name_edit = QLineEdit(self.plan.name)
        self.plan_name_edit.setMinimumWidth(260)
        self.file_status = QLabel("自動保存")
        self.file_status.setStyleSheet("color:#666")
        save_button = QPushButton("保存")
        open_button = QPushButton("開く")
        save_button.clicked.connect(self.save_as)
        open_button.clicked.connect(self.open_plan)
        bar.addWidget(QLabel("プラン名"))
        bar.addWidget(self.plan_name_edit)
        bar.addStretch()
        bar.addWidget(self.file_status)
        bar.addWidget(save_button)
        bar.addWidget(open_button)
        root_layout.insertLayout(1, bar)

    def _configure_annual_table(self) -> None:
        headers = [
            "年",
            "夫/妻",
            "夫年収",
            "妻年収",
            "年金",
            "一時収入",
            "収入合計",
            "生活費",
            "住宅",
            "教育",
            "車",
            "生活収支",
            "現預金",
            "投資",
            "純資産",
        ]
        self.year_table.setColumnCount(len(headers))
        self.year_table.setHorizontalHeaderLabels(headers)
        self.year_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

    def _upsert_retirement_income(
        self,
        owner: str,
        label: str,
        age: int,
        amount: float,
    ) -> None:
        self.plan.one_time_incomes = [
            item
            for item in self.plan.one_time_incomes
            if not (item.owner == owner and "退職金" in item.label)
        ]
        self.plan.one_time_incomes.append(
            OneTimeIncome(
                owner=owner,
                label=label,
                age=age,
                amount=amount,
            )
        )

    def _apply_inputs(self) -> None:
        super()._apply_inputs()
        self.plan.income_periods = [
            period
            for period in self.plan.income_periods
            if period.owner != "husband"
        ] + self.husband_income_editor.periods()
        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband"
                and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.plan.husband.annual_gross_income = (
            current_period.annual_gross_income
            if current_period
            else 0
        )

        self.plan.husband.pension_start_age = (
            self.h_pension_age.int_value()
        )
        self.plan.husband.annual_pension = self.h_pension.value()
        self.plan.wife.retirement_age = self.w_retire.int_value()
        self.plan.wife.pension_start_age = self.w_pension_age.int_value()
        self.plan.wife.annual_pension = self.w_pension.value()
        retirement_offset = max(
            0,
            self.plan.wife.retirement_age - self.plan.wife.current_age,
        )
        stages = {
            stage.key: stage
            for stage in self.plan.wife_work_stages
        }
        stages["junior_high"].end_offset = retirement_offset
        stages["retired"].start_offset = retirement_offset
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
            self.plan.name = (
                self.plan_name_edit.text().strip()
                or "LifeCanvas Plan"
            )

    def recalculate(self) -> None:
        try:
            self._apply_inputs()
            self.results = SimulationEngine(self.plan).run()
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(
                self,
                "入力内容を確認してください",
                str(exc),
            )
            return
        self._refresh_dashboard()
        self._refresh_table()
        self._refresh_compare()
        if self._complete_ready:
            self.compact_timeline.set_data(
                self.plan,
                self.results,
            )
            if not self._loading_file:
                self._autosave()

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
                man(result.total_income),
                man(result.core_living_cost),
                man(result.housing_cost),
                man(result.education_cost),
                man(result.car_cost),
                man(result.living_surplus),
                man(result.cash_end),
                man(result.investments_market_value),
                man(result.net_worth),
            ]
            for column, value in enumerate(values):
                self.year_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )
        self.year_table.selectRow(0)

    def _show_selected_year(self) -> None:
        row = self.year_table.currentRow()
        if 0 <= row < len(self.results):
            self._set_year_detail(
                self.year_detail,
                row,
                [],
            )

    def _show_timeline_detail(
        self,
        offset: int,
        events: list,
    ) -> None:
        self._set_year_detail(
            self.timeline_detail,
            offset,
            events,
        )

    def _set_year_detail(
        self,
        widget: QTextEdit,
        offset: int,
        events: list,
    ) -> None:
        result = self.results[offset]
        children = "、".join(
            f"{name}{age}歳"
            for name, age in result.children_ages.items()
        ) or "なし"
        event_lines = [
            f"・{event.title}: {event.detail}"
            for event in events
        ] or [
            f"・{event}"
            for event in result.events
        ] or ["・なし"]
        lines = [
            f"{result.calendar_year}年（夫{result.husband_age}歳・妻{result.wife_age}歳）",
            f"子ども: {children}",
            "",
            "イベント:",
            *event_lines,
            "",
            f"夫年収 {man(result.husband_gross)} / 妻年収 {man(result.wife_gross)}",
            f"給与手取り {man(result.salary_net)} / 年金 {man(result.pension_income)} / 一時収入 {man(result.one_time_income)}",
            f"給付 {man(result.benefits)} / 家賃 {man(result.rental_income)}",
            f"収入合計 {man(result.total_income)}",
            "",
            f"生活費 {man(result.core_living_cost)} / 住宅 {man(result.housing_cost)}",
            f"教育 {man(result.education_cost)} / 車 {man(result.car_cost)}",
            f"生活収支 {man(result.living_surplus)}",
            f"現預金 {man(result.cash_end)} / 純資産 {man(result.net_worth)}",
        ]
        if result.warnings:
            lines.extend(
                [
                    "",
                    "注意:",
                    *[
                        f"・{warning}"
                        for warning in result.warnings
                    ],
                ]
            )
        widget.setPlainText("\n".join(lines))

    def _refresh_compare(self) -> None:
        scenarios = []
        for label, post_income, rate_max, move in [
            (
                "現在の計画",
                None,
                self.rate_max.value(),
                self.plan.housing.move_offset,
            ),
            (
                "定年後 年240万円",
                2_400_000,
                self.rate_max.value(),
                self.plan.housing.move_offset,
            ),
            (
                "金利固定",
                None,
                self.rate_start.value(),
                self.plan.housing.move_offset,
            ),
            (
                "住み替えなし",
                None,
                self.rate_max.value(),
                None,
            ),
        ]:
            plan = deepcopy(self.plan)
            if post_income is not None:
                period = next(
                    (
                        item
                        for item in plan.income_periods
                        if item.owner == "husband"
                        and item.start_age
                        == plan.husband.retirement_age
                    ),
                    None,
                )
                if period:
                    period.annual_gross_income = post_income
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
                (
                    row
                    for row in results
                    if row.husband_age
                    == plan.husband.retirement_age
                ),
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
                text = (
                    str(value)
                    if column in (0, 5)
                    else man(value)
                )
                self.compare_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(text),
                )

    def _autosave_path(self) -> Path:
        return Path(
            QStandardPaths.writableLocation(
                QStandardPaths.AppDataLocation
            )
        ) / "autosave.json"

    def _autosave(self) -> None:
        try:
            save_plan(self.plan, self._autosave_path())
            self.file_status.setText("自動保存済み")
        except Exception:
            self.file_status.setText("自動保存できませんでした")

    def _load_autosave(self) -> None:
        path = self._autosave_path()
        if path.exists():
            try:
                self.plan = load_plan(path)
                self.file_status.setText("前回の内容を復元")
            except Exception:
                self.plan = build_genki_family_plan()

    def _retirement_amount(self, owner: str) -> float:
        return next(
            (
                item.amount
                for item in self.plan.one_time_incomes
                if item.owner == owner
                and "退職金" in item.label
            ),
            0,
        )

    def _sync_inputs_from_plan(self) -> None:
        self.plan_name_edit.setText(self.plan.name)
        self.start_month.set_value(self.plan.start_month)
        self.initial_cash.set_value(self.plan.initial_cash)
        self.living_monthly.set_value(
            self.plan.living_cost.monthly_amount
        )
        self.first_child_offset.set_value(
            self.plan.children[0].birth_offset
        )
        self.second_child_offset.set_value(
            self.plan.children[1].birth_offset
        )
        self.car_purchase_offset.set_value(
            self.plan.car.purchase_offset
        )
        self.car_cycle.set_value(
            self.plan.car.replacement_cycle_years or 0
        )
        self.husband_income_editor.load(self.plan)
        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband"
                and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.h_income.set_value(
            current_period.annual_gross_income
            if current_period
            else self.plan.husband.annual_gross_income
        )
        self.h_retire.set_value(
            self.plan.husband.retirement_age
        )
        self.h_retirement_lump.set_value(
            self._retirement_amount("husband")
        )
        self.h_pension_age.set_value(
            self.plan.husband.pension_start_age
        )
        self.h_pension.set_value(
            self.plan.husband.annual_pension
        )
        self.w_retire.set_value(
            self.plan.wife.retirement_age
        )
        self.w_retirement_lump.set_value(
            self._retirement_amount("wife")
        )
        self.w_pension_age.set_value(
            self.plan.wife.pension_start_age
        )
        self.w_pension.set_value(
            self.plan.wife.annual_pension
        )

        stages = {
            stage.key: stage
            for stage in self.plan.wife_work_stages
        }
        self.w_before.set_value(
            stages["full_time"].annual_gross_income
        )
        self.w_nursery.set_value(
            stages["nursery"].annual_gross_income
        )
        self.w_elementary.set_value(
            stages["elementary"].annual_gross_income
        )
        self.w_junior.set_value(
            stages["junior_high"].annual_gross_income
        )

        mortgage = self.plan.housing.mortgage
        self.loan_amount.set_value(mortgage.principal)
        self.loan_term.set_value(mortgage.term_years)
        self.rate_start.set_value(
            mortgage.initial_rate_percent
        )
        self.rate_step.set_value(
            mortgage.annual_rate_step_percent
        )
        self.rate_max.set_value(
            mortgage.max_rate_percent
        )
        self.move_offset.set_value(
            self.plan.housing.move_offset or 0
        )
        self.new_home.set_value(
            self.plan.housing.new_home_monthly_cost
        )
        self.rental_income.set_value(
            self.plan.housing.old_home_net_rent_annual
        )
        self.h_nisa_before.set_value(
            self.plan.nisa_accounts[0].monthly_contribution
        )
        self.h_nisa_after.set_value(
            self.plan.nisa_accounts[0].contribution_changes.get(
                5,
                0,
            )
        )
        self.w_nisa.set_value(
            self.plan.nisa_accounts[1].monthly_contribution
        )

    def save_as(self) -> None:
        try:
            self._apply_inputs()
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(
                self,
                "入力内容を確認してください",
                str(exc),
            )
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "プランを保存",
            f"{self.plan.name}.json",
            "LifeCanvas Plan (*.json)",
        )
        if filename:
            self.current_file = save_plan(
                self.plan,
                filename,
            )
            self.file_status.setText(
                self.current_file.name
            )

    def open_plan(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "プランを開く",
            "",
            "LifeCanvas Plan (*.json)",
        )
        if not filename:
            return
        try:
            self._loading_file = True
            self.plan = load_plan(filename)
            self.current_file = Path(filename)
            self._sync_inputs_from_plan()
            self._loading_file = False
            self.recalculate()
            self.file_status.setText(
                self.current_file.name
            )
        except Exception as exc:
            self._loading_file = False
            QMessageBox.warning(
                self,
                "ファイルを開けません",
                str(exc),
            )


def run_app() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
