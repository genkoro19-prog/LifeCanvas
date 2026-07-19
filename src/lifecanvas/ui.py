from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .engine import SimulationEngine
from .sample import build_genki_family_plan


def man(value: float) -> str:
    return f"{value / 10_000:,.0f}万円"


class MetricCard(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: #666;")
        layout.addWidget(self.value)
        layout.addWidget(self.note)


class LifeCanvasWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.plan = build_genki_family_plan()
        self.results = []
        self.setWindowTitle("LifeCanvas")
        self.resize(1400, 900)
        self.setStyleSheet("""
            QMainWindow { background: #f5f6f8; }
            QGroupBox { background: white; border: 1px solid #dfe3e8; border-radius: 10px; margin-top: 14px; padding: 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            QPushButton { padding: 9px 16px; border-radius: 7px; background: #1769e0; color: white; font-weight: 600; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab { padding: 10px 18px; }
            QTableWidget { background: white; gridline-color: #e8eaed; }
        """)

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        header = QHBoxLayout()
        title = QLabel("LifeCanvas")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        subtitle = QLabel("家計簿ではなく、将来の選択を比較するライフプラン")
        subtitle.setStyleSheet("color: #666;")
        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()
        recalc = QPushButton("再計算")
        recalc.clicked.connect(self.recalculate)
        header.addWidget(recalc)
        main.addLayout(header)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs)
        self.tabs.addTab(self._build_dashboard(), "結果")
        self.tabs.addTab(self._build_setup(), "かんたん設定")
        self.tabs.addTab(self._build_annual(), "年表・内訳")
        self.tabs.addTab(self._build_compare(), "比較")
        self.recalculate()

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        cards = QGridLayout()
        self.card_retirement = MetricCard("夫60歳時点の純資産")
        self.card_cash = MetricCard("最低現預金")
        self.card_shortage = MetricCard("資金ショート")
        self.card_move = MetricCard("住み替え時のローン残高")
        for index, card in enumerate([self.card_retirement, self.card_cash, self.card_shortage, self.card_move]):
            cards.addWidget(card, 0, index)
        layout.addLayout(cards)

        self.figure = Figure(figsize=(9, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)
        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMaximumHeight(150)
        layout.addWidget(self.dashboard_warnings)
        return page

    @staticmethod
    def _money_spin(value: float, maximum: float = 100_000_000) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, maximum)
        spin.setDecimals(0)
        spin.setSingleStep(10_000)
        spin.setSuffix(" 円")
        spin.setValue(value)
        return spin

    def _build_setup(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        basic = QGroupBox("まず見る項目")
        form = QFormLayout(basic)
        self.start_month = QSpinBox(); self.start_month.setRange(1, 12); self.start_month.setValue(self.plan.start_month)
        self.initial_cash = self._money_spin(self.plan.initial_cash)
        self.living_monthly = self._money_spin(self.plan.living_cost.monthly_amount, 2_000_000)
        form.addRow("開始月", self.start_month)
        form.addRow("現在の現預金", self.initial_cash)
        form.addRow("現在の生活費合計（月・住宅費込み）", self.living_monthly)
        note = QLabel("住宅費込みの金額から初年度のローン・固定資産税等を一度だけ差し引き、基本生活費を作ります。二重計上しません。")
        note.setWordWrap(True); note.setStyleSheet("color:#666")
        form.addRow(note)
        layout.addWidget(basic)

        work = QGroupBox("夫婦の働き方")
        form = QFormLayout(work)
        self.h_income = self._money_spin(self.plan.husband.annual_gross_income)
        self.h_retire = QSpinBox(); self.h_retire.setRange(40, 80); self.h_retire.setValue(self.plan.husband.retirement_age)
        self.w_before = self._money_spin(self.plan.wife_work_stages[0].annual_gross_income)
        self.w_nursery = self._money_spin(next(s for s in self.plan.wife_work_stages if s.key == "nursery").annual_gross_income)
        self.w_elementary = self._money_spin(next(s for s in self.plan.wife_work_stages if s.key == "elementary").annual_gross_income)
        self.w_junior = self._money_spin(next(s for s in self.plan.wife_work_stages if s.key == "junior_high").annual_gross_income)
        form.addRow("夫の年収", self.h_income)
        form.addRow("夫の定年", self.h_retire)
        form.addRow("妻・出産前", self.w_before)
        form.addRow("妻・第二子保育園", self.w_nursery)
        form.addRow("妻・第二子小学生", self.w_elementary)
        form.addRow("妻・第二子中学生以降（パート）", self.w_junior)
        layout.addWidget(work)

        house = QGroupBox("住宅と住み替え")
        form = QFormLayout(house)
        self.loan_amount = self._money_spin(self.plan.housing.mortgage.principal)
        self.rate_start = QDoubleSpinBox(); self.rate_start.setRange(0, 10); self.rate_start.setDecimals(2); self.rate_start.setSuffix(" %"); self.rate_start.setValue(self.plan.housing.mortgage.initial_rate_percent)
        self.rate_max = QDoubleSpinBox(); self.rate_max.setRange(0, 10); self.rate_max.setDecimals(2); self.rate_max.setSuffix(" %"); self.rate_max.setValue(self.plan.housing.mortgage.max_rate_percent)
        self.move_offset = QSpinBox(); self.move_offset.setRange(0, 60); self.move_offset.setValue(self.plan.housing.move_offset or 26)
        self.new_home = self._money_spin(self.plan.housing.new_home_monthly_cost, 1_000_000)
        self.rental_income = self._money_spin(self.plan.housing.old_home_net_rent_annual)
        form.addRow("住宅ローン", self.loan_amount)
        form.addRow("開始金利", self.rate_start)
        form.addRow("上限金利", self.rate_max)
        form.addRow("住み替え（開始から何年後）", self.move_offset)
        form.addRow("新居費（月）", self.new_home)
        form.addRow("旧居の手取り家賃（年）", self.rental_income)
        layout.addWidget(house)

        invest = QGroupBox("NISA")
        form = QFormLayout(invest)
        self.h_nisa_before = self._money_spin(self.plan.nisa_accounts[0].monthly_contribution, 1_000_000)
        self.h_nisa_after = self._money_spin(self.plan.nisa_accounts[0].contribution_changes[5], 1_000_000)
        self.w_nisa = self._money_spin(self.plan.nisa_accounts[1].monthly_contribution, 1_000_000)
        form.addRow("夫・現在（月）", self.h_nisa_before)
        form.addRow("夫・5年後（月）", self.h_nisa_after)
        form.addRow("妻（月）", self.w_nisa)
        layout.addWidget(invest)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_annual(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.year_table = QTableWidget(0, 10)
        self.year_table.setHorizontalHeaderLabels(["年", "夫/妻", "妻年収", "収入", "消費支出", "生活収支", "NISA積立", "現預金", "投資", "純資産"])
        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.year_table.horizontalHeader().setStretchLastSection(True)
        self.year_table.itemSelectionChanged.connect(self._show_selected_year)
        layout.addWidget(self.year_table, 3)
        self.year_detail = QTextEdit(); self.year_detail.setReadOnly(True)
        layout.addWidget(self.year_detail, 1)
        return page

    def _build_compare(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("妻の中学生以降の年収や、金利・住み替え条件を変えた結果を並べます。"))
        self.compare_table = QTableWidget(0, 6)
        self.compare_table.setHorizontalHeaderLabels(["シナリオ", "60歳純資産", "最低現金", "NISA売却", "最終純資産", "警告年数"])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.compare_table)
        return page

    def _apply_inputs(self):
        self.plan.start_month = self.start_month.value()
        self.plan.initial_cash = self.initial_cash.value()
        self.plan.living_cost.monthly_amount = self.living_monthly.value()
        self.plan.husband.annual_gross_income = self.h_income.value()
        self.plan.husband.retirement_age = self.h_retire.value()
        mapping = {s.key: s for s in self.plan.wife_work_stages}
        mapping["full_time"].annual_gross_income = self.w_before.value()
        mapping["nursery"].annual_gross_income = self.w_nursery.value()
        mapping["elementary"].annual_gross_income = self.w_elementary.value()
        mapping["junior_high"].annual_gross_income = self.w_junior.value()
        self.plan.housing.mortgage.principal = self.loan_amount.value()
        self.plan.housing.purchase_price = self.loan_amount.value()
        self.plan.housing.mortgage.initial_rate_percent = self.rate_start.value()
        self.plan.housing.mortgage.max_rate_percent = self.rate_max.value()
        self.plan.housing.move_offset = self.move_offset.value()
        self.plan.housing.new_home_monthly_cost = self.new_home.value()
        self.plan.housing.old_home_net_rent_annual = self.rental_income.value()
        self.plan.nisa_accounts[0].monthly_contribution = self.h_nisa_before.value()
        self.plan.nisa_accounts[0].contribution_changes[5] = self.h_nisa_after.value()
        self.plan.nisa_accounts[1].monthly_contribution = self.w_nisa.value()

    def recalculate(self):
        self._apply_inputs()
        self.results = SimulationEngine(self.plan).run()
        self._refresh_dashboard()
        self._refresh_table()
        self._refresh_compare()

    def _refresh_dashboard(self):
        retirement = next((r for r in self.results if r.husband_age == self.plan.husband.retirement_age), self.results[-1])
        minimum_cash = min(self.results, key=lambda r: r.cash_end)
        shortage = [r for r in self.results if any("資金ショート" in w for w in r.warnings)]
        move = self.results[min(self.plan.housing.move_offset or 0, len(self.results)-1)]
        self.card_retirement.value.setText(man(retirement.net_worth)); self.card_retirement.note.setText(f"{retirement.calendar_year}年")
        self.card_cash.value.setText(man(minimum_cash.cash_end)); self.card_cash.note.setText(f"最低年: {minimum_cash.calendar_year}年")
        self.card_shortage.value.setText("あり" if shortage else "なし"); self.card_shortage.note.setText(f"{shortage[0].calendar_year}年から" if shortage else "現在の前提では発生しません")
        self.card_move.value.setText(man(move.mortgage_balance)); self.card_move.note.setText(f"住み替え年: {move.calendar_year}年")

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        years = [r.calendar_year for r in self.results]
        ax.plot(years, [r.net_worth / 10_000 for r in self.results], label="純資産")
        ax.plot(years, [r.cash_end / 10_000 for r in self.results], label="現預金")
        ax.plot(years, [r.investments_market_value / 10_000 for r in self.results], label="投資")
        ax.set_ylabel("万円"); ax.grid(True, alpha=.25); ax.legend(); self.figure.tight_layout(); self.canvas.draw()
        self.dashboard_warnings.clear()
        for result in self.results:
            for warning in result.warnings:
                self.dashboard_warnings.addItem(f"{result.calendar_year}年: {warning}")
        if self.dashboard_warnings.count() == 0:
            self.dashboard_warnings.addItem("重大な資金ショートはありません。")

    def _refresh_table(self):
        self.year_table.setRowCount(len(self.results))
        for row, r in enumerate(self.results):
            values = [
                str(r.calendar_year), f"{r.husband_age}/{r.wife_age}", man(r.wife_gross), man(r.total_income),
                man(r.consumption_total), man(r.living_surplus), man(r.nisa_contributed), man(r.cash_end),
                man(r.investments_market_value), man(r.net_worth),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2: item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.year_table.setItem(row, col, item)
        self.year_table.selectRow(0)

    def _show_selected_year(self):
        row = self.year_table.currentRow()
        if row < 0 or row >= len(self.results): return
        r = self.results[row]
        children = "、".join(f"{k} {v}歳" for k, v in r.children_ages.items()) or "なし"
        lines = [
            f"{r.calendar_year}年（夫{r.husband_age}歳・妻{r.wife_age}歳 / 子: {children}）",
            "",
            f"収入合計: {man(r.total_income)}（給与等手取り {man(r.salary_net)} / 給付 {man(r.benefits)} / 家賃 {man(r.rental_income)}）",
            f"消費支出: {man(r.consumption_total)}（基本生活 {man(r.core_living_cost)} / 住宅 {man(r.housing_cost)} / 教育 {man(r.education_cost)} / 車 {man(r.car_cost)}）",
            f"生活収支: {man(r.living_surplus)}",
            f"NISA: 予定 {man(r.nisa_planned)} / 実行 {man(r.nisa_contributed)} / 売却 {man(r.nisa_sold)}",
            f"現預金: {man(r.cash_end)} / 投資: {man(r.investments_market_value)} / 純資産: {man(r.net_worth)}",
            "",
            "イベント:", *[f"・{e}" for e in r.events],
            "警告:", *([f"・{w}" for w in r.warnings] or ["・なし"]),
        ]
        self.year_detail.setPlainText("\n".join(lines))

    def _refresh_compare(self):
        scenarios = []
        for label, wife_income, rate_max, move in [
            ("現在の計画", self.w_junior.value(), self.rate_max.value(), self.move_offset.value()),
            ("妻 年180万円", 1_800_000, self.rate_max.value(), self.move_offset.value()),
            ("金利1.68%固定", self.w_junior.value(), 1.68, self.move_offset.value()),
            ("住み替えなし", self.w_junior.value(), self.rate_max.value(), None),
        ]:
            p = deepcopy(self.plan)
            next(s for s in p.wife_work_stages if s.key == "junior_high").annual_gross_income = wife_income
            p.housing.mortgage.max_rate_percent = rate_max
            p.housing.move_offset = move
            res = SimulationEngine(p).run()
            retirement = next((r for r in res if r.husband_age == p.husband.retirement_age), res[-1])
            scenarios.append((label, retirement.net_worth, min(r.cash_end for r in res), sum(r.nisa_sold for r in res), res[-1].net_worth, sum(bool(r.warnings) for r in res)))
        self.compare_table.setRowCount(len(scenarios))
        for row, data in enumerate(scenarios):
            for col, value in enumerate(data):
                text = str(value) if col in (0, 5) else man(value)
                self.compare_table.setItem(row, col, QTableWidgetItem(text))


def run_app():
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
