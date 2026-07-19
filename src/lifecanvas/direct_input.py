from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class NumberEdit(QWidget):
    """Direct number entry without spin buttons or mouse-wheel changes."""

    def __init__(
        self,
        value: float,
        unit: str = "円",
        decimals: int = 0,
        minimum: float = 0,
        maximum: float = 100_000_000,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.decimals = decimals
        self.minimum = minimum
        self.maximum = maximum

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setAlignment(Qt.AlignRight)
        self.edit.setMinimumWidth(140)
        self.edit.setClearButtonEnabled(True)
        self.unit_label = QLabel(unit)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.unit_label)

        self.set_value(value)
        self.edit.editingFinished.connect(self._format)

    def _parse(self) -> float:
        text = self.edit.text().strip().replace(",", "").replace(" ", "")
        if not text:
            return self.minimum
        try:
            value = float(text)
        except ValueError as exc:
            raise ValueError(f"数値で入力してください: {self.edit.text()}") from exc
        if not self.minimum <= value <= self.maximum:
            raise ValueError(f"{self.minimum:g}〜{self.maximum:g}の範囲で入力してください")
        return value

    def _format(self) -> None:
        try:
            self.set_value(self._parse())
        except ValueError:
            pass

    def value(self) -> float:
        return self._parse()

    def int_value(self) -> int:
        return int(round(self._parse()))

    def set_value(self, value: float) -> None:
        if self.decimals == 0:
            self.edit.setText(f"{value:,.0f}")
        else:
            self.edit.setText(f"{value:,.{self.decimals}f}")
