from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGridLayout, QGroupBox, QLabel, QWidget

from .models import ProjectPlan
from .personal_debt_editor import PersonalDebtEditor
from .widgets import NumberEdit


class QuickPolicyEditor(QGroupBox):
    changed = Signal()

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__("4. 家計ルールと個人借入", parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        policy = QGroupBox("育休時の家計と夫婦の預金")
        form = QFormLayout(policy)
        form.setVerticalSpacing(5)
        self.wife_threshold = NumberEdit(30_000, "円/月")
        self.wife_cap = NumberEdit(100_000, "円/月")
        self.wife_target = NumberEdit(3_000_000)
        self.husband_minimum = NumberEdit(1_000_000)
        self.husband_target = NumberEdit(3_000_000)
        self.husband_saving = NumberEdit(50_000, "円/月")
        form.addRow("妻の家計拠出開始基準", self.wife_threshold)
        form.addRow("妻の家計負担上限", self.wife_cap)
        form.addRow("妻の目標預金", self.wife_target)
        form.addRow("夫の最低維持預金", self.husband_minimum)
        form.addRow("夫の目標預金", self.husband_target)
        form.addRow("目標までの基本貯金", self.husband_saving)
        note = QLabel("妻は借入・個人支出・本人NISAを優先し、余剰が基準を超えた月は余剰全体を上限まで家計へ入れます。")
        note.setWordWrap(True)
        form.addRow(note)

        self.debts = PersonalDebtEditor(plan)
        grid.addWidget(policy, 0, 0)
        grid.addWidget(self.debts, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for editor in (
            self.wife_threshold,
            self.wife_cap,
            self.wife_target,
            self.husband_minimum,
            self.husband_target,
            self.husband_saving,
        ):
            editor.edit.editingFinished.connect(self.changed)
        self.debts.changed.connect(self.changed)
        self.load(plan)

    def apply_to(self, plan: ProjectPlan) -> None:
        wallet = plan.wallets
        wallet.wife_contribution_threshold_monthly = self.wife_threshold.value()
        wallet.wife_household_monthly = self.wife_cap.value()
        wallet.wife_target_cash = self.wife_target.value()
        wallet.husband_minimum_cash = self.husband_minimum.value()
        wallet.husband_target_cash = self.husband_target.value()
        wallet.husband_monthly_saving_until_target = self.husband_saving.value()
        wallet.household_shortfall_husband_percent = 100
        wallet.household_shortfall_wife_percent = 0
        plan.personal_debts = self.debts.debts()

    def load(self, plan: ProjectPlan) -> None:
        wallet = plan.wallets
        self.wife_threshold.set_value(wallet.wife_contribution_threshold_monthly)
        self.wife_cap.set_value(wallet.wife_household_monthly)
        self.wife_target.set_value(wallet.wife_target_cash)
        self.husband_minimum.set_value(wallet.husband_minimum_cash)
        self.husband_target.set_value(wallet.husband_target_cash)
        self.husband_saving.set_value(wallet.husband_monthly_saving_until_target)
        self.debts.load(plan)
