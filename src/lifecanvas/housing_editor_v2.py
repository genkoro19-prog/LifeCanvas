from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .models import ProjectPlan
from .rent_engine import is_rental_move
from .widgets import NumberEdit


class HousingEditor(QGroupBox):
    """Simple housing plan with a clear ownership-to-rent option."""

    changed = Signal()
    MODES = (
        ("現在の家に住み続ける", "none"),
        ("今の家を売って、新しい家を買う", "sell"),
        ("今の家を売って、賃貸へ移る", "rent"),
        ("今の家を残して、別の住まいへ移る", "keep"),
    )

    def __init__(self, plan: ProjectPlan):
        super().__init__("住宅・将来の住まい")
        outer = QVBoxLayout(self)
        note = QLabel(
            "将来の住まい方を選び、大きな金額だけ入力します。空室率や細かな諸経費は扱いません。"
        )
        note.setWordWrap(True)
        note.setObjectName("sectionNote")
        outer.addWidget(note)

        current = QGroupBox("現在の住宅")
        current_form = QFormLayout(current)
        self.loan_amount = NumberEdit(0, "円")
        self.loan_term = NumberEdit(35, "年", maximum=50)
        self.rate_start = NumberEdit(1.0, "%", decimals=2, maximum=20)
        self.rate_max = NumberEdit(3.0, "%", decimals=2, maximum=20)
        current_form.addRow("現在のローン残高", self.loan_amount)
        current_form.addRow("返済期間", self.loan_term)
        current_form.addRow("現在金利", self.rate_start)
        current_form.addRow("想定上限金利", self.rate_max)
        outer.addWidget(current)

        mode_row = QFormLayout()
        self.mode = QComboBox()
        for label, value in self.MODES:
            self.mode.addItem(label, value)
        mode_row.addRow("将来の住まい", self.mode)
        outer.addLayout(mode_row)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._none_page())
        self.pages.addWidget(self._sell_page())
        self.pages.addWidget(self._rent_page())
        self.pages.addWidget(self._keep_page())
        outer.addWidget(self.pages)

        self.mode.currentIndexChanged.connect(self.pages.setCurrentIndex)
        self.mode.currentIndexChanged.connect(self.changed)
        self._connect_changes()
        self.load(plan)

    @staticmethod
    def _none_page() -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        text = QLabel("現在の家に住み続ける前提で計算します。")
        text.setObjectName("sectionNote")
        layout.addWidget(text)
        layout.addStretch()
        return page

    def _sell_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.sell_year = NumberEdit(2045, "年", minimum=1900, maximum=2200)
        self.sale_price = NumberEdit(0, "円")
        self.new_home_price = NumberEdit(0, "円")
        self.new_loan = NumberEdit(0, "円")
        self.new_loan_term = NumberEdit(35, "年", maximum=50)
        self.new_loan_rate = NumberEdit(1.5, "%", decimals=2, maximum=20)
        self.sell_move_cost = NumberEdit(1_000_000, "円")
        form.addRow("住み替える年", self.sell_year)
        form.addRow("今の家の売却額", self.sale_price)
        form.addRow("新居の購入額", self.new_home_price)
        form.addRow("新居の住宅ローン", self.new_loan)
        form.addRow("新居ローンの返済期間", self.new_loan_term)
        form.addRow("新居ローン金利", self.new_loan_rate)
        form.addRow("引っ越し・購入諸費用", self.sell_move_cost)
        return page

    def _rent_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.rent_year = NumberEdit(2045, "年", minimum=1900, maximum=2200)
        self.rent_sale_price = NumberEdit(0, "円")
        self.future_rent = NumberEdit(150_000, "円/月")
        self.rent_move_cost = NumberEdit(700_000, "円")
        form.addRow("賃貸へ移る年", self.rent_year)
        form.addRow("今の家の売却額", self.rent_sale_price)
        form.addRow("将来の家賃", self.future_rent)
        form.addRow("引っ越し諸費用", self.rent_move_cost)
        explanation = QLabel(
            "売却額からその時点の住宅ローン残高を返済し、以後は入力した家賃を毎年の住宅費として計算します。"
        )
        explanation.setWordWrap(True)
        explanation.setObjectName("sectionNote")
        form.addRow(explanation)
        return page

    def _keep_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.keep_year = NumberEdit(2045, "年", minimum=1900, maximum=2200)
        self.new_home_monthly = NumberEdit(150_000, "円/月")
        self.old_home_rent = NumberEdit(750_000, "円/年")
        self.keep_move_cost = NumberEdit(1_000_000, "円")
        form.addRow("住み替える年", self.keep_year)
        form.addRow("新しい住まいの住宅費", self.new_home_monthly)
        form.addRow("旧居の年間手取り家賃", self.old_home_rent)
        form.addRow("引っ越し諸費用", self.keep_move_cost)
        explanation = QLabel("旧居の家賃は、管理費・空室・税金などを差し引いた手取り額だけ入力します。")
        explanation.setWordWrap(True)
        explanation.setObjectName("sectionNote")
        form.addRow(explanation)
        return page

    def _connect_changes(self) -> None:
        for field in self.findChildren(NumberEdit):
            field.edit.editingFinished.connect(self.changed)

    def load(self, plan: ProjectPlan) -> None:
        house = plan.housing
        mortgage = house.mortgage
        self.loan_amount.set_value(mortgage.principal)
        self.loan_term.set_value(mortgage.term_years)
        self.rate_start.set_value(mortgage.initial_rate_percent)
        self.rate_max.set_value(mortgage.max_rate_percent)

        stored_mode = "rent" if is_rental_move(plan) else house.move_mode
        index = self.mode.findData(stored_mode)
        self.mode.setCurrentIndex(max(0, index))
        year = plan.start_year + (house.move_offset or 0)
        self.sell_year.set_value(year)
        self.rent_year.set_value(year)
        self.keep_year.set_value(year)
        self.sale_price.set_value(house.sale_price)
        self.rent_sale_price.set_value(house.sale_price)
        self.new_home_price.set_value(house.new_home_purchase_price)
        self.new_loan.set_value(house.new_mortgage_principal)
        self.new_loan_term.set_value(house.new_mortgage_term_years)
        self.new_loan_rate.set_value(house.new_mortgage_rate_percent)
        self.sell_move_cost.set_value(house.move_cost)
        self.rent_move_cost.set_value(house.move_cost)
        self.keep_move_cost.set_value(house.move_cost)
        self.future_rent.set_value(house.new_home_monthly_cost)
        self.new_home_monthly.set_value(house.new_home_monthly_cost)
        self.old_home_rent.set_value(house.old_home_net_rent_annual)

    def apply_to(self, plan: ProjectPlan) -> None:
        house = plan.housing
        mortgage = house.mortgage
        mortgage.principal = self.loan_amount.value()
        mortgage.term_years = self.loan_term.int_value()
        mortgage.initial_rate_percent = self.rate_start.value()
        mortgage.max_rate_percent = max(self.rate_start.value(), self.rate_max.value())
        house.purchase_price = max(house.purchase_price, mortgage.principal)

        mode = self.mode.currentData()
        if mode == "none":
            house.move_mode = "none"
            house.move_offset = None
            return

        year_field = {
            "sell": self.sell_year,
            "rent": self.rent_year,
            "keep": self.keep_year,
        }[mode]
        year = year_field.int_value()
        last_year = plan.start_year + plan.simulation_years - 1
        if not plan.start_year <= year <= last_year:
            raise ValueError(f"住み替え年は{plan.start_year}〜{last_year}年で入力してください。")
        house.move_offset = year - plan.start_year

        if mode == "sell":
            house.move_mode = "sell"
            house.sale_price = self.sale_price.value()
            house.new_home_purchase_price = self.new_home_price.value()
            house.new_mortgage_principal = self.new_loan.value()
            house.new_mortgage_term_years = self.new_loan_term.int_value()
            house.new_mortgage_rate_percent = self.new_loan_rate.value()
            house.new_home_monthly_cost = 0
            house.move_cost = self.sell_move_cost.value()
            if house.new_mortgage_principal > house.new_home_purchase_price:
                raise ValueError("新居の住宅ローンは新居購入額以下にしてください。")
        elif mode == "rent":
            # Persist with existing fields so old plan files remain readable.
            house.move_mode = "sell"
            house.sale_price = self.rent_sale_price.value()
            house.new_home_purchase_price = 0
            house.new_mortgage_principal = 0
            house.new_home_monthly_cost = self.future_rent.value()
            house.move_cost = self.rent_move_cost.value()
        else:
            house.move_mode = "keep"
            house.new_home_monthly_cost = self.new_home_monthly.value()
            house.old_home_net_rent_annual = self.old_home_rent.value()
            house.move_cost = self.keep_move_cost.value()
