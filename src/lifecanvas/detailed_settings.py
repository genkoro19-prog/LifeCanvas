from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class DetailedSettingsPage(QWidget):
    """Turn the legacy long form into category navigation with compact two-column pages."""

    CATEGORIES = (
        "基本情報",
        "収入・働き方",
        "家計・預金",
        "NISA・投資",
        "子ども・教育",
        "住宅",
        "車",
        "借入・イベント",
        "年金・計算条件",
    )

    def __init__(self, legacy_scroll: QScrollArea, parent: QWidget | None = None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.categories = QListWidget()
        self.categories.setFixedWidth(172)
        self.categories.addItems(self.CATEGORIES)
        self.categories.setObjectName("detailCategoryList")
        root.addWidget(self.categories)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        pages: dict[str, tuple[QWidget, QGridLayout]] = {}
        for category in self.CATEGORIES:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            content = QWidget()
            grid = QGridLayout(content)
            grid.setContentsMargins(12, 10, 12, 14)
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            scroll.setWidget(content)
            self.stack.addWidget(scroll)
            pages[category] = (content, grid)

        widgets = self._take_widgets(legacy_scroll)
        counters = {category: 0 for category in self.CATEGORIES}
        for widget in widgets:
            if widget.isHidden() and widget.property("forceCompactVisible") is not True:
                continue
            category = self._category_for(widget)
            _, grid = pages[category]
            index = counters[category]
            grid.addWidget(widget, index // 2, index % 2, Qt.AlignTop)
            counters[category] += 1
            widget.show()
            self._compact(widget)

        for category in self.CATEGORIES:
            _, grid = pages[category]
            if counters[category] == 0:
                note = QLabel("このカテゴリの設定項目はありません。")
                note.setStyleSheet("color:#6b7280; padding:12px;")
                grid.addWidget(note, 0, 0, 1, 2)
            grid.setRowStretch((counters[category] + 1) // 2 + 1, 1)

        self.categories.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.categories.setCurrentRow(0)
        legacy_scroll.deleteLater()

    @staticmethod
    def _take_widgets(scroll: QScrollArea) -> list[QWidget]:
        content = scroll.widget()
        if content is None or content.layout() is None:
            return []
        layout = content.layout()
        widgets: list[QWidget] = []
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widgets.append(widget)
        return widgets

    @classmethod
    def _category_for(cls, widget: QWidget) -> str:
        title = widget.title() if isinstance(widget, QGroupBox) else ""
        key = f"{title} {widget.objectName()} {widget.__class__.__name__}".lower()
        if any(token in key for token in ("借入", "奨学", "イベント", "cashflow")):
            return "借入・イベント"
        if any(token in key for token in ("子ども", "教育", "child")):
            return "子ども・教育"
        if any(token in key for token in ("住宅", "住み替", "housing")):
            return "住宅"
        if any(token in key for token in ("車", "car")):
            return "車"
        if any(token in key for token in ("年金", "定年", "退職", "計算条件", "税", "社会保険")):
            return "年金・計算条件"
        if any(token in key for token in ("nisa", "投資", "運用")):
            return "NISA・投資"
        if any(token in key for token in ("家計", "預金", "財布", "wallet")):
            return "家計・預金"
        if any(token in key for token in ("収入", "働き", "勤務", "income")):
            return "収入・働き方"
        return "基本情報"

    @classmethod
    def _compact(cls, widget: QWidget) -> None:
        if isinstance(widget, QGroupBox):
            widget.setStyleSheet(
                "QGroupBox { margin-top:10px; padding:8px; }"
                "QGroupBox::title { left:9px; padding:0 3px; }"
            )
        for form in widget.findChildren(QFormLayout):
            form.setContentsMargins(8, 8, 8, 8)
            form.setHorizontalSpacing(10)
            form.setVerticalSpacing(4)
        for layout in widget.findChildren(QVBoxLayout):
            layout.setSpacing(min(layout.spacing() if layout.spacing() >= 0 else 6, 8))
        for edit in widget.findChildren(QLineEdit):
            edit.setMinimumHeight(30)
            edit.setMaximumHeight(34)
        for spin in widget.findChildren(QAbstractSpinBox):
            spin.setMinimumHeight(30)
            spin.setMaximumHeight(34)
