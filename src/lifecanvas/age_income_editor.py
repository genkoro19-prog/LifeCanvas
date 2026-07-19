from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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


class AgeIncomeEditor(QGroupBox):
    """Set annual income from a given age; end ages are inferred from the next row."""

    changed = Signal()

    MODES = (
        ("会社員", SocialInsuranceMode.EMPLOYEE),
        ("扶養", SocialInsuranceMode.DEPENDENT),
        ("国民保険", SocialInsuranceMode.NATIONAL),
        ("なし", SocialInsuranceMode.NONE),
    )

    def __init__(self, plan: ProjectPlan, owner: str, title: str):
        super().__init__(title)
        self.owner = owner
        self._benefits_by_start: dict[int, float] = {}

        layout = QVBoxLayout(self)
        note = QLabel(
            "『何歳から、年収いくら』だけを順番に設定します。"
            "終了年齢は次の行から自動計算されます。"
        )
        note.setWordWrap(True)
        note.setObjectName("sectionNote")
        layout.addWidget(note)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["区分", "この年齢から", "年収", "社会保険"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(155)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_button = QPushButton("年収変更を追加")
        remove_button = QPushButton("選択行を削除")
        add_button.clicked.connect(self.add_row)
        remove_button.clicked.connect(self.remove_selected)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.load(plan)

    @staticmethod
    def _edit(value: str | int | float = "", right: bool = False) -> QLineEdit:
        edit = QLineEdit(str(value))
        if right:
            edit.setAlignment(Qt.AlignRight)
        return edit

    def add_row(self, period: IncomePeriod | None = None) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        if period is None:
            person_age = self._current_age
            starts = [
                self._number(self.table.cellWidget(index, 1))
                for index in range(row)
            ]
            start_age = int(max(starts, default=person_age) + (5 if starts else 0))
            label = "年収変更"
            income = 0
            mode = SocialInsuranceMode.EMPLOYEE
        else:
            start_age = period.start_age
            label = period.label
            income = period.annual_gross_income
            mode = period.social_insurance_mode
            self._benefits_by_start[start_age] = period.annual_benefit

        label_edit = self._edit(label)
        age_edit = self._edit(start_age, right=True)
        income_edit = self._edit(f"{income:,.0f}", right=True)
        combo = QComboBox()
        for mode_label, mode_value in self.MODES:
            combo.addItem(mode_label, mode_value.value)
        combo.setCurrentIndex(max(0, combo.findData(mode.value)))

        self.table.setCellWidget(row, 0, label_edit)
        self.table.setCellWidget(row, 1, age_edit)
        self.table.setCellWidget(row, 2, income_edit)
        self.table.setCellWidget(row, 3, combo)

        label_edit.editingFinished.connect(self.changed)
        age_edit.editingFinished.connect(self.changed)
        income_edit.editingFinished.connect(self.changed)
        combo.currentIndexChanged.connect(self.changed)
        self.changed.emit()

    def remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()},
            reverse=True,
        )
        if not rows and self.table.currentRow() >= 0:
            rows = [self.table.currentRow()]
        for row in rows:
            self.table.removeRow(row)
        self.changed.emit()

    def load(self, plan: ProjectPlan) -> None:
        person = plan.husband if self.owner == "husband" else plan.wife
        self._current_age = person.current_age
        self._retirement_age = person.retirement_age
        self._pension_age = person.pension_start_age
        self._benefits_by_start = {}
        self.table.setRowCount(0)

        periods = sorted(
            [period for period in plan.income_periods if period.owner == self.owner],
            key=lambda item: item.start_age,
        )
        if not periods and self.owner == "wife":
            for stage in sorted(plan.wife_work_stages, key=lambda item: item.start_offset):
                start_age = person.current_age + stage.start_offset
                end_age = (
                    person.current_age + stage.end_offset
                    if stage.end_offset is not None
                    else None
                )
                if end_age is not None and end_age <= start_age:
                    continue
                periods.append(
                    IncomePeriod(
                        owner="wife",
                        label=stage.label,
                        start_age=start_age,
                        end_age=end_age,
                        annual_gross_income=stage.annual_gross_income,
                        annual_benefit=stage.annual_benefit,
                        social_insurance_mode=stage.social_insurance_mode,
                    )
                )
        if not periods:
            periods = [
                IncomePeriod(
                    owner=self.owner,
                    label="現在の勤務",
                    start_age=person.current_age,
                    end_age=person.retirement_age,
                    annual_gross_income=person.annual_gross_income,
                    social_insurance_mode=person.social_insurance_mode,
                )
            ]

        self.blockSignals(True)
        for period in periods:
            self.add_row(period)
        self.blockSignals(False)

    @staticmethod
    def _number(edit: QLineEdit) -> float:
        text = edit.text().strip().replace(",", "")
        return float(text or 0)

    def periods(self, plan: ProjectPlan) -> list[IncomePeriod]:
        person = plan.husband if self.owner == "husband" else plan.wife
        rows: list[tuple[int, str, float, SocialInsuranceMode]] = []
        for row in range(self.table.rowCount()):
            label = self.table.cellWidget(row, 0).text().strip() or "収入期間"
            try:
                start_age = int(self._number(self.table.cellWidget(row, 1)))
                income = self._number(self.table.cellWidget(row, 2))
            except (TypeError, ValueError) as exc:
                raise ValueError("年齢と年収は数字で入力してください。") from exc
            if start_age < person.current_age:
                raise ValueError(
                    f"{person.name}の開始年齢は現在の{person.current_age}歳以上にしてください。"
                )
            if income < 0:
                raise ValueError("年収は0円以上で入力してください。")
            mode = SocialInsuranceMode(self.table.cellWidget(row, 3).currentData())
            rows.append((start_age, label, income, mode))

        rows.sort(key=lambda item: item[0])
        starts = [item[0] for item in rows]
        if len(starts) != len(set(starts)):
            raise ValueError(f"{person.name}の同じ開始年齢が重複しています。")

        periods: list[IncomePeriod] = []
        for index, (start_age, label, income, mode) in enumerate(rows):
            if index + 1 < len(rows):
                end_age = rows[index + 1][0]
            else:
                end_age = (
                    max(person.pension_start_age, start_age + 1)
                    if start_age >= person.retirement_age
                    else person.retirement_age
                )
            if end_age <= start_age:
                raise ValueError(f"{person.name}の収入期間の年齢順を確認してください。")
            periods.append(
                IncomePeriod(
                    owner=self.owner,
                    label=label,
                    start_age=start_age,
                    end_age=end_age,
                    annual_gross_income=income,
                    annual_benefit=self._benefits_by_start.get(start_age, 0),
                    social_insurance_mode=mode,
                )
            )
        return periods
