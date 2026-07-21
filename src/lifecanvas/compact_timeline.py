from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from .timeline import LifeEvent, build_life_events, build_life_periods


class CompactTimelineView(QGraphicsView):
    eventSelected = Signal(int, object)

    LANES = [
        ("husband", "夫の仕事・収入", "#5E35B1"),
        ("wife", "妻の仕事・収入", "#8E24AA"),
        ("family", "子ども・教育", "#2E7D32"),
        ("housing", "住宅・ローン", "#1565C0"),
        ("car", "車", "#EF6C00"),
        ("assets", "資産・注意", "#00838F"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor("#f7f8fa"))
        self.setMinimumHeight(520)
        self._ready = False

    def _lane(self, event: LifeEvent) -> str:
        if event.owner in ("husband", "wife"):
            return event.owner
        lane_names = {lane[0] for lane in self.LANES}
        return event.category if event.category in lane_names else "assets"

    def set_data(self, plan, results) -> None:
        scene = QGraphicsScene(self)
        width, height = 1180, 520
        left, right, top = 150, 25, 55
        lane_height = 70
        usable_width = width - left - right
        scene.setSceneRect(0, 0, width, height)

        title = scene.addText("ライフイベント全体像")
        title.setFont(QFont("", 15, QFont.Bold))
        title.setPos(12, 8)

        for offset in range(0, plan.simulation_years, 5):
            x = left + (offset / max(1, plan.simulation_years - 1)) * usable_width
            scene.addLine(x, top - 7, x, height - 25, QPen(QColor("#d7dce2"), 1))
            year_text = scene.addText(str(plan.start_year + offset))
            year_text.setScale(0.8)
            year_text.setPos(x - 18, top - 30)

        events = build_life_events(plan)
        lane_map = {
            "family": "family",
            "work": "assets",
            "housing": "housing",
            "car": "car",
            "travel": "assets",
            "other": "assets",
        }
        for item in plan.cashflow_events:
            flow_label = "収入" if item.flow_type == "income" else "支出"
            events.append(
                LifeEvent(
                    item.offset,
                    lane_map.get(item.category, "assets"),
                    item.label,
                    f"{flow_label} {item.amount / 10_000:,.0f}万円",
                )
            )

        car_names = [car.name for car in plan.cars if car.enabled]
        for result in results:
            for text in result.events:
                if "住み替え" in text or "家を売却" in text:
                    events.append(LifeEvent(result.offset, "housing", text))
                elif any(name and name in text for name in car_names):
                    events.append(LifeEvent(result.offset, "car", text))
                elif "NISA 1/" in text:
                    events.append(LifeEvent(result.offset, "assets", text))
            if result.warnings:
                events.append(
                    LifeEvent(
                        result.offset,
                        "assets",
                        "資金注意",
                        " / ".join(result.warnings),
                    )
                )
        periods = build_life_periods(plan)
        lane_index = {key: index for index, (key, _, _) in enumerate(self.LANES)}
        lane_colors = {key: color for key, _, color in self.LANES}

        for key, label, color in self.LANES:
            y = top + lane_index[key] * lane_height
            scene.addRect(0, y, width, lane_height - 4, QPen(Qt.NoPen), QColor("#ffffff"))
            label_item = scene.addText(label)
            label_item.setFont(QFont("", 10, QFont.Bold))
            label_item.setDefaultTextColor(QColor(color))
            label_item.setPos(12, y + 20)
            scene.addLine(left, y + 34, width - right, y + 34, QPen(QColor("#dfe3e8"), 2))

        for period in periods:
            lane = period.owner if period.owner in ("husband", "wife") else period.category
            if lane not in lane_index:
                continue
            y = top + lane_index[lane] * lane_height + 16
            x1 = left + (period.start_offset / max(1, plan.simulation_years - 1)) * usable_width
            x2 = left + (period.end_offset / max(1, plan.simulation_years - 1)) * usable_width
            color = QColor(lane_colors[lane])
            fill = QColor(color)
            fill.setAlpha(65)
            scene.addRect(x1, y, max(5, x2 - x1), 18, QPen(color, 1), fill)

        grouped: dict[tuple[str, int], list[LifeEvent]] = defaultdict(list)
        for event in events:
            if 0 <= event.offset < plan.simulation_years:
                key = (self._lane(event), event.offset)
                if not any(item.title == event.title for item in grouped[key]):
                    grouped[key].append(event)

        for (lane, offset), items in grouped.items():
            if lane not in lane_index:
                continue
            x = left + (offset / max(1, plan.simulation_years - 1)) * usable_width
            y = top + lane_index[lane] * lane_height + 28
            color = QColor(lane_colors[lane])
            marker = scene.addEllipse(
                x - 7,
                y - 7,
                14,
                14,
                QPen(QColor("#ffffff"), 2),
                color,
            )
            marker.setData(0, offset)
            marker.setData(1, items)
            marker.setToolTip("\n".join(event.title for event in items))
            marker.setZValue(10)
            if len(items) > 1:
                count = scene.addText(str(len(items)))
                count.setDefaultTextColor(color)
                count.setFont(QFont("", 8, QFont.Bold))
                count.setPos(x + 5, y - 17)
                count.setData(0, offset)
                count.setData(1, items)
                count.setZValue(11)

        hint = scene.addText("● をクリックすると、その年のイベントと収支を右側に表示します")
        hint.setDefaultTextColor(QColor("#64748b"))
        hint.setPos(left, height - 23)

        self.setScene(scene)
        self._ready = True
        self._fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        if self._ready and self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is not None and item.data(0) is not None:
            self.eventSelected.emit(int(item.data(0)), item.data(1))
            return
        super().mousePressEvent(event)
