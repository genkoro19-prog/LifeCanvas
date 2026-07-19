from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .family import infer_work_reference_child
from .models import ChildPlan, ProjectPlan


class ChildEditor(QGroupBox):
    """Edit any number of children and choose the child used for work-stage timing."""

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__("子どもの設定", parent)
        layout = QVBoxLayout(self)

        description = QLabel(
            "子どもは自由に追加・削除できます。妻の育休や復職時期を連動させる基準の子も選べます。"
        )
        description.setWordWrap(True)
        description.setStyleSheet("color:#666;")
        layout.addWidget(description)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["名前", "誕生（開始から何年後）"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self._refresh_reference_choices)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_button = QPushButton("子どもを追加")
        remove_button = QPushButton("選択した子を削除")
        add_button.clicked.connect(self.add_child)
        remove_button.clicked.connect(self.remove_selected)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        reference_row = QHBoxLayout()
        reference_row.addWidget(QLabel("妻の働き方を連動させる子"))
        self.reference_child = QComboBox()
        self.reference_child.setMinimumWidth(180)
        reference_row.addWidget(self.reference_child)
        reference_row.addStretch()
        layout.addLayout(reference_row)

        self.load(plan)

    def load(self, plan: ProjectPlan) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for child in plan.children:
            self._append_row(child.name, child.birth_offset)
        self.table.blockSignals(False)
        self._refresh_reference_choices()

        reference = infer_work_reference_child(plan)
        if reference:
            index = self.reference_child.findText(reference)
            if index >= 0:
                self.reference_child.setCurrentIndex(index)
        elif self.reference_child.count():
            self.reference_child.setCurrentIndex(self.reference_child.count() - 1)

    def _append_row(self, name: str, birth_offset: int) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(name)
        offset_item = QTableWidgetItem(str(birth_offset))
        offset_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, offset_item)

    def add_child(self) -> None:
        number = self.table.rowCount() + 1
        default_offset = number + 3
        if self.table.rowCount():
            try:
                default_offset = int(self.table.item(self.table.rowCount() - 1, 1).text()) + 1
            except (AttributeError, ValueError):
                pass
        self._append_row(f"第{number}子", default_offset)
        self._refresh_reference_choices()

    def remove_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self._refresh_reference_choices()

    def _refresh_reference_choices(self, *_args) -> None:
        current = self.reference_child.currentText() if hasattr(self, "reference_child") else ""
        if not hasattr(self, "reference_child"):
            return
        names: list[str] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            name = item.text().strip() if item else ""
            if name:
                names.append(name)

        self.reference_child.blockSignals(True)
        self.reference_child.clear()
        self.reference_child.addItems(names)
        if current in names:
            self.reference_child.setCurrentText(current)
        elif names:
            self.reference_child.setCurrentIndex(len(names) - 1)
        self.reference_child.blockSignals(False)

    def children(self) -> list[ChildPlan]:
        children: list[ChildPlan] = []
        seen: set[str] = set()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            offset_item = self.table.item(row, 1)
            name = name_item.text().strip() if name_item else ""
            if not name:
                raise ValueError("子どもの名前を入力してください。")
            if name in seen:
                raise ValueError("子どもの名前は重複しないようにしてください。")
            seen.add(name)
            try:
                birth_offset = int((offset_item.text() if offset_item else "").replace(",", ""))
            except ValueError as exc:
                raise ValueError(f"{name}の誕生時期を整数で入力してください。") from exc
            if birth_offset < 0:
                raise ValueError(f"{name}の誕生時期は0以上で入力してください。")
            children.append(ChildPlan(name=name, birth_offset=birth_offset))
        return sorted(children, key=lambda child: (child.birth_offset, child.name))

    def reference_child_name(self) -> str | None:
        text = self.reference_child.currentText().strip()
        return text or None
