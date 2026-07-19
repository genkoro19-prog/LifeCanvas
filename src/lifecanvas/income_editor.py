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

from .models import IncomePeriod, ProjectPlan, SocialInsuranceMode


class HusbandIncomeEditor(QGroupBox):
    MODES = [
        ("会社員", SocialInsuranceMode.EMPLOYEE),
        ("扶養", SocialInsuranceMode.DEPENDENT),
        ("国民保険", SocialInsuranceMode.NATIONAL),
        ("なし", SocialInsuranceMode.NONE),
    ]

    def __init__(self, plan: ProjectPlan):
        super().__init__("夫の収入計画（期間ごと）")
        layout = QVBoxLayout(self)
        note = QLabel(
            "現役・継続雇用・副業などを年齢の区間で追加できます。"
            "終了年齢はその年齢になる直前までです。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#666")
        layout.addWidget(note)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["区分", "開始年齢", "終了年齢", "年収", "社会保険"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_button = QPushButton("期間を追加")
        delete_button = QPushButton("選択行を削除")
        add_button.clicked.connect(self.add_row)
        delete_button.clicked.connect(self.delete_row)
        buttons.addWidget(add_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.load(plan)

    @staticmethod
    def _edit(value: str | int | float = "") -> QLineEdit:
        edit = QLineEdit(str(value))
        edit.setAlignment(Qt.AlignRight)
        return edit

    def add_row(self, period: IncomePeriod | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(
            row,
            0,
            QLineEdit(period.label if period else "新しい収入期間"),
        )
        self.table.setCellWidget(
            row,
            1,
            self._edit(period.start_age if period else 60),
        )
        end_age = (
            ""
            if period and period.end_age is None
            else period.end_age
            if period
            else 65
        )
        self.table.setCellWidget(row, 2, self._edit(end_age))
        income = f"{period.annual_gross_income:,.0f}" if period else "0"
        self.table.setCellWidget(row, 3, self._edit(income))
        combo = QComboBox()
        for label, mode in self.MODES:
            combo.addItem(label, mode.value)
        if period:
            combo.setCurrentIndex(
                max(0, combo.findData(period.social_insurance_mode.value))
            )
        self.table.setCellWidget(row, 4, combo)

    def delete_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def load(self, plan: ProjectPlan) -> None:
        self.table.setRowCount(0)
        periods = [
            period
            for period in plan.income_periods
            if period.owner == "husband"
        ]
        if not periods:
            periods = [
                IncomePeriod(
                    owner="husband",
                    label="現在の勤務",
                    start_age=plan.husband.current_age,
                    end_age=plan.husband.retirement_age,
                    annual_gross_income=plan.husband.annual_gross_income,
                    social_insurance_mode=plan.husband.social_insurance_mode,
                )
            ]
        for period in periods:
            self.add_row(period)

    @staticmethod
    def _number(edit: QLineEdit, allow_blank: bool = False) -> float | None:
        text = edit.text().strip().replace(",", "")
        if allow_blank and not text:
            return None
        return float(text)

    def periods(self) -> list[IncomePeriod]:
        periods: list[IncomePeriod] = []
        for row in range(self.table.rowCount()):
            label = self.table.cellWidget(row, 0).text().strip() or "収入期間"
            start_age = int(self._number(self.table.cellWidget(row, 1)))
            raw_end = self._number(
                self.table.cellWidget(row, 2),
                allow_blank=True,
            )
            end_age = int(raw_end) if raw_end is not None else None
            income = self._number(self.table.cellWidget(row, 3))
            mode = SocialInsuranceMode(
                self.table.cellWidget(row, 4).currentData()
            )
            periods.append(
                IncomePeriod(
                    owner="husband",
                    label=label,
                    start_age=start_age,
                    end_age=end_age,
                    annual_gross_income=income,
                    social_insurance_mode=mode,
                )
            )
        return sorted(periods, key=lambda period: period.start_age)
