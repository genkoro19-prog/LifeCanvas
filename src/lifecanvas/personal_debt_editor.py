from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import PersonalDebt, ProjectPlan
from .widgets import NumberEdit


BORROWERS = (("夫", "husband"), ("妻", "wife"), ("家計", "household"))
PAYMENT_SOURCES = (
    ("本人", "borrower"),
    ("配偶者", "spouse"),
    ("家計", "household"),
    ("不足表示", "unmet"),
)
REPAYMENT_METHODS = (
    ("月額固定", "fixed"),
    ("元利均等", "equal_payment"),
    ("元金均等", "equal_principal"),
)


class PersonalDebtDetailDialog(QDialog):
    """Detailed debt assumptions kept out of the compact quick-entry table."""

    def __init__(self, debt: PersonalDebt, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"{debt.name}の詳細設定")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        note = QLabel(
            "元金や金利が不明な場合は、月額と残り期間だけで固定支出として計算します。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#667085;")
        root.addWidget(note)

        form = QFormLayout()
        form.setVerticalSpacing(6)
        self.current_balance = NumberEdit(debt.current_balance)
        self.principal = NumberEdit(debt.principal)
        self.interest = NumberEdit(debt.annual_interest_rate, "%/年", decimals=2, maximum=100)
        self.start_months = NumberEdit(debt.start_offset_months, "か月後", maximum=1_200)
        self.bonus = NumberEdit(debt.bonus_payment, "円/回")
        self.method = QComboBox()
        for label, value in REPAYMENT_METHODS:
            self.method.addItem(label, value)
        self.method.setCurrentIndex(max(0, self.method.findData(debt.repayment_method)))
        self.source = QComboBox()
        for label, value in PAYMENT_SOURCES:
            self.source.addItem(label, value)
        self.source.setCurrentIndex(max(0, self.source.findData(debt.payment_source)))
        self.notes = QPlainTextEdit(debt.notes)
        self.notes.setMaximumHeight(84)
        form.addRow("現在残高", self.current_balance)
        form.addRow("当初元金", self.principal)
        form.addRow("年利", self.interest)
        form.addRow("返済開始", self.start_months)
        form.addRow("ボーナス返済", self.bonus)
        form.addRow("返済方式", self.method)
        form.addRow("本人資金不足時", self.source)
        form.addRow("備考", self.notes)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def apply_to(self, debt: PersonalDebt) -> PersonalDebt:
        return debt.model_copy(
            update={
                "current_balance": self.current_balance.value(),
                "principal": self.principal.value(),
                "annual_interest_rate": self.interest.value(),
                "start_offset_months": self.start_months.int_value(),
                "bonus_payment": self.bonus.value(),
                "repayment_method": self.method.currentData(),
                "payment_source": self.source.currentData(),
                "notes": self.notes.toPlainText().strip(),
            }
        )


class PersonalDebtEditor(QGroupBox):
    """Quick debt entry with an optional detailed editor."""

    changed = Signal()
    COLUMNS = ("借入名", "借入者", "月額", "残り年数", "支払元")
    DETAIL_ROLE = int(Qt.UserRole) + 1

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__("個人借入・奨学金", parent)
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        note = QLabel("通常は借入名・借入者・月額・残り年数だけで登録できます。")
        note.setStyleSheet("color:#667085;")
        layout.addWidget(note)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(self.COLUMNS)):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(145)
        self.table.itemChanged.connect(lambda _item: self._emit_changed())
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        add_button = QPushButton("借入を追加")
        detail_button = QPushButton("選択行の詳細設定")
        remove_button = QPushButton("選択行を削除")
        add_button.clicked.connect(lambda _checked=False: self.add_debt())
        detail_button.clicked.connect(lambda _checked=False: self.edit_selected())
        remove_button.clicked.connect(lambda _checked=False: self.remove_selected())
        actions.addWidget(add_button)
        actions.addWidget(detail_button)
        actions.addWidget(remove_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.load(plan)

    def _emit_changed(self) -> None:
        if not self._loading:
            self.changed.emit()

    def _combo(self, items: tuple[tuple[str, str], ...], value: str) -> QComboBox:
        combo = QComboBox()
        for label, data in items:
            combo.addItem(label, data)
        combo.setCurrentIndex(max(0, combo.findData(value)))
        combo.currentIndexChanged.connect(lambda _index: self._emit_changed())
        return combo

    def add_debt(self, debt: PersonalDebt | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        debt = debt or PersonalDebt(
            debt_id=uuid4().hex,
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=8 * 12,
        )
        name = QTableWidgetItem(debt.name)
        name.setData(Qt.UserRole, debt.debt_id)
        name.setData(self.DETAIL_ROLE, debt.model_dump(mode="json"))
        self.table.setItem(row, 0, name)
        self.table.setCellWidget(row, 1, self._combo(BORROWERS, debt.borrower))
        self.table.setItem(row, 2, QTableWidgetItem(f"{debt.monthly_payment:.0f}"))
        years = debt.remaining_months / 12 if debt.remaining_months else 0
        self.table.setItem(row, 3, QTableWidgetItem(f"{years:g}"))
        self.table.setCellWidget(row, 4, self._combo(PAYMENT_SOURCES, debt.payment_source))
        self._emit_changed()

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self._emit_changed()

    def edit_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        debt = self._debt_for_row(row)
        if debt is None:
            return
        dialog = PersonalDebtDetailDialog(debt, self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = dialog.apply_to(debt)
        name_item = self.table.item(row, 0)
        if name_item is not None:
            name_item.setData(self.DETAIL_ROLE, updated.model_dump(mode="json"))
        source = self.table.cellWidget(row, 4)
        if isinstance(source, QComboBox):
            source.setCurrentIndex(max(0, source.findData(updated.payment_source)))
        self._emit_changed()

    @staticmethod
    def _number(text: str, default: float = 0.0) -> float:
        try:
            return float(text.replace(",", "").strip())
        except (AttributeError, ValueError):
            return default

    def _debt_for_row(self, row: int) -> PersonalDebt | None:
        name_item = self.table.item(row, 0)
        monthly_item = self.table.item(row, 2)
        years_item = self.table.item(row, 3)
        borrower = self.table.cellWidget(row, 1)
        source = self.table.cellWidget(row, 4)
        name = name_item.text().strip() if name_item else "個人借入"
        monthly = self._number(monthly_item.text() if monthly_item else "")
        years = self._number(years_item.text() if years_item else "")
        if monthly <= 0 or years <= 0:
            return None
        stored = name_item.data(self.DETAIL_ROLE) if name_item else None
        data = dict(stored) if isinstance(stored, dict) else {}
        data.update(
            {
                "debt_id": str(name_item.data(Qt.UserRole))
                if name_item and name_item.data(Qt.UserRole)
                else uuid4().hex,
                "name": name or "個人借入",
                "borrower": borrower.currentData()
                if isinstance(borrower, QComboBox)
                else "household",
                "monthly_payment": monthly,
                "remaining_months": max(1, int(round(years * 12))),
                "payment_source": source.currentData()
                if isinstance(source, QComboBox)
                else data.get("payment_source", "borrower"),
            }
        )
        return PersonalDebt.model_validate(data)

    def debts(self) -> list[PersonalDebt]:
        debts: list[PersonalDebt] = []
        for row in range(self.table.rowCount()):
            debt = self._debt_for_row(row)
            if debt is not None:
                debts.append(debt)
        return debts

    def load(self, plan: ProjectPlan) -> None:
        self._loading = True
        try:
            self.table.setRowCount(0)
            for debt in plan.personal_debts:
                self.add_debt(debt)
        finally:
            self._loading = False
