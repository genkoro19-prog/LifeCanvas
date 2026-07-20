from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import PersonalDebt, ProjectPlan


class PersonalDebtEditor(QGroupBox):
    """Compact editor: name, borrower, monthly payment and remaining years are enough."""

    changed = Signal()
    COLUMNS = ("借入名", "借入者", "月額", "残り年数", "支払元")

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__("個人借入・奨学金", parent)
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

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
        remove_button = QPushButton("選択行を削除")
        add_button.clicked.connect(lambda _checked=False: self.add_debt())
        remove_button.clicked.connect(lambda _checked=False: self.remove_selected())
        actions.addWidget(add_button)
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
        name.setData(256, debt.debt_id)
        self.table.setItem(row, 0, name)
        self.table.setCellWidget(
            row,
            1,
            self._combo((("夫", "husband"), ("妻", "wife"), ("家計", "household")), debt.borrower),
        )
        self.table.setItem(row, 2, QTableWidgetItem(f"{debt.monthly_payment:.0f}"))
        years = debt.remaining_months / 12 if debt.remaining_months else 0
        self.table.setItem(row, 3, QTableWidgetItem(f"{years:g}"))
        self.table.setCellWidget(
            row,
            4,
            self._combo(
                (("本人", "borrower"), ("配偶者", "spouse"), ("家計", "household"), ("不足表示", "unmet")),
                debt.payment_source,
            ),
        )
        self._emit_changed()

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self._emit_changed()

    @staticmethod
    def _number(text: str, default: float = 0.0) -> float:
        try:
            return float(text.replace(",", "").strip())
        except (AttributeError, ValueError):
            return default

    def debts(self) -> list[PersonalDebt]:
        debts: list[PersonalDebt] = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            monthly_item = self.table.item(row, 2)
            years_item = self.table.item(row, 3)
            borrower = self.table.cellWidget(row, 1)
            source = self.table.cellWidget(row, 4)
            name = name_item.text().strip() if name_item else "個人借入"
            monthly = self._number(monthly_item.text() if monthly_item else "")
            years = self._number(years_item.text() if years_item else "")
            if monthly <= 0 or years <= 0:
                continue
            debt_id = str(name_item.data(256)) if name_item and name_item.data(256) else uuid4().hex
            debts.append(
                PersonalDebt(
                    debt_id=debt_id,
                    name=name or "個人借入",
                    borrower=borrower.currentData() if isinstance(borrower, QComboBox) else "household",
                    monthly_payment=monthly,
                    remaining_months=max(1, int(round(years * 12))),
                    payment_source=source.currentData() if isinstance(source, QComboBox) else "borrower",
                )
            )
        return debts

    def load(self, plan: ProjectPlan) -> None:
        self._loading = True
        try:
            self.table.setRowCount(0)
            for debt in plan.personal_debts:
                self.add_debt(debt)
        finally:
            self._loading = False
