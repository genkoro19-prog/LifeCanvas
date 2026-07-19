from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .models import ProjectPlan, WalletPlan
from .widgets import NumberEdit


class WalletEditor(QGroupBox):
    changed = Signal()
    recommendationRequested = Signal()

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__("家計の分け方・おすすめ投資", parent)
        self._loading = False
        layout = QVBoxLayout(self)

        note = QLabel(
            "夫婦別では、給与は本人の財布へ入り、設定した金額だけ共同家計へ移します。"
            "NISAは本人の財布からだけ積み立てます。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5f6670;")
        layout.addWidget(note)

        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem("すべて共同家計に合算（従来方式）", "combined")
        self.mode.addItem("共同家計・夫・妻を分ける", "separate")
        form.addRow("家計モード", self.mode)

        self.initial_husband_cash = NumberEdit(0)
        self.initial_wife_cash = NumberEdit(0)
        self.husband_household_monthly = NumberEdit(0, "円/月")
        self.wife_household_monthly = NumberEdit(0, "円/月")
        self.husband_personal_spending = NumberEdit(0, "円/月")
        self.wife_personal_spending = NumberEdit(0, "円/月")
        form.addRow("夫の現在の個人預金", self.initial_husband_cash)
        form.addRow("妻の現在の個人預金", self.initial_wife_cash)
        form.addRow("夫から共同家計へ", self.husband_household_monthly)
        form.addRow("妻から共同家計へ", self.wife_household_monthly)
        form.addRow("夫の個人支出（使途不明含む）", self.husband_personal_spending)
        form.addRow("妻の個人支出（使途不明含む）", self.wife_personal_spending)

        self.minimum_household_cash = NumberEdit(1_200_000)
        self.target_household_cash = NumberEdit(10_000_000)
        self.minimum_personal_cash = NumberEdit(300_000)
        self.target_personal_cash = NumberEdit(1_000_000)
        form.addRow("共同現預金の最低額", self.minimum_household_cash)
        form.addRow("共同現預金の目標額", self.target_household_cash)
        form.addRow("個人現預金の最低額", self.minimum_personal_cash)
        form.addRow("個人現預金の目標額", self.target_personal_cash)

        self.auto_invest = QCheckBox("現預金に応じて積立を自動停止・増額する")
        form.addRow(self.auto_invest)
        layout.addLayout(form)

        action_row = QHBoxLayout()
        self.recommend_button = QPushButton("おすすめ投資額を試算")
        self.recommend_button.clicked.connect(
            lambda _checked=False: self.recommendationRequested.emit()
        )
        action_row.addWidget(self.recommend_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.recommendation = QLabel("夫婦別モードにすると、本人資金だけで安全な月額を試算できます。")
        self.recommendation.setWordWrap(True)
        self.recommendation.setStyleSheet(
            "background:#eef6ff; color:#174a7c; padding:10px; border-radius:7px;"
        )
        layout.addWidget(self.recommendation)

        self._connect_changes()
        self.load(plan)

    def _connect_changes(self) -> None:
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.auto_invest.toggled.connect(lambda _checked: self._emit_changed())
        for editor in (
            self.initial_husband_cash,
            self.initial_wife_cash,
            self.husband_household_monthly,
            self.wife_household_monthly,
            self.husband_personal_spending,
            self.wife_personal_spending,
            self.minimum_household_cash,
            self.target_household_cash,
            self.minimum_personal_cash,
            self.target_personal_cash,
        ):
            editor.edit.editingFinished.connect(self._emit_changed)

    def _emit_changed(self) -> None:
        if not self._loading:
            self.changed.emit()

    def _mode_changed(self, *_args) -> None:
        separate = self.mode.currentData() == "separate"
        for widget in (
            self.initial_husband_cash,
            self.initial_wife_cash,
            self.husband_household_monthly,
            self.wife_household_monthly,
            self.husband_personal_spending,
            self.wife_personal_spending,
            self.minimum_household_cash,
            self.target_household_cash,
            self.minimum_personal_cash,
            self.target_personal_cash,
            self.auto_invest,
            self.recommend_button,
        ):
            widget.setEnabled(separate)
        self._emit_changed()

    def load(self, plan: ProjectPlan) -> None:
        self._loading = True
        try:
            wallet = plan.wallets
            index = self.mode.findData(wallet.mode)
            self.mode.setCurrentIndex(max(0, index))
            self.initial_husband_cash.set_value(wallet.initial_husband_cash)
            self.initial_wife_cash.set_value(wallet.initial_wife_cash)
            self.husband_household_monthly.set_value(wallet.husband_household_monthly)
            self.wife_household_monthly.set_value(wallet.wife_household_monthly)
            self.husband_personal_spending.set_value(wallet.husband_personal_spending_monthly)
            self.wife_personal_spending.set_value(wallet.wife_personal_spending_monthly)
            self.minimum_household_cash.set_value(wallet.minimum_household_cash)
            self.target_household_cash.set_value(wallet.target_household_cash)
            self.minimum_personal_cash.set_value(wallet.minimum_personal_cash)
            self.target_personal_cash.set_value(wallet.target_personal_cash)
            self.auto_invest.setChecked(wallet.auto_invest_enabled)
            self._mode_changed()
        finally:
            self._loading = False

    def value(self) -> WalletPlan:
        return WalletPlan(
            mode=self.mode.currentData(),
            initial_husband_cash=self.initial_husband_cash.value(),
            initial_wife_cash=self.initial_wife_cash.value(),
            husband_household_monthly=self.husband_household_monthly.value(),
            wife_household_monthly=self.wife_household_monthly.value(),
            husband_personal_spending_monthly=self.husband_personal_spending.value(),
            wife_personal_spending_monthly=self.wife_personal_spending.value(),
            minimum_household_cash=self.minimum_household_cash.value(),
            target_household_cash=self.target_household_cash.value(),
            minimum_personal_cash=self.minimum_personal_cash.value(),
            target_personal_cash=self.target_personal_cash.value(),
            auto_invest_enabled=self.auto_invest.isChecked(),
        )

    def show_recommendation(self, husband_monthly: float, wife_monthly: float, note: str) -> None:
        self.recommendation.setText(
            f"おすすめ投資枠　夫：月{husband_monthly/10_000:,.1f}万円　"
            f"妻：月{wife_monthly/10_000:,.1f}万円\n{note}"
        )
