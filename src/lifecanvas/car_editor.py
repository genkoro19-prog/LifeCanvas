from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from .models import CarPlan, ProjectPlan


class CarEditor(QGroupBox):
    """A compact list of planned vehicles, without detailed loan modelling."""

    changed = Signal()

    def __init__(self, plan: ProjectPlan):
        super().__init__("車の予定")
        layout = QVBoxLayout(self)
        note = QLabel(
            "購入時期・価格・年間維持費・買い替え周期だけを設定します。必要な台数だけ追加してください。"
        )
        note.setWordWrap(True)
        note.setObjectName("sectionNote")
        layout.addWidget(note)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["車の名前", "購入年", "購入価格", "年間維持費", "買い替え周期", "買い替え価格"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(165)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_button = QPushButton("車を追加")
        remove_button = QPushButton("選択行を削除")
        add_button.clicked.connect(self.add_row)
        remove_button.clicked.connect(self.remove_selected)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.load(plan)

    @staticmethod
    def _edit(value: str | int | float = "", align_right: bool = True) -> QLineEdit:
        edit = QLineEdit(str(value))
        if align_right:
            edit.setAlignment(Qt.AlignRight)
        edit.editingFinished.connect(lambda: None)
        return edit

    def add_row(self, car: CarPlan | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        year = self.start_year + (car.purchase_offset if car else min(1, self.simulation_years - 1))
        values = [
            car.name if car else f"車{row + 1}",
            year,
            f"{(car.purchase_price if car else 0):,.0f}",
            f"{(car.annual_running_cost if car else 0):,.0f}",
            car.replacement_cycle_years or 0 if car else 0,
            f"{(car.replacement_price if car else 0):,.0f}",
        ]
        for column, value in enumerate(values):
            edit = self._edit(value, align_right=column != 0)
            edit.editingFinished.connect(self.changed)
            self.table.setCellWidget(row, column, edit)
        self.changed.emit()

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.changed.emit()

    def load(self, plan: ProjectPlan) -> None:
        self.start_year = plan.start_year
        self.simulation_years = plan.simulation_years
        self.table.setRowCount(0)
        cars = plan.cars or [plan.car]
        for car in cars:
            if car.enabled:
                self.add_row(car)

    @staticmethod
    def _number(edit: QLineEdit) -> float:
        text = edit.text().strip().replace(",", "")
        return float(text or 0)

    def cars(self) -> list[CarPlan]:
        cars: list[CarPlan] = []
        last_year = self.start_year + self.simulation_years - 1
        for row in range(self.table.rowCount()):
            name = self.table.cellWidget(row, 0).text().strip()
            if not name:
                raise ValueError("車の名前を入力してください。")
            try:
                year = int(self._number(self.table.cellWidget(row, 1)))
                purchase_price = self._number(self.table.cellWidget(row, 2))
                running_cost = self._number(self.table.cellWidget(row, 3))
                cycle = int(self._number(self.table.cellWidget(row, 4)))
                replacement_price = self._number(self.table.cellWidget(row, 5))
            except (TypeError, ValueError) as exc:
                raise ValueError("車の年・金額・周期は数字で入力してください。") from exc
            if not self.start_year <= year <= last_year:
                raise ValueError(f"車の購入年は{self.start_year}〜{last_year}年で入力してください。")
            if min(purchase_price, running_cost, cycle, replacement_price) < 0:
                raise ValueError("車の金額と周期は0以上で入力してください。")
            cars.append(
                CarPlan(
                    name=name,
                    enabled=True,
                    purchase_offset=year - self.start_year,
                    purchase_price=purchase_price,
                    annual_running_cost=running_cost,
                    replacement_cycle_years=cycle or None,
                    replacement_price=replacement_price,
                )
            )
        return sorted(cars, key=lambda item: (item.purchase_offset, item.name))
