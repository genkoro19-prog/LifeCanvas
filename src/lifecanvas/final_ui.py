from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .car_editor import CarEditor
from .cashflow_event_editor import CashFlowEventEditor
from .child_editor import ChildEditor
from .complete_ui import LifeCanvasWindow as CompleteLifeCanvasWindow
from .engine import SimulationEngine
from .family import apply_work_stages_for_child, infer_work_reference_child
from .housing_editor import HousingEditor
from .insights import analyze_plan, dominant_expense
from .models import CarPlan, IncomePeriod
from .modern_theme import MODERN_STYLESHEET
from .pdf_report import export_pdf
from .plotting import configure_japanese_matplotlib
from .sample import build_genki_family_plan
from .ui import MetricCard, man


class LifeCanvasWindow(CompleteLifeCanvasWindow):
    """Finished desktop edition: simple inputs, local analysis, PDF, and modern UI."""

    def __init__(self):
        self._modern_ready = False
        super().__init__()
        self.setWindowTitle("LifeCanvas — 人生設計シミュレーター")
        self.resize(1480, 940)
        self.setMinimumSize(1120, 760)
        self.setStyleSheet(MODERN_STYLESHEET)
        self.tabs.setDocumentMode(True)
        tab_names = ["結果", "入力", "ライフイベント", "年別", "比較"]
        for index, label in enumerate(tab_names):
            if index < self.tabs.count():
                self.tabs.setTabText(index, label)

        for button in self.findChildren(QPushButton):
            if button.text() == "再計算":
                button.setText("未来を更新")
                button.setObjectName("primaryButton")
                self.recalc_button = button
                break

        self._install_completion_actions()
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.setInterval(650)
        self._auto_timer.timeout.connect(self.recalculate)
        self._connect_auto_refresh()
        self._modern_ready = True
        self._set_refresh_status(False)

    def _install_completion_actions(self) -> None:
        root_layout = self.centralWidget().layout()
        actions = QHBoxLayout()
        guide = QLabel("大きな前提だけ入力して、結果を見ながら調整します。")
        guide.setObjectName("sectionNote")
        self.refresh_status = QLabel("最新")
        self.refresh_status.setObjectName("statusFresh")
        pdf_button = QPushButton("PDFレポート")
        pdf_button.setObjectName("pdfButton")
        reset_button = QPushButton("サンプルへ戻す")
        pdf_button.clicked.connect(self.export_report)
        reset_button.clicked.connect(self.reset_to_sample)
        actions.addWidget(guide)
        actions.addStretch()
        actions.addWidget(self.refresh_status)
        actions.addWidget(reset_button)
        actions.addWidget(pdf_button)
        root_layout.insertLayout(2, actions)

    def _connect_auto_refresh(self) -> None:
        for edit in self.findChildren(QLineEdit):
            edit.editingFinished.connect(self._schedule_refresh)
        for combo in self.findChildren(QComboBox):
            combo.currentIndexChanged.connect(self._schedule_refresh)
        self.housing_editor.changed.connect(self._schedule_refresh)
        self.car_editor.changed.connect(self._schedule_refresh)

    def _schedule_refresh(self, *_args) -> None:
        if not self._modern_ready:
            return
        self._set_refresh_status(True)
        self._auto_timer.start()

    def _set_refresh_status(self, dirty: bool) -> None:
        if not hasattr(self, "refresh_status"):
            return
        self.refresh_status.setText("未反映の変更" if dirty else "最新")
        self.refresh_status.setObjectName("statusDirty" if dirty else "statusFresh")
        self.refresh_status.style().unpolish(self.refresh_status)
        self.refresh_status.style().polish(self.refresh_status)

    def recalculate(self) -> None:
        super().recalculate()
        if getattr(self, "results", None):
            self._set_refresh_status(False)

    def reset_to_sample(self) -> None:
        answer = QMessageBox.question(
            self,
            "サンプルへ戻す",
            "現在の入力内容をサンプルプランへ戻しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.plan = build_genki_family_plan()
        self.current_file = None
        self._sync_inputs_from_plan()
        self.recalculate()

    def export_report(self) -> None:
        if not self.results:
            self.recalculate()
        default_name = f"{self.plan.name or 'LifeCanvas'}_レポート.pdf"
        documents = Path.home() / "Documents"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "PDFレポートを保存",
            str(documents / default_name),
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            target = export_pdf(self.plan, self.results, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "PDFを保存できませんでした", str(exc))
            return
        QMessageBox.information(self, "PDFを保存しました", str(target))

    def _build_dashboard(self) -> QWidget:
        configure_japanese_matplotlib()
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        cards = QGridLayout()
        cards.setSpacing(10)
        self.card_retirement = MetricCard("夫の定年時純資産")
        self.card_cash = MetricCard("最低現預金")
        self.card_shortage = MetricCard("資金ショート")
        self.card_move = MetricCard("住み替え")
        self.card_outlook = MetricCard("将来判定")
        self.card_final = MetricCard("最終年の純資産")
        card_items = [
            self.card_outlook,
            self.card_cash,
            self.card_shortage,
            self.card_retirement,
            self.card_move,
            self.card_final,
        ]
        for index, card in enumerate(card_items):
            cards.addWidget(card, index // 3, index % 3)
        layout.addLayout(cards)

        self.figure = Figure(figsize=(10, 4.3))
        self.figure.patch.set_facecolor("#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)

        self.dashboard_summary = QTextEdit()
        self.dashboard_summary.setReadOnly(True)
        self.dashboard_summary.setMaximumHeight(142)
        layout.addWidget(self.dashboard_summary)

        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMaximumHeight(105)
        layout.addWidget(self.dashboard_warnings)
        return page

    def _build_setup(self) -> QWidget:
        scroll = super()._build_setup()
        layout = scroll.widget().layout()

        legacy_family = self.first_child_offset.parentWidget()
        legacy_family.hide()
        legacy_housing = self.loan_amount.parentWidget()
        legacy_housing.hide()

        insert_at = layout.indexOf(self.husband_income_editor)
        self.child_editor = ChildEditor(self.plan)
        self.housing_editor = HousingEditor(self.plan)
        self.car_editor = CarEditor(self.plan)
        self.cashflow_event_editor = CashFlowEventEditor(self.plan)
        self.cashflow_event_editor.setCheckable(True)
        self.cashflow_event_editor.setChecked(False)

        for offset, widget in enumerate(
            [
                self.child_editor,
                self.housing_editor,
                self.car_editor,
                self.cashflow_event_editor,
            ]
        ):
            layout.insertWidget(max(0, insert_at + offset), widget)
        self._update_work_labels()
        return scroll

    def _configure_annual_table(self) -> None:
        headers = [
            "年",
            "夫/妻",
            "夫年収",
            "妻年収",
            "年金",
            "退職金等",
            "イベント収入",
            "収入合計",
            "生活費",
            "住宅",
            "教育",
            "車",
            "イベント支出",
            "生活収支",
            "現預金",
            "投資",
            "純資産",
        ]
        self.year_table.setColumnCount(len(headers))
        self.year_table.setHorizontalHeaderLabels(headers)
        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.year_table.setAlternatingRowColors(True)

    def _update_work_labels(self) -> None:
        work_form = self.w_nursery.parentWidget().layout()
        labels = [
            (self.w_before, "妻・出産前"),
            (self.w_nursery, "妻・基準の子が保育園期"),
            (self.w_elementary, "妻・基準の子が小学生期"),
            (self.w_junior, "妻・基準の子が中学生以降"),
        ]
        for field, text in labels:
            label = work_form.labelForField(field) if hasattr(work_form, "labelForField") else None
            if label:
                label.setText(text)

    def _apply_inputs(self) -> None:
        start_month = self.start_month.int_value()
        if not 1 <= start_month <= 12:
            raise ValueError("開始月は1〜12で入力してください。")

        self.plan.start_month = start_month
        self.plan.initial_cash = self.initial_cash.value()
        self.plan.living_cost.monthly_amount = self.living_monthly.value()
        self.plan.husband.retirement_age = self.h_retire.int_value()
        self.plan.husband.pension_start_age = self.h_pension_age.int_value()
        self.plan.husband.annual_pension = self.h_pension.value()
        self.plan.wife.retirement_age = self.w_retire.int_value()
        self.plan.wife.pension_start_age = self.w_pension_age.int_value()
        self.plan.wife.annual_pension = self.w_pension.value()

        self.plan.children = self.child_editor.children()
        apply_work_stages_for_child(self.plan, self.child_editor.reference_child_name())
        self.plan.cashflow_events = self.cashflow_event_editor.events()
        self.housing_editor.apply_to(self.plan)
        self.plan.cars = self.car_editor.cars()
        self.plan.car = (
            self.plan.cars[0].model_copy(deep=True)
            if self.plan.cars
            else CarPlan(enabled=False, replacement_cycle_years=None)
        )

        self.plan.income_periods = [
            period for period in self.plan.income_periods if period.owner != "husband"
        ] + self.husband_income_editor.periods()
        for period in self.plan.income_periods:
            if (
                period.owner == "husband"
                and "継続雇用" in period.label
                and period.start_age == self.plan.husband.retirement_age
            ):
                period.end_age = self.plan.husband.pension_start_age

        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband" and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.plan.husband.annual_gross_income = current_period.annual_gross_income if current_period else 0

        stages = {stage.key: stage for stage in self.plan.wife_work_stages}
        stages["full_time"].annual_gross_income = self.w_before.value()
        stages["nursery"].annual_gross_income = self.w_nursery.value()
        stages["elementary"].annual_gross_income = self.w_elementary.value()
        stages["junior_high"].annual_gross_income = self.w_junior.value()

        self.plan.nisa_accounts[0].monthly_contribution = self.h_nisa_before.value()
        self.plan.nisa_accounts[0].contribution_changes[5] = self.h_nisa_after.value()
        self.plan.nisa_accounts[1].monthly_contribution = self.w_nisa.value()

        self._upsert_retirement_income(
            "husband",
            "夫の退職金",
            self.plan.husband.retirement_age,
            self.h_retirement_lump.value(),
        )
        self._upsert_retirement_income(
            "wife",
            "妻の退職金",
            self.plan.wife.retirement_age,
            self.w_retirement_lump.value(),
        )
        if hasattr(self, "plan_name_edit"):
            self.plan.name = self.plan_name_edit.text().strip() or "LifeCanvas Plan"

    def _sync_inputs_from_plan(self) -> None:
        self.plan_name_edit.setText(self.plan.name)
        self.start_month.set_value(self.plan.start_month)
        self.initial_cash.set_value(self.plan.initial_cash)
        self.living_monthly.set_value(self.plan.living_cost.monthly_amount)
        self.child_editor.load(self.plan)
        self.housing_editor.load(self.plan)
        self.car_editor.load(self.plan)
        self.cashflow_event_editor.load(self.plan)
        inferred = infer_work_reference_child(self.plan)
        if inferred:
            index = self.child_editor.reference_child.findText(inferred)
            if index >= 0:
                self.child_editor.reference_child.setCurrentIndex(index)

        self.husband_income_editor.load(self.plan)
        current_period = next(
            (
                period
                for period in self.plan.income_periods
                if period.owner == "husband" and period.active(self.plan.husband.current_age)
            ),
            None,
        )
        self.h_income.set_value(
            current_period.annual_gross_income if current_period else self.plan.husband.annual_gross_income
        )
        self.h_retire.set_value(self.plan.husband.retirement_age)
        self.h_retirement_lump.set_value(self._retirement_amount("husband"))
        self.h_pension_age.set_value(self.plan.husband.pension_start_age)
        self.h_pension.set_value(self.plan.husband.annual_pension)
        self.w_retire.set_value(self.plan.wife.retirement_age)
        self.w_retirement_lump.set_value(self._retirement_amount("wife"))
        self.w_pension_age.set_value(self.plan.wife.pension_start_age)
        self.w_pension.set_value(self.plan.wife.annual_pension)

        stages = {stage.key: stage for stage in self.plan.wife_work_stages}
        self.w_before.set_value(stages["full_time"].annual_gross_income)
        self.w_nursery.set_value(stages["nursery"].annual_gross_income)
        self.w_elementary.set_value(stages["elementary"].annual_gross_income)
        self.w_junior.set_value(stages["junior_high"].annual_gross_income)
        self.h_nisa_before.set_value(self.plan.nisa_accounts[0].monthly_contribution)
        self.h_nisa_after.set_value(self.plan.nisa_accounts[0].contribution_changes.get(5, 0))
        self.w_nisa.set_value(self.plan.nisa_accounts[1].monthly_contribution)
        self._update_work_labels()

    def _refresh_dashboard(self) -> None:
        configure_japanese_matplotlib()
        retirement = next(
            (row for row in self.results if row.husband_age == self.plan.husband.retirement_age),
            self.results[-1],
        )
        minimum_cash = min(self.results, key=lambda row: row.cash_end)
        shortage = [
            row
            for row in self.results
            if any("資金ショート" in warning for warning in row.warnings)
        ]
        insight = analyze_plan(self.plan, self.results)

        self.card_retirement.value.setText(man(retirement.net_worth))
        self.card_retirement.note.setText(f"{retirement.calendar_year}年")
        self.card_cash.value.setText(man(minimum_cash.cash_end))
        self.card_cash.note.setText(f"最低年: {minimum_cash.calendar_year}年")
        self.card_shortage.value.setText("あり" if shortage else "なし")
        self.card_shortage.note.setText(
            f"{shortage[0].calendar_year}年から" if shortage else "現在の前提では発生しません"
        )
        if self.plan.housing.move_mode == "none" or self.plan.housing.move_offset is None:
            self.card_move.value.setText("予定なし")
            self.card_move.note.setText("現在の家に住み続ける")
        else:
            move_year = self.plan.start_year + self.plan.housing.move_offset
            label = "売却して移る" if self.plan.housing.move_mode == "sell" else "残して移る"
            self.card_move.value.setText(label)
            self.card_move.note.setText(f"{move_year}年")
        self.card_outlook.value.setText(insight.status)
        self.card_outlook.note.setText(insight.status_note)
        self.card_final.value.setText(man(insight.final_net_worth))
        self.card_final.note.setText(f"{self.results[-1].calendar_year}年")

        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_facecolor("#ffffff")
        years = [row.calendar_year for row in self.results]
        axis.plot(years, [row.net_worth / 10_000 for row in self.results], label="純資産", linewidth=2.4)
        axis.plot(years, [row.cash_end / 10_000 for row in self.results], label="現預金", linewidth=1.8)
        axis.plot(
            years,
            [row.investments_market_value / 10_000 for row in self.results],
            label="投資資産",
            linewidth=1.8,
        )
        axis.plot(
            years,
            [-row.mortgage_balance / 10_000 for row in self.results],
            label="住宅ローン（負債）",
            linestyle="--",
            linewidth=1.5,
        )
        axis.axhline(0, linewidth=1, alpha=0.4)
        axis.set_title("資産・負債の推移")
        axis.set_xlabel("年")
        axis.set_ylabel("万円")
        axis.grid(True, alpha=0.2)
        axis.legend(ncol=4, loc="best", frameon=False)
        self.figure.tight_layout()
        self.canvas.draw()

        difficult_lines = [
            f"・{row.calendar_year}年　収支 {man(row.living_surplus)}　主な支出: {dominant_expense(row)}"
            for row in insight.difficult_years
        ]
        self.dashboard_summary.setPlainText(
            "\n".join(
                [
                    f"判定: {insight.status} — {insight.status_note}",
                    f"老後期間の最低現預金: {man(insight.retirement_min_cash)}",
                    "",
                    "収支が厳しい年:",
                    *difficult_lines,
                ]
            )
        )

        self.dashboard_warnings.clear()
        for result in self.results:
            for warning in result.warnings:
                self.dashboard_warnings.addItem(f"{result.calendar_year}年: {warning}")
        if self.dashboard_warnings.count() == 0:
            self.dashboard_warnings.addItem("重大な資金ショートはありません。")

    def _refresh_table(self) -> None:
        self.year_table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            values = [
                str(result.calendar_year),
                f"{result.husband_age}/{result.wife_age}",
                man(result.husband_gross),
                man(result.wife_gross),
                man(result.pension_income),
                man(result.one_time_income),
                man(result.life_event_income),
                man(result.total_income),
                man(result.core_living_cost),
                man(result.housing_cost),
                man(result.education_cost),
                man(result.car_cost),
                man(result.life_event_expense),
                man(result.living_surplus),
                man(result.cash_end),
                man(result.investments_market_value),
                man(result.net_worth),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.year_table.setItem(row, column, item)
        self.year_table.selectRow(0)

    def _set_year_detail(self, widget: QTextEdit, offset: int, events: list) -> None:
        result = self.results[offset]
        children = "、".join(
            f"{name}{age}歳" for name, age in result.children_ages.items()
        ) or "なし"
        event_lines = [
            f"・{event.title}: {event.detail}" for event in events
        ] or [f"・{event}" for event in result.events] or ["・なし"]
        lines = [
            f"{result.calendar_year}年（夫{result.husband_age}歳・妻{result.wife_age}歳）",
            f"子ども: {children}",
            "",
            "イベント:",
            *event_lines,
            "",
            f"夫年収 {man(result.husband_gross)} / 妻年収 {man(result.wife_gross)}",
            f"給与手取り {man(result.salary_net)} / 年金 {man(result.pension_income)}",
            f"退職金等 {man(result.one_time_income)} / イベント収入 {man(result.life_event_income)}",
            f"給付 {man(result.benefits)} / 家賃 {man(result.rental_income)}",
            f"収入合計 {man(result.total_income)}",
            "",
            f"生活費 {man(result.core_living_cost)} / 住宅 {man(result.housing_cost)}",
            f"教育 {man(result.education_cost)} / 車 {man(result.car_cost)}",
            f"イベント支出 {man(result.life_event_expense)}",
            f"生活収支 {man(result.living_surplus)}",
            f"現預金 {man(result.cash_end)} / 純資産 {man(result.net_worth)}",
        ]
        if result.warnings:
            lines.extend(["", "注意:", *[f"・{warning}" for warning in result.warnings]])
        widget.setPlainText("\n".join(lines))

    def _refresh_compare(self) -> None:
        scenarios = []
        definitions = [
            ("現在の計画", "current"),
            ("住み替えなし", "no_move"),
            ("車なし", "no_car"),
            ("住宅ローン金利固定", "fixed_rate"),
        ]
        for label, scenario in definitions:
            plan = deepcopy(self.plan)
            if scenario == "no_move":
                plan.housing.move_mode = "none"
                plan.housing.move_offset = None
            elif scenario == "no_car":
                plan.cars = []
                plan.car.enabled = False
            elif scenario == "fixed_rate":
                plan.housing.mortgage.max_rate_percent = plan.housing.mortgage.initial_rate_percent
                plan.housing.mortgage.annual_rate_step_percent = 0
            results = SimulationEngine(plan).run()
            retirement = next(
                (row for row in results if row.husband_age == plan.husband.retirement_age),
                results[-1],
            )
            scenarios.append(
                (
                    label,
                    retirement.net_worth,
                    min(row.cash_end for row in results),
                    sum(row.nisa_sold for row in results),
                    results[-1].net_worth,
                    sum(bool(row.warnings) for row in results),
                )
            )
        self.compare_table.setRowCount(len(scenarios))
        for row, data in enumerate(scenarios):
            for column, value in enumerate(data):
                text = str(value) if column in (0, 5) else man(value)
                self.compare_table.setItem(row, column, QTableWidgetItem(text))


def run_app() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
