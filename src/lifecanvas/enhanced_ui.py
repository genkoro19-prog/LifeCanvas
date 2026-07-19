from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .engine import SimulationEngine
from .ui import LifeCanvasWindow as BaseLifeCanvasWindow, man
from .widgets import LifeTimelineView, NumberEdit


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """LifeCanvas UI with direct numeric entry and a visual event timeline."""

    def __init__(self):
        self._timeline_ready = False
        super().__init__()
        self.timeline_page = self._build_timeline()
        self.tabs.insertTab(2, self.timeline_page, "ライフイベント")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._timeline_ready = True
        self._refresh_timeline()

    @staticmethod
    def _number(
        value: float,
        unit: str = "円",
        decimals: int = 0,
        maximum: float = 100_000_000,
    ) -> NumberEdit:
        return NumberEdit(value=value, unit=unit, decimals=decimals, maximum=maximum)

    def _build_setup(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        guide = QLabel("数字は矢印ではなく、欄をクリックして直接入力してください。カンマなしでも入力できます。")
        guide.setWordWrap(True)
        guide.setStyleSheet("background:#e8f1ff; color:#174ea6; padding:10px; border-radius:7px;")
        layout.addWidget(guide)

        basic = QGroupBox("まず見る項目")
        form = QFormLayout(basic)
        self.start_month = self._number(self.plan.start_month, "月", maximum=12)
        self.initial_cash = self._number(self.plan.initial_cash)
        self.living_monthly = self._number(self.plan.living_cost.monthly_amount, maximum=2_000_000)
        form.addRow("開始月", self.start_month)
        form.addRow("現在の現預金", self.initial_cash)
        form.addRow("現在の生活費合計（月・住宅費込み）", self.living_monthly)
        note = QLabel("住宅費込みの金額から初年度のローン・固定資産税等を一度だけ差し引き、基本生活費を作ります。二重計上しません。")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666")
        form.addRow(note)
        layout.addWidget(basic)

        family = QGroupBox("家族とライフイベント")
        form = QFormLayout(family)
        self.first_child_offset = self._number(self.plan.children[0].birth_offset, "年後", maximum=50)
        self.second_child_offset = self._number(self.plan.children[1].birth_offset, "年後", maximum=50)
        self.car_purchase_offset = self._number(self.plan.car.purchase_offset, "年後", maximum=50)
        self.car_cycle = self._number(self.plan.car.replacement_cycle_years or 0, "年ごと", maximum=30)
        form.addRow("第一子の誕生", self.first_child_offset)
        form.addRow("第二子の誕生", self.second_child_offset)
        form.addRow("車の購入", self.car_purchase_offset)
        form.addRow("車の買い替え周期", self.car_cycle)
        layout.addWidget(family)

        work = QGroupBox("夫婦の働き方")
        form = QFormLayout(work)
        self.h_income = self._number(self.plan.husband.annual_gross_income)
        self.h_retire = self._number(self.plan.husband.retirement_age, "歳", maximum=80)
        self.w_before = self._number(self.plan.wife_work_stages[0].annual_gross_income)
        self.w_nursery = self._number(next(s for s in self.plan.wife_work_stages if s.key == "nursery").annual_gross_income)
        self.w_elementary = self._number(next(s for s in self.plan.wife_work_stages if s.key == "elementary").annual_gross_income)
        self.w_junior = self._number(next(s for s in self.plan.wife_work_stages if s.key == "junior_high").annual_gross_income)
        form.addRow("夫の年収", self.h_income)
        form.addRow("夫の定年", self.h_retire)
        form.addRow("妻・出産前", self.w_before)
        form.addRow("妻・第二子保育園", self.w_nursery)
        form.addRow("妻・第二子小学生", self.w_elementary)
        form.addRow("妻・第二子中学生以降（パート）", self.w_junior)
        layout.addWidget(work)

        house = QGroupBox("住宅と住み替え")
        form = QFormLayout(house)
        self.loan_amount = self._number(self.plan.housing.mortgage.principal)
        self.loan_term = self._number(self.plan.housing.mortgage.term_years, "年", maximum=50)
        self.rate_start = self._number(self.plan.housing.mortgage.initial_rate_percent, "%", decimals=2, maximum=10)
        self.rate_step = self._number(self.plan.housing.mortgage.annual_rate_step_percent, "%/年", decimals=2, maximum=5)
        self.rate_max = self._number(self.plan.housing.mortgage.max_rate_percent, "%", decimals=2, maximum=10)
        self.move_offset = self._number(self.plan.housing.move_offset or 26, "年後", maximum=60)
        self.new_home = self._number(self.plan.housing.new_home_monthly_cost, maximum=1_000_000)
        self.rental_income = self._number(self.plan.housing.old_home_net_rent_annual)
        form.addRow("住宅ローン", self.loan_amount)
        form.addRow("返済期間", self.loan_term)
        form.addRow("開始金利", self.rate_start)
        form.addRow("金利上昇幅", self.rate_step)
        form.addRow("上限金利", self.rate_max)
        form.addRow("住み替え", self.move_offset)
        form.addRow("新居費（月）", self.new_home)
        form.addRow("旧居の手取り家賃（年）", self.rental_income)
        layout.addWidget(house)

        invest = QGroupBox("NISA")
        form = QFormLayout(invest)
        self.h_nisa_before = self._number(self.plan.nisa_accounts[0].monthly_contribution, maximum=1_000_000)
        self.h_nisa_after = self._number(self.plan.nisa_accounts[0].contribution_changes[5], maximum=1_000_000)
        self.w_nisa = self._number(self.plan.nisa_accounts[1].monthly_contribution, maximum=1_000_000)
        form.addRow("夫・現在（月）", self.h_nisa_before)
        form.addRow("夫・5年後（月）", self.h_nisa_after)
        form.addRow("妻（月）", self.w_nisa)
        layout.addWidget(invest)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_timeline(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel("子どもの成長、働き方、車、住宅ローン、住み替え、NISAの変更を同じ時間軸で確認できます。")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#555; padding:4px 2px;")
        layout.addWidget(intro)
        self.timeline_view = LifeTimelineView()
        layout.addWidget(self.timeline_view, 1)
        return page

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.timeline_page:
            QTimer.singleShot(0, self.timeline_view.scroll_to_start)

    def _apply_inputs(self) -> None:
        start_month = self.start_month.int_value()
        if not 1 <= start_month <= 12:
            raise ValueError("開始月は1〜12で入力してください。")
        first_child = self.first_child_offset.int_value()
        second_child = self.second_child_offset.int_value()
        if second_child < first_child:
            raise ValueError("第二子の誕生時期は第一子以降にしてください。")

        self.plan.start_month = start_month
        self.plan.initial_cash = self.initial_cash.value()
        self.plan.living_cost.monthly_amount = self.living_monthly.value()
        self.plan.children[0].birth_offset = first_child
        self.plan.children[1].birth_offset = second_child

        wife_retirement_offset = max(0, self.plan.wife.retirement_age - self.plan.wife.current_age)
        stage_map = {stage.key: stage for stage in self.plan.wife_work_stages}
        stage_map["full_time"].end_offset = first_child
        stage_map["childcare_leave"].start_offset = first_child
        stage_map["childcare_leave"].end_offset = second_child + 4
        stage_map["nursery"].start_offset = second_child + 4
        stage_map["nursery"].end_offset = second_child + 6
        stage_map["elementary"].start_offset = second_child + 6
        stage_map["elementary"].end_offset = second_child + 12
        stage_map["junior_high"].start_offset = second_child + 12
        stage_map["junior_high"].end_offset = wife_retirement_offset
        stage_map["retired"].start_offset = wife_retirement_offset

        self.plan.car.purchase_offset = self.car_purchase_offset.int_value()
        cycle = self.car_cycle.int_value()
        self.plan.car.replacement_cycle_years = cycle if cycle > 0 else None
        self.plan.husband.annual_gross_income = self.h_income.value()
        self.plan.husband.retirement_age = self.h_retire.int_value()
        stage_map["full_time"].annual_gross_income = self.w_before.value()
        stage_map["nursery"].annual_gross_income = self.w_nursery.value()
        stage_map["elementary"].annual_gross_income = self.w_elementary.value()
        stage_map["junior_high"].annual_gross_income = self.w_junior.value()
        self.plan.housing.mortgage.principal = self.loan_amount.value()
        self.plan.housing.purchase_price = self.loan_amount.value()
        self.plan.housing.mortgage.term_years = self.loan_term.int_value()
        self.plan.housing.mortgage.initial_rate_percent = self.rate_start.value()
        self.plan.housing.mortgage.annual_rate_step_percent = self.rate_step.value()
        self.plan.housing.mortgage.max_rate_percent = self.rate_max.value()
        self.plan.housing.move_offset = self.move_offset.int_value()
        self.plan.housing.new_home_monthly_cost = self.new_home.value()
        self.plan.housing.old_home_net_rent_annual = self.rental_income.value()
        self.plan.nisa_accounts[0].monthly_contribution = self.h_nisa_before.value()
        self.plan.nisa_accounts[0].contribution_changes[5] = self.h_nisa_after.value()
        self.plan.nisa_accounts[1].monthly_contribution = self.w_nisa.value()

    def recalculate(self) -> None:
        try:
            self._apply_inputs()
            self.results = SimulationEngine(self.plan).run()
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "入力内容を確認してください", str(exc))
            return
        self._refresh_dashboard()
        self._refresh_table()
        self._refresh_compare()
        if self._timeline_ready:
            self._refresh_timeline()

    def _refresh_timeline(self) -> None:
        self.timeline_view.set_plan(self.plan)

    def _refresh_compare(self) -> None:
        scenarios = []
        for label, wife_income, rate_max, move in [
            ("現在の計画", self.w_junior.value(), self.rate_max.value(), self.move_offset.int_value()),
            ("妻 年180万円", 1_800_000, self.rate_max.value(), self.move_offset.int_value()),
            ("金利1.68%固定", self.w_junior.value(), 1.68, self.move_offset.int_value()),
            ("住み替えなし", self.w_junior.value(), self.rate_max.value(), None),
        ]:
            plan = deepcopy(self.plan)
            next(stage for stage in plan.wife_work_stages if stage.key == "junior_high").annual_gross_income = wife_income
            plan.housing.mortgage.max_rate_percent = rate_max
            plan.housing.move_offset = move
            results = SimulationEngine(plan).run()
            retirement = next((r for r in results if r.husband_age == plan.husband.retirement_age), results[-1])
            scenarios.append(
                (
                    label,
                    retirement.net_worth,
                    min(r.cash_end for r in results),
                    sum(r.nisa_sold for r in results),
                    results[-1].net_worth,
                    sum(bool(r.warnings) for r in results),
                )
            )
        self.compare_table.setRowCount(len(scenarios))
        for row, data in enumerate(scenarios):
            for col, value in enumerate(data):
                text = str(value) if col in (0, 5) else man(value)
                self.compare_table.setItem(row, col, QTableWidgetItem(text))


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
