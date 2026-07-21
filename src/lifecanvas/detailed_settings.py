from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QGroupBox):
    """A checkable detail section that leaves no blank area while closed."""

    def __init__(self, title: str = "詳細項目", parent: QWidget | None = None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 4, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(8)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        outer.addWidget(self.content)
        self.content.setVisible(False)
        self.toggled.connect(self.content.setVisible)


class DetailedSettingsPage(QWidget):
    """Category navigation with compact pages and a fixed recalculation action."""

    recalculateRequested = Signal()

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
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        title = QLabel("詳細設定")
        title.setStyleSheet("font-size:16px; font-weight:700;")
        self.status = QLabel("変更内容は自動計算されます")
        self.status.setStyleSheet("color:#667085;")
        self.recalculate_button = QPushButton("設定を反映して再計算")
        self.recalculate_button.setObjectName("primaryButton")
        self.recalculate_button.clicked.connect(
            lambda _checked=False: self._request_recalculation()
        )
        toolbar.addWidget(title)
        toolbar.addWidget(self.status)
        toolbar.addStretch()
        toolbar.addWidget(self.recalculate_button)
        root.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(8)
        self.categories = QListWidget()
        self.categories.setFixedWidth(172)
        self.categories.addItems(self.CATEGORIES)
        self.categories.setObjectName("detailCategoryList")
        body.addWidget(self.categories)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        pages: dict[str, dict[str, object]] = {}
        for category in self.CATEGORIES:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(12, 10, 12, 14)
            content_layout.setSpacing(8)

            primary_grid = QGridLayout()
            primary_grid.setHorizontalSpacing(10)
            primary_grid.setVerticalSpacing(8)
            primary_grid.setColumnStretch(0, 1)
            primary_grid.setColumnStretch(1, 1)
            content_layout.addLayout(primary_grid)

            advanced = CollapsibleSection("詳細項目を表示")
            advanced.hide()
            content_layout.addWidget(advanced)
            content_layout.addStretch()
            scroll.setWidget(content)
            self.stack.addWidget(scroll)
            pages[category] = {
                "primary": primary_grid,
                "advanced": advanced,
                "primary_count": 0,
                "advanced_count": 0,
            }

        self.category_widget_counts = {category: 0 for category in self.CATEGORIES}
        widgets = self._take_widgets(legacy_scroll)
        for widget in widgets:
            if widget.property("skipCompactSettings") is True:
                continue
            category = self._category_for(widget)
            self.category_widget_counts[category] += 1
            page = pages[category]
            primary_count = int(page["primary_count"])
            if primary_count < 2:
                grid = page["primary"]
                assert isinstance(grid, QGridLayout)
                grid.addWidget(widget, primary_count // 2, primary_count % 2, Qt.AlignTop)
                page["primary_count"] = primary_count + 1
            else:
                advanced = page["advanced"]
                assert isinstance(advanced, CollapsibleSection)
                advanced_count = int(page["advanced_count"])
                advanced.grid.addWidget(
                    widget,
                    advanced_count // 2,
                    advanced_count % 2,
                    Qt.AlignTop,
                )
                page["advanced_count"] = advanced_count + 1
                advanced.show()
            widget.show()
            self._compact(widget)

        for category in self.CATEGORIES:
            page = pages[category]
            primary_count = int(page["primary_count"])
            advanced_count = int(page["advanced_count"])
            primary = page["primary"]
            advanced = page["advanced"]
            assert isinstance(primary, QGridLayout)
            assert isinstance(advanced, CollapsibleSection)
            if primary_count == 0 and advanced_count == 0:
                note = QLabel("このカテゴリの設定項目はありません。")
                note.setStyleSheet("color:#6b7280; padding:12px;")
                primary.addWidget(note, 0, 0, 1, 2)
            if advanced_count == 0:
                advanced.hide()

        self.categories.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.categories.setCurrentRow(0)
        legacy_scroll.deleteLater()

    def _request_recalculation(self) -> None:
        self.status.setText("再計算しています…")
        top_level = self.window()

        # Ensure the detailed settings are the active input source. This avoids
        # a stale guided-input page overwriting values when the action is
        # triggered programmatically or through a keyboard shortcut.
        tabs = getattr(top_level, "tabs", None)
        if isinstance(tabs, QTabWidget):
            index = tabs.indexOf(self)
            if index >= 0:
                tabs.setCurrentIndex(index)

        self.recalculateRequested.emit()
        recalculate = getattr(top_level, "recalculate", None)
        if callable(recalculate):
            recalculate()
        self.status.setText("反映済み")

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
        explicit = widget.property("settingsCategory")
        if explicit in cls.CATEGORIES:
            return str(explicit)
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
