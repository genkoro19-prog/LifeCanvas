from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from .models import CashFlowEvent, ProjectPlan


class CashFlowEventEditor(QGroupBox):
    FLOW_TYPES = (("支出", "expense"), ("収入", "income"))
    CATEGORIES = (
        ("家族", "family"),
        ("仕事", "work"),
        ("住宅", "housing"),
        ("車", "car"),
        ("旅行", "travel"),
        ("その他", "other"),
    )

    def __init__(self, plan: ProjectPlan):
        super().__init__("自由なライフイベント（臨時収入・臨時支出）")
        self.start_year = plan.start_year
        self.simulation_years = plan.simulation_years
        layout = QVBoxLayout(self)

        note = QLabel(
            "旅行、リフォーム、家電購入、援助、相続などを自由に追加できます。"
            "同じ年に複数のイベントを登録できます。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#666")
        layout.addWidget(note)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["年", "収支", "分類", "イベント", "金額"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(180)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_button = QPushButton("イベントを追加")
        remove_button = QPushButton("選択行を削除")
        add_button.clicked.connect(self.add_row)
        remove_button.clicked.connect(self.remove_selected)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.load(plan)

    @staticmethod
    def _edit(value: str | int | float = "") -> QLineEdit:
        edit = QLineEdit(str(value))
        edit.setAlignment(Qt.AlignRight)
        return edit

    @staticmethod
    def _combo(options: tuple[tuple[str, str], ...], selected: str) -> QComboBox:
        combo = QComboBox()
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(max(0, index))
        return combo

    def add_row(self, event: CashFlowEvent | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        year = self.start_year + event.offset if event else self.start_year + min(1, self.simulation_years - 1)
        self.table.setCellWidget(row, 0, self._edit(year))
        self.table.setCellWidget(
            row,
            1,
            self._combo(self.FLOW_TYPES, event.flow_type if event else "expense"),
        )
        self.table.setCellWidget(
            row,
            2,
            self._combo(self.CATEGORIES, event.category if event else "other"),
        )
        self.table.setCellWidget(
            row,
            3,
            QLineEdit(event.label if event else "新しいイベント"),
        )
        amount = f"{event.amount:,.0f}" if event else "0"
        self.table.setCellWidget(row, 4, self._edit(amount))

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def load(self, plan: ProjectPlan) -> None:
        self.start_year = plan.start_year
        self.simulation_years = plan.simulation_years
        self.table.setRowCount(0)
        for event in plan.cashflow_events:
            self.add_row(event)

    @staticmethod
    def _number(edit: QLineEdit) -> float:
        return float(edit.text().strip().replace(",", ""))

    def events(self) -> list[CashFlowEvent]:
        events: list[CashFlowEvent] = []
        last_year = self.start_year + self.simulation_years - 1
        for row in range(self.table.rowCount()):
            try:
                year = int(self._number(self.table.cellWidget(row, 0)))
                amount = self._number(self.table.cellWidget(row, 4))
            except (TypeError, ValueError) as exc:
                raise ValueError("ライフイベントの年と金額は数字で入力してください。") from exc
            if not self.start_year <= year <= last_year:
                raise ValueError(
                    f"ライフイベントの年は{self.start_year}〜{last_year}年で入力してください。"
                )
            if amount < 0:
                raise ValueError("ライフイベントの金額は0以上で入力してください。")
            label = self.table.cellWidget(row, 3).text().strip()
            if not label:
                raise ValueError("ライフイベント名を入力してください。")
            events.append(
                CashFlowEvent(
                    label=label,
                    offset=year - self.start_year,
                    flow_type=self.table.cellWidget(row, 1).currentData(),
                    category=self.table.cellWidget(row, 2).currentData(),
                    amount=amount,
                )
            )
        return sorted(events, key=lambda event: (event.offset, event.label))
