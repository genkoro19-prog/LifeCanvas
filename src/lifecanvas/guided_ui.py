from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from .guided_input import GuidedInputPage
from .plan_review import check_plan, impact_ranking, scenario_summaries
from .revision_ui import LifeCanvasWindow as BaseLifeCanvasWindow
from .ui import man


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """LifeCanvas with a guided baseline flow before the detailed editor."""

    def __init__(self):
        self.guided_input: GuidedInputPage | None = None
        super().__init__()

        self.guided_input = GuidedInputPage(self.plan)
        self.guided_input.applyRequested.connect(self._apply_guided_input)
        self.tabs.insertTab(1, self.guided_input, "かんたん入力")
        labels = [
            "結果",
            "かんたん入力",
            "詳細設定",
            "ライフイベント",
            "年別",
            "比較",
        ]
        for index, label in enumerate(labels):
            if index < self.tabs.count():
                self.tabs.setTabText(index, label)
        self.tabs.setCurrentIndex(1)

    def _apply_guided_input(self) -> None:
        if self.guided_input is None:
            return
        try:
            self.guided_input.apply_to(self.plan)
            self._sync_inputs_from_plan()
            # The legacy simple field always stores a five-year amount. Keep it flat
            # after guided input instead of creating a hidden stop or increase.
            self.h_nisa_after.set_value(self.h_nisa_before.value())
            self.recalculate()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "入力内容を確認してください", str(exc))
            return
        self.tabs.setCurrentIndex(0)

    def _sync_inputs_from_plan(self) -> None:
        super()._sync_inputs_from_plan()
        if self.guided_input is not None:
            self.guided_input.load(self.plan)

    def _refresh_dashboard(self) -> None:
        super()._refresh_dashboard()
        if not getattr(self, "results", None):
            return

        checks = check_plan(self.plan)
        impacts = impact_ranking(self.plan, self.results)
        additions: list[str] = []

        additions.append("【入力内容のチェック】")
        if checks:
            for check in checks[:5]:
                additions.append(f"・{check.title}：{check.suggestion}")
        else:
            additions.append("・大きな矛盾や二重計上は見つかりませんでした。")

        additions.append("")
        additions.append("【将来資産へ影響が大きい項目】")
        if impacts:
            for index, item in enumerate(impacts, start=1):
                additions.append(
                    f"{index}. {item.label}　約{item.improvement/10_000:,.0f}万円"
                    f"（{item.note}）"
                )
        else:
            additions.append("・比較できる大きな任意支出はありません。")

        current = self.dashboard_summary.toPlainText().rstrip()
        self.dashboard_summary.setPlainText(current + "\n\n" + "\n".join(additions))
        self.dashboard_summary.setMinimumHeight(315)
        self.dashboard_summary.setMaximumHeight(430)

    def _refresh_compare(self) -> None:
        summaries = scenario_summaries(self.plan)
        headers = [
            "シナリオ",
            "夫の定年時純資産",
            "最低手元現金",
            "最終純資産",
            "警告年数",
            "前提",
        ]
        self.compare_table.setColumnCount(len(headers))
        self.compare_table.setHorizontalHeaderLabels(headers)
        self.compare_table.setRowCount(len(summaries))
        for row, summary in enumerate(summaries):
            values = [
                summary.label,
                man(summary.retirement_net_worth),
                man(summary.minimum_cash),
                man(summary.final_net_worth),
                str(summary.warning_years),
                summary.note,
            ]
            for column, value in enumerate(values):
                self.compare_table.setItem(row, column, QTableWidgetItem(value))


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
