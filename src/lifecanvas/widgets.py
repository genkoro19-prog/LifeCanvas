from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from .timeline import LifeEvent, LifePeriod, build_life_events, build_life_periods


class NumberEdit(QWidget):
    """Direct numeric input without spin buttons or mouse-wheel changes."""

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
        self.edit.setMinimumWidth(150)
        self.edit.setClearButtonEnabled(True)
        self.edit.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #cfd5dc; border-radius: 7px; "
            "padding: 8px 10px; font-size: 14px; }"
            "QLineEdit:focus { border: 2px solid #1769e0; padding: 7px 9px; }"
        )
        self.unit_label = QLabel(unit)
        self.unit_label.setMinimumWidth(42)
        self.unit_label.setStyleSheet("color: #5f6670;")
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.unit_label)

        self.set_value(value)
        self.edit.editingFinished.connect(self._format_text)

    def _parse(self) -> float:
        text = self.edit.text().strip().replace(",", "").replace(" ", "")
        if not text:
            return self.minimum
        try:
            value = float(text)
        except ValueError:
            value = self.minimum
        return min(self.maximum, max(self.minimum, value))

    def _format_text(self) -> None:
        self.set_value(self._parse())

    def value(self) -> float:
        return self._parse()

    def int_value(self) -> int:
        return int(round(self._parse()))

    def set_value(self, value: float) -> None:
        value = min(self.maximum, max(self.minimum, value))
        if self.decimals == 0:
            text = f"{value:,.0f}"
        else:
            text = f"{value:,.{self.decimals}f}"
        self.edit.setText(text)


