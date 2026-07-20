from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
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
        super().__init__("家計・預金・NISA配分", parent)
        self._loading = False
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem("すべて共同家計に合算（従来方式）", "combined")
        self.mode.addItem("夫婦の預金を分ける", "separate")
        header.addWidget(QLabel("家計モード"))
        header.addWidget(self.mode, 1)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.addWidget(self._build_husband_group(), 0, 0)
        grid.addWidget(self._build_wife_group(), 0, 1)
        grid.addWidget(self._build_investment_group(), 1, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

        # Hidden compatibility controls keep older saved workflows and tests usable.
        # The new policy engine does not use a fixed husband cap or shortfall ratio.
        self.husband_household_monthly = NumberEdit(0, "円/月", parent=self)
        self.husband_child_increment = NumberEdit(0, "円/月", parent=self)
        self.shortfall_husband_percent = NumberEdit(100, "%", maximum=100, parent=self)
        self.shortfall_wife_percent = NumberEdit(0, "%", maximum=100, parent=self)
        self.minimum_personal_cash = self.husband_minimum_cash
        self.target_personal_cash = self.husband_target_cash
        for compatibility_widget in (
            self.husband_household_monthly,
            self.husband_child_increment,
            self.shortfall_husband_percent,
            self.shortfall_wife_percent,
        ):
            compatibility_widget.hide()

        actions = QHBoxLayout()
        self.recommend_button = QPushButton("おすすめ基本NISAを試算")
        self.recommend_button.clicked.connect(
            lambda _checked=False: self.recommendationRequested.emit()
        )
        actions.addWidget(self.recommend_button)
        actions.addStretch()
        root.addLayout(actions)

        self.recommendation = QLabel("家計成立と夫の最低維持預金を守れる基本NISAを試算します。")
        self.recommendation.setWordWrap(True)
        self.recommendation.setStyleSheet(
            "background:#eef6ff; color:#174a7c; padding:8px; border-radius:7px;"
        )
        root.addWidget(self.recommendation)
        self._connect_changes()
        self.load(plan)

    def _form(self, parent: QGroupBox) -> QFormLayout:
        form = QFormLayout(parent)
        form.setContentsMargins(10, 10, 10, 10)
        form.setVerticalSpacing(5)
        form.setHorizontalSpacing(10)
        return form

    def _build_husband_group(self) -> QGroupBox:
        group = QGroupBox("夫・家計の土台")
        form = self._form(group)
        self.initial_husband_cash = NumberEdit(0)
        self.husband_personal_spending = NumberEdit(0, "円/月")
        self.husband_minimum_cash = NumberEdit(1_000_000)
        self.husband_target_cash = NumberEdit(3_000_000)
        self.husband_monthly_saving = NumberEdit(50_000, "円/月")
        form.addRow("現在の預金", self.initial_husband_cash)
        form.addRow("個人支出", self.husband_personal_spending)
        form.addRow("最低維持預金", self.husband_minimum_cash)
        form.addRow("目標預金", self.husband_target_cash)
        form.addRow("目標までの基本貯金", self.husband_monthly_saving)
        return group

    def _build_wife_group(self) -> QGroupBox:
        group = QGroupBox("妻・余剰だけ家計へ")
        form = self._form(group)
        self.initial_wife_cash = NumberEdit(0)
        self.wife_personal_spending = NumberEdit(0, "円/月")
        self.wife_contribution_threshold = NumberEdit(30_000, "円/月")
        self.wife_household_monthly = NumberEdit(100_000, "円/月")
        self.use_wife_cash = QCheckBox("収入不足時に妻の既存預金も家計へ使う")
        form.addRow("現在の預金", self.initial_wife_cash)
        form.addRow("個人支出", self.wife_personal_spending)
        form.addRow("家計に入れず残す余裕", self.wife_contribution_threshold)
        form.addRow("家計負担上限", self.wife_household_monthly)
        form.addRow(self.use_wife_cash)
        return group

    def _build_investment_group(self) -> QGroupBox:
        group = QGroupBox("余剰投資")
        form = self._form(group)
        self.auto_invest = QCheckBox("目標預金を超えた余剰をNISAへ自動追加する")
        self.auto_extra_cap = NumberEdit(300_000, "円/月", maximum=300_000)
        self.spouse_transfer_enabled = QCheckBox("夫NISA満額後に妻NISAへ資金移転する")
        self.spouse_transfer_limit = NumberEdit(1_100_000, "円/年")
        self.other_transfers = NumberEdit(0, "円/年")
        self.after_destination = QComboBox()
        self.after_destination.addItem("夫の預金に残す", "husband_cash")
        self.after_destination.addItem("夫の課税口座", "husband_taxable")
        self.after_destination.addItem("妻の課税口座", "wife_taxable")
        self.after_destination.addItem("住宅ローン繰上返済", "mortgage")
        self.after_destination.addItem("その他目標", "other_goal")
        form.addRow(self.auto_invest)
        form.addRow("追加投資の月上限", self.auto_extra_cap)
        form.addRow(self.spouse_transfer_enabled)
        form.addRow("年間資金移転管理上限", self.spouse_transfer_limit)
        form.addRow("当年のその他資金移転", self.other_transfers)
        form.addRow("NISA後の余剰先", self.after_destination)
        return group

    def _number_edits(self) -> tuple[NumberEdit, ...]:
        return (
            self.initial_husband_cash,
            self.husband_personal_spending,
            self.husband_minimum_cash,
            self.husband_target_cash,
            self.husband_monthly_saving,
            self.initial_wife_cash,
            self.wife_personal_spending,
            self.wife_contribution_threshold,
            self.wife_household_monthly,
            self.auto_extra_cap,
            self.spouse_transfer_limit,
            self.other_transfers,
            self.husband_household_monthly,
            self.husband_child_increment,
            self.shortfall_husband_percent,
            self.shortfall_wife_percent,
        )

    def _connect_changes(self) -> None:
        self.mode.currentIndexChanged.connect(self._mode_changed)
        for editor in self._number_edits():
            editor.edit.editingFinished.connect(self._emit_changed)
        for checkbox in (self.use_wife_cash, self.auto_invest, self.spouse_transfer_enabled):
            checkbox.toggled.connect(lambda _checked: self._emit_changed())
        self.after_destination.currentIndexChanged.connect(lambda _index: self._emit_changed())

    def _emit_changed(self) -> None:
        if not self._loading:
            self.changed.emit()

    def _mode_changed(self, *_args) -> None:
        enabled = self.mode.currentData() == "separate"
        for widget in (
            *self._number_edits(),
            self.use_wife_cash,
            self.auto_invest,
            self.spouse_transfer_enabled,
            self.after_destination,
            self.recommend_button,
        ):
            widget.setEnabled(enabled)
        self._emit_changed()

    def load(self, plan: ProjectPlan) -> None:
        self._loading = True
        try:
            wallet = plan.wallets
            self.mode.setCurrentIndex(max(0, self.mode.findData(wallet.mode)))
            self.initial_husband_cash.set_value(wallet.initial_husband_cash)
            self.initial_wife_cash.set_value(wallet.initial_wife_cash)
            self.husband_personal_spending.set_value(wallet.husband_personal_spending_monthly)
            self.wife_personal_spending.set_value(wallet.wife_personal_spending_monthly)
            self.husband_minimum_cash.set_value(wallet.husband_minimum_cash)
            self.husband_target_cash.set_value(wallet.husband_target_cash)
            self.husband_monthly_saving.set_value(wallet.husband_monthly_saving_until_target)
            self.wife_contribution_threshold.set_value(wallet.wife_contribution_threshold_monthly)
            self.wife_household_monthly.set_value(wallet.wife_household_monthly)
            self.husband_household_monthly.set_value(wallet.husband_household_monthly)
            self.husband_child_increment.set_value(
                wallet.husband_child_household_increment_monthly
            )
            self.shortfall_husband_percent.set_value(
                wallet.household_shortfall_husband_percent
            )
            self.shortfall_wife_percent.set_value(
                wallet.household_shortfall_wife_percent
            )
            self.use_wife_cash.setChecked(wallet.wife_use_existing_cash_for_household)
            self.auto_invest.setChecked(wallet.auto_invest_enabled)
            self.auto_extra_cap.set_value(wallet.auto_extra_monthly_cap)
            self.spouse_transfer_enabled.setChecked(wallet.spouse_nisa_transfer_enabled)
            self.spouse_transfer_limit.set_value(wallet.spouse_nisa_annual_management_limit)
            self.other_transfers.set_value(wallet.spouse_nisa_other_transfers_this_year)
            self.after_destination.setCurrentIndex(
                max(0, self.after_destination.findData(wallet.after_nisa_destination))
            )
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
            husband_child_household_increment_monthly=self.husband_child_increment.value(),
            wife_child_household_increment_monthly=0,
            husband_personal_spending_monthly=self.husband_personal_spending.value(),
            wife_personal_spending_monthly=self.wife_personal_spending.value(),
            wife_contribution_threshold_monthly=self.wife_contribution_threshold.value(),
            wife_use_existing_cash_for_household=self.use_wife_cash.isChecked(),
            husband_minimum_cash=self.husband_minimum_cash.value(),
            husband_target_cash=self.husband_target_cash.value(),
            husband_monthly_saving_until_target=self.husband_monthly_saving.value(),
            auto_invest_enabled=self.auto_invest.isChecked(),
            auto_extra_monthly_cap=self.auto_extra_cap.value(),
            spouse_nisa_transfer_enabled=self.spouse_transfer_enabled.isChecked(),
            spouse_nisa_annual_management_limit=self.spouse_transfer_limit.value(),
            spouse_nisa_other_transfers_this_year=self.other_transfers.value(),
            after_nisa_destination=self.after_destination.currentData(),
            household_shortfall_husband_percent=self.shortfall_husband_percent.value(),
            household_shortfall_wife_percent=self.shortfall_wife_percent.value(),
            minimum_personal_cash=self.husband_minimum_cash.value(),
            target_personal_cash=self.husband_target_cash.value(),
        )

    def show_recommendation(self, husband_monthly: float, wife_monthly: float, note: str) -> None:
        self.recommendation.setText(
            f"おすすめ基本NISA　夫：月{husband_monthly/10_000:,.1f}万円　"
            f"妻：月{wife_monthly/10_000:,.1f}万円\n{note}"
        )
