from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import complete_ui as complete_ui_module
from . import final_ui as final_ui_module
from .age_income_editor import AgeIncomeEditor
from .housing_editor_v2 import HousingEditor
from .ito_sample import build_ito_family_plan
from .pdf_report_v2 import export_pdf
from .plotting import configure_japanese_matplotlib
from .rent_engine import SimulationEngine, is_rental_move
from .sample import build_genki_family_plan
from .ui import MetricCard

# Keep all inherited calculation and export paths on the revised implementations.
complete_ui_module.SimulationEngine = SimulationEngine
final_ui_module.SimulationEngine = SimulationEngine
final_ui_module.HousingEditor = HousingEditor
final_ui_module.export_pdf = export_pdf

from .final_ui import LifeCanvasWindow as BaseLifeCanvasWindow


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """Desktop UI with fully synchronized family, income, and result views."""

    def _install_completion_actions(self) -> None:
        root_layout = self.centralWidget().layout()
        actions = QHBoxLayout()
        guide = QLabel("大きな前提だけ入力して、結果を見ながら調整します。")
        guide.setObjectName("sectionNote")
        self.refresh_status = QLabel("最新")
        self.refresh_status.setObjectName("statusFresh")

        self.sample_combo = QComboBox()
        self.sample_combo.setObjectName("sampleSelector")
        self.sample_combo.addItem("大原家サンプル", "genki")
        self.sample_combo.addItem("伊藤家サンプル（仮設定）", "ito")
        load_sample_button = QPushButton("サンプルを読み込む")
        load_sample_button.clicked.connect(self.load_selected_sample)

        pdf_button = QPushButton("PDFレポート")
        pdf_button.setObjectName("pdfButton")
        pdf_button.clicked.connect(self.export_report)

        actions.addWidget(guide)
        actions.addStretch()
        actions.addWidget(self.refresh_status)
        actions.addWidget(self.sample_combo)
        actions.addWidget(load_sample_button)
        actions.addWidget(pdf_button)
        root_layout.insertLayout(2, actions)

    def _build_dashboard(self) -> QWidget:
        """Build a vertically scrollable result page with no floating overlays."""

        configure_japanese_matplotlib()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("resultScroll")

        page = QWidget()
        page.setObjectName("resultContent")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 12, 14, 18)

        cards = QGridLayout()
        cards.setHorizontalSpacing(10)
        cards.setVerticalSpacing(10)
        self.card_retirement = MetricCard("夫の定年時純資産")
        self.card_cash = MetricCard("最低現預金")
        self.card_shortage = MetricCard("資金ショート")
        self.card_move = MetricCard("将来の住まい")
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
            row, column = divmod(index, 3)
            card.setMinimumWidth(0)
            cards.addWidget(card, row, column)
            cards.setColumnStretch(column, 1)
        layout.addLayout(cards)

        graph_title = QLabel("資産・負債の推移")
        graph_title.setObjectName("sectionTitle")
        layout.addWidget(graph_title)

        self.figure = Figure(figsize=(11.5, 5.6))
        self.figure.patch.set_facecolor("#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(430)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.canvas)

        result_label = QLabel("判定と確認ポイント")
        result_label.setObjectName("sectionTitle")
        layout.addWidget(result_label)
        self.dashboard_summary = QTextEdit()
        self.dashboard_summary.setReadOnly(True)
        self.dashboard_summary.setMinimumHeight(165)
        self.dashboard_summary.setMaximumHeight(190)
        layout.addWidget(self.dashboard_summary)

        warning_label = QLabel("年ごとの注意")
        warning_label.setObjectName("sectionTitle")
        layout.addWidget(warning_label)
        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMinimumHeight(145)
        self.dashboard_warnings.setMaximumHeight(185)
        layout.addWidget(self.dashboard_warnings)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def _build_setup(self) -> QWidget:
        scroll = super()._build_setup()
        layout = scroll.widget().layout()

        # Replace the old husband-only period editor with matching editors for both spouses.
        old_index = layout.indexOf(self.husband_income_editor)
        self.husband_income_editor.hide()
        self.husband_age_income = AgeIncomeEditor(
            self.plan,
            owner="husband",
            title="夫の収入計画（年齢ごと）",
        )
        self.wife_age_income = AgeIncomeEditor(
            self.plan,
            owner="wife",
            title="妻の収入計画（年齢ごと）",
        )
        layout.insertWidget(max(0, old_index), self.husband_age_income)
        layout.insertWidget(max(0, old_index + 1), self.wife_age_income)

        # Hide the obsolete child-linked wife salary fields while retaining retirement inputs.
        work_group = self.w_before.parentWidget()
        if hasattr(work_group, "setTitle"):
            work_group.setTitle("定年の基本設定")
        work_form = work_group.layout()
        for field in (self.w_before, self.w_nursery, self.w_elementary, self.w_junior):
            label = work_form.labelForField(field) if hasattr(work_form, "labelForField") else None
            if label:
                label.hide()
            field.hide()
        return scroll

    def _connect_auto_refresh(self) -> None:
        super()._connect_auto_refresh()
        self.child_editor.changed.connect(self._schedule_refresh)
        self.husband_age_income.changed.connect(self._schedule_refresh)
        self.wife_age_income.changed.connect(self._schedule_refresh)

    def _apply_inputs(self) -> None:
        super()._apply_inputs()
        other_periods = [
            period
            for period in self.plan.income_periods
            if period.owner not in ("husband", "wife")
        ]
        husband_periods = self.husband_age_income.periods(self.plan)
        wife_periods = self.wife_age_income.periods(self.plan)
        self.plan.income_periods = [*other_periods, *husband_periods, *wife_periods]

        husband_current = next(
            (
                period
                for period in husband_periods
                if period.active(self.plan.husband.current_age)
            ),
            None,
        )
        wife_current = next(
            (
                period
                for period in wife_periods
                if period.active(self.plan.wife.current_age)
            ),
            None,
        )
        self.plan.husband.annual_gross_income = (
            husband_current.annual_gross_income if husband_current else 0
        )
        self.plan.wife.annual_gross_income = (
            wife_current.annual_gross_income if wife_current else 0
        )

    def _sync_inputs_from_plan(self) -> None:
        super()._sync_inputs_from_plan()
        if hasattr(self, "husband_age_income"):
            self.husband_age_income.load(self.plan)
        if hasattr(self, "wife_age_income"):
            self.wife_age_income.load(self.plan)

    def _selected_sample(self):
        if self.sample_combo.currentData() == "ito":
            return build_ito_family_plan()
        return build_genki_family_plan()

    def load_selected_sample(self) -> None:
        label = self.sample_combo.currentText()
        answer = QMessageBox.question(
            self,
            "サンプルを読み込む",
            f"現在の入力内容を「{label}」へ置き換えますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.plan = self._selected_sample()
        self.current_file = None
        self._sync_inputs_from_plan()
        self.recalculate()

    def reset_to_sample(self) -> None:
        self.load_selected_sample()

    def _refresh_dashboard(self) -> None:
        super()._refresh_dashboard()
        if is_rental_move(self.plan):
            move_year = self.plan.start_year + (self.plan.housing.move_offset or 0)
            self.card_move.value.setText("賃貸へ移る")
            self.card_move.note.setText(f"{move_year}年・月額家賃を反映")

        if self.figure.axes:
            axis = self.figure.axes[0]
            legend = axis.get_legend()
            if legend:
                legend.remove()
            axis.legend(
                ncol=2,
                loc="upper left",
                frameon=False,
                fontsize=9,
            )
            axis.margins(x=0.01)
            self.figure.subplots_adjust(left=0.075, right=0.985, bottom=0.14, top=0.88)
            self.canvas.draw_idle()


def run_app() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
