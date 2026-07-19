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
        super().__init__("夫婦別の預金・家計負担・おすすめ投資", parent)
        self._loading = False
        self._syncing_ratio = False
        layout = QVBoxLayout(self)

        note = QLabel(
            "夫婦別モードでは共同預金を作りません。夫と妻の収入から、"
            "家計負担・個人支出・本人NISAを引いた残りが各自の預金へ貯まります。"
            "家計の不足分は設定割合で双方の預金から補填し、給付金は妻口座へ入ります。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5f6670;")
        layout.addWidget(note)

        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem("すべて共同家計に合算（従来方式）", "combined")
        self.mode.addItem("夫婦の預金を分ける", "separate")
        form.addRow("家計モード", self.mode)

        self.initial_husband_cash = NumberEdit(0)
        self.initial_wife_cash = NumberEdit(0)
        form.addRow("夫の現在の預金", self.initial_husband_cash)
        form.addRow("妻の現在の預金", self.initial_wife_cash)

        self.husband_household_monthly = NumberEdit(0, "円/月")
        self.wife_household_monthly = NumberEdit(0, "円/月")
        self.husband_child_increment = NumberEdit(0, "円/月・1人")
        self.wife_child_increment = NumberEdit(0, "円/月・1人")
        form.addRow("夫の通常の家計負担上限", self.husband_household_monthly)
        form.addRow("妻の通常の家計負担上限", self.wife_household_monthly)
        form.addRow("子ども誕生後の夫の追加負担", self.husband_child_increment)
        form.addRow("子ども誕生後の妻の追加負担", self.wife_child_increment)

        self.husband_personal_spending = NumberEdit(0, "円/月")
        self.wife_personal_spending = NumberEdit(0, "円/月")
        form.addRow("夫の個人支出", self.husband_personal_spending)
        form.addRow("妻の個人支出（使途不明含む）", self.wife_personal_spending)

        self.shortfall_husband_percent = NumberEdit(
            50, "%", decimals=0, minimum=0, maximum=100
        )
        self.shortfall_wife_percent = NumberEdit(
            50, "%", decimals=0, minimum=0, maximum=100
        )
        form.addRow("家計不足を夫が出す割合", self.shortfall_husband_percent)
        form.addRow("家計不足を妻が出す割合", self.shortfall_wife_percent)

        self.minimum_personal_cash = NumberEdit(1_000_000)
        self.target_personal_cash = NumberEdit(1_000_000)
        form.addRow("各自に必ず残す最低手元現金", self.minimum_personal_cash)
        form.addRow("自動増額後も残す目標現金", self.target_personal_cash)

        self.auto_invest = QCheckBox("現金が目標額を超えたらNISAを自動増額する")
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

        self.recommendation = QLabel(
            "夫婦別モードにすると、家計不足と各自100万円の手元現金を考慮して試算できます。"
        )
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
        self.shortfall_husband_percent.edit.editingFinished.connect(
            self._sync_wife_ratio
        )
        self.shortfall_wife_percent.edit.editingFinished.connect(
            self._sync_husband_ratio
        )
        for editor in (
            self.initial_husband_cash,
            self.initial_wife_cash,
            self.husband_household_monthly,
            self.wife_household_monthly,
            self.husband_child_increment,
            self.wife_child_increment,
            self.husband_personal_spending,
            self.wife_personal_spending,
            self.minimum_personal_cash,
            self.target_personal_cash,
        ):
            editor.edit.editingFinished.connect(self._emit_changed)

    def _sync_wife_ratio(self) -> None:
        if self._syncing_ratio:
            return
        self._syncing_ratio = True
        try:
            self.shortfall_wife_percent.set_value(
                100 - self.shortfall_husband_percent.value()
            )
        finally:
            self._syncing_ratio = False
        self._emit_changed()

    def _sync_husband_ratio(self) -> None:
        if self._syncing_ratio:
            return
        self._syncing_ratio = True
        try:
            self.shortfall_husband_percent.set_value(
                100 - self.shortfall_wife_percent.value()
            )
        finally:
            self._syncing_ratio = False
        self._emit_changed()

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
            self.husband_child_increment,
            self.wife_child_increment,
            self.husband_personal_spending,
            self.wife_personal_spending,
            self.shortfall_husband_percent,
            self.shortfall_wife_percent,
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
            self.husband_child_increment.set_value(
                wallet.husband_child_household_increment_monthly
            )
            self.wife_child_increment.set_value(
                wallet.wife_child_household_increment_monthly
            )
            self.husband_personal_spending.set_value(
                wallet.husband_personal_spending_monthly
            )
            self.wife_personal_spending.set_value(
                wallet.wife_personal_spending_monthly
            )
            self.shortfall_husband_percent.set_value(
                wallet.household_shortfall_husband_percent
            )
            self.shortfall_wife_percent.set_value(
                wallet.household_shortfall_wife_percent
            )
            self.minimum_personal_cash.set_value(wallet.minimum_personal_cash)
            self.target_personal_cash.set_value(wallet.target_personal_cash)
            self.auto_invest.setChecked(wallet.auto_invest_enabled)
            self._mode_changed()
        finally:
            self._loading = False

    def value(self) -> WalletPlan:
        husband_ratio = self.shortfall_husband_percent.value()
        wife_ratio = 100 - husband_ratio
        if abs(self.shortfall_wife_percent.value() - wife_ratio) > 0.01:
            self.shortfall_wife_percent.set_value(wife_ratio)
        return WalletPlan(
            mode=self.mode.currentData(),
            initial_husband_cash=self.initial_husband_cash.value(),
            initial_wife_cash=self.initial_wife_cash.value(),
            husband_household_monthly=self.husband_household_monthly.value(),
            wife_household_monthly=self.wife_household_monthly.value(),
            husband_child_household_increment_monthly=self.husband_child_increment.value(),
            wife_child_household_increment_monthly=self.wife_child_increment.value(),
            husband_personal_spending_monthly=self.husband_personal_spending.value(),
            wife_personal_spending_monthly=self.wife_personal_spending.value(),
            household_shortfall_husband_percent=husband_ratio,
            household_shortfall_wife_percent=wife_ratio,
            minimum_personal_cash=self.minimum_personal_cash.value(),
            target_personal_cash=self.target_personal_cash.value(),
            auto_invest_enabled=self.auto_invest.isChecked(),
            minimum_household_cash=0,
            target_household_cash=0,
        )

    def show_recommendation(
        self,
        husband_monthly: float,
        wife_monthly: float,
        note: str,
    ) -> None:
        self.recommendation.setText(
            f"おすすめ投資枠　夫：月{husband_monthly/10_000:,.1f}万円　"
            f"妻：月{wife_monthly/10_000:,.1f}万円\n{note}"
        )