class LifeTimelineView(QGraphicsView):
    CATEGORY_INFO = {
        "family": ("家族・子ども", "#2E7D32", "#E8F5E9"),
        "work": ("仕事・年金", "#6A1B9A", "#F3E5F5"),
        "housing": ("住宅・ローン", "#1565C0", "#E3F2FD"),
        "car": ("車", "#EF6C00", "#FFF3E0"),
        "assets": ("資産形成", "#00838F", "#E0F7FA"),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setMinimumHeight(620)

    def set_plan(self, plan) -> None:
        events = build_life_events(plan)
        periods = build_life_periods(plan)
        scene = QGraphicsScene(self)

        year_width = 150
        left_margin = 150
        top_margin = 65
        lane_height = 225
        categories = list(self.CATEGORY_INFO)
        width = left_margin + plan.simulation_years * year_width + 180
        height = top_margin + len(categories) * lane_height + 70
        scene.setSceneRect(0, 0, width, height)

        title = scene.addText("ライフイベント年表")
        title.setFont(QFont("", 16, QFont.Bold))
        title.setPos(16, 8)
        hint = scene.addText("横方向にスクロールできます。ドラッグでも移動できます。")
        hint.setDefaultTextColor(QColor("#6b7280"))
        hint.setPos(210, 13)

        for offset in range(plan.simulation_years):
            x = left_margin + offset * year_width
            year = plan.start_year + offset
            line_pen = QPen(QColor("#d8dde3"))
            line_pen.setWidth(2 if offset % 5 == 0 else 1)
            scene.addLine(x, top_margin - 8, x, height - 35, line_pen)
            if offset % 2 == 0 or offset < 5:
                year_text = scene.addText(str(year))
                year_text.setDefaultTextColor(QColor("#4b5563"))
                year_text.setPos(x - 18, top_margin - 35)

        for lane_index, category in enumerate(categories):
            label, line_color, background = self.CATEGORY_INFO[category]
            y = top_margin + lane_index * lane_height
            scene.addRect(0, y, width, lane_height - 8, QPen(Qt.NoPen), QColor(background))
            label_item = scene.addText(label)
            label_item.setFont(QFont("", 11, QFont.Bold))
            label_item.setDefaultTextColor(QColor(line_color))
            label_item.setPos(14, y + 12)
            for marker_offset in range(0, plan.simulation_years, 10):
                marker = scene.addText(label)
                marker.setDefaultTextColor(QColor(line_color))
                marker.setOpacity(0.22)
                marker.setFont(QFont("", 12, QFont.Bold))
                marker.setPos(left_margin + marker_offset * year_width + 12, y + 7)
            scene.addLine(left_margin, y + 38, width - 20, y + 38, QPen(QColor(line_color), 2))

        self._draw_periods(scene, plan, periods, left_margin, top_margin, lane_height, year_width)
        self._draw_events(scene, plan, events, left_margin, top_margin, lane_height, year_width)
        self.setScene(scene)
        self.setSceneRect(scene.sceneRect())
        QTimer.singleShot(0, self.scroll_to_start)

    def scroll_to_start(self) -> None:
        try:
            horizontal = self.horizontalScrollBar()
            vertical = self.verticalScrollBar()
            horizontal.setValue(horizontal.minimum())
            vertical.setValue(vertical.minimum())
        except RuntimeError:
            # A zero-delay callback may outlive a window that was closed immediately
            # by a UI test or during rapid page replacement.
            return

    def _draw_periods(
        self,
        scene: QGraphicsScene,
        plan,
        periods: list[LifePeriod],
        left_margin: int,
        top_margin: int,
        lane_height: int,
        year_width: int,
    ) -> None:
        categories = list(self.CATEGORY_INFO)
        period_slot: dict[str, int] = {category: 0 for category in categories}
        for period in periods:
            if period.category not in categories:
                continue
            lane_index = categories.index(period.category)
            slot = period_slot[period.category] % 2
            period_slot[period.category] += 1
            y = top_margin + lane_index * lane_height + 48 + slot * 25
            x = left_margin + period.start_offset * year_width + 4
            end = min(plan.simulation_years - 1, period.end_offset)
            width = max(70, (end - period.start_offset + 1) * year_width - 8)
            color = QColor(self.CATEGORY_INFO[period.category][1])
            color.setAlpha(42)
            scene.addRect(x, y, width, 19, QPen(QColor(self.CATEGORY_INFO[period.category][1]), 1), color)
            text = scene.addText(period.title)
            text.setDefaultTextColor(QColor(self.CATEGORY_INFO[period.category][1]))
            text.setScale(0.72)
            text.setPos(x + 5, y - 2)

    def _draw_events(
        self,
        scene: QGraphicsScene,
        plan,
        events: list[LifeEvent],
        left_margin: int,
        top_margin: int,
        lane_height: int,
        year_width: int,
    ) -> None:
        categories = list(self.CATEGORY_INFO)
        event_counts: dict[tuple[str, int], int] = {}
        card_width = 140
        card_height = 54

        for event in events:
            if event.category not in categories or event.offset >= plan.simulation_years:
                continue
            lane_index = categories.index(event.category)
            x = left_margin + event.offset * year_width + 5
            key = (event.category, event.offset)
            slot = event_counts.get(key, 0) % 2
            event_counts[key] = event_counts.get(key, 0) + 1
            y = top_margin + lane_index * lane_height + 102 + slot * 58

            border = QColor(self.CATEGORY_INFO[event.category][1])
            scene.addRect(x, y, card_width, card_height, QPen(border, 1), QColor("#ffffff"))
            scene.addLine(
                left_margin + event.offset * year_width,
                top_margin + lane_index * lane_height + 38,
                x + 8,
                y,
                QPen(border, 1),
            )
            year_text = scene.addText(str(plan.start_year + event.offset))
            year_text.setDefaultTextColor(border)
            year_text.setScale(0.72)
            year_text.setPos(x + 6, y + 2)
            title = scene.addText(event.title)
            title.setFont(QFont("", 8, QFont.Bold))
            title.setTextWidth(card_width - 12)
            title.setPos(x + 6, y + 16)
            if event.detail:
                detail = scene.addText(event.detail)
                detail.setDefaultTextColor(QColor("#6b7280"))
                detail.setScale(0.68)
                detail.setTextWidth((card_width - 12) / 0.68)
                detail.setPos(x + 6, y + 36)
