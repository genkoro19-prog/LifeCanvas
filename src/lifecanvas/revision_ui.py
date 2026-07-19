from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import complete_ui as complete_ui_module
from . import final_ui as final_ui_module
from .housing_editor_v2 import HousingEditor
from .ito_sample import build_ito_family_plan
from .plotting import configure_japanese_matplotlib
from .rent_engine import SimulationEngine, is_rental_move
from .sample import build_genki_family_plan
from .ui import MetricCard

# Keep all inherited calculation paths on the rent-aware engine and the new editor.
complete_ui_module.SimulationEngine = SimulationEngine
final_ui_module.SimulationEngine = SimulationEngine
final_ui_module.HousingEditor = HousingEditor

from .final_ui import LifeCanvasWindow as BaseLifeCanvasWindow


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """UI revision with a readable graph, rental housing, and selectable samples."""

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
        configure_japanese_matplotlib()
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 10, 12, 10)

        cards = QGridLayout()
        cards.setHorizontalSpacing(8)
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
            card.setMinimumWidth(0)
            cards.addWidget(card, 0, index)
            cards.setColumnStretch(index, 1)
        layout.addLayout(cards)

        self.figure = Figure(figsize=(11.5, 5.2))
        self.figure.patch.set_facecolor("#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(360)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)

        details = QHBoxLayout()
        details.setSpacing(10)
        self.dashboard_summary = QTextEdit()
        self.dashboard_summary.setReadOnly(True)
        self.dashboard_summary.setMinimumHeight(105)
        self.dashboard_summary.setMaximumHeight(125)
        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMinimumHeight(105)
        self.dashboard_warnings.setMaximumHeight(125)
        details.addWidget(self.dashboard_summary, 3)
        details.addWidget(self.dashboard_warnings, 2)
        layout.addLayout(details)
        layout.setStretch(1, 1)
        return page

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
