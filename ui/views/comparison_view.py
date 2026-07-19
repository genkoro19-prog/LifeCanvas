from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt, Slot
import ui.views.dashboard  # 日本語フォント設定の副作用インポート
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import copy

class ComparisonView(QWidget):
    """
    シナリオ比較ビュー。
    現在のアクティブな複数シナリオの資産推移を同一の折れ線グラフに描画し、効果を検証します。
    """
    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        self.scenarios = {} # 保存されているシナリオ名: シミュレーション結果
        self._init_ui()
        self.vm.simulation_updated.connect(self.on_current_simulation_updated)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("⚖️ シナリオ比較分析", self)
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        # 上部アクション領域
        top_layout = QHBoxLayout()
        self.btn_save_scenario = QPushButton("現在の設定を比較対象として追加", self)
        self.btn_save_scenario.clicked.connect(self._save_current_as_scenario)
        
        self.btn_clear_scenarios = QPushButton("比較リストをクリア", self)
        self.btn_clear_scenarios.setObjectName("SecondaryButton")
        self.btn_clear_scenarios.clicked.connect(self._clear_scenarios)
        
        top_layout.addWidget(self.btn_save_scenario)
        top_layout.addWidget(self.btn_clear_scenarios)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # スプリッターでテーブルとグラフを配置
        content_layout = QHBoxLayout()
        
        # 保存シナリオテーブル
        self.table_scenarios = QTableWidget(0, 2, self)
        self.table_scenarios.setHorizontalHeaderLabels(["シナリオ名", "最終純資産 (万円)"])
        self.table_scenarios.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_scenarios.setMinimumWidth(250)
        self.table_scenarios.setMaximumWidth(350)
        content_layout.addWidget(self.table_scenarios)

        # 比較用グラフ
        self.fig = Figure(facecolor="#ffffff")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        content_layout.addWidget(self.canvas)

        layout.addLayout(content_layout)

    def _save_current_as_scenario(self):
        """現在のアクティブな設定とその計算結果を別名保存"""
        # シナリオ名を入力（簡易化して連番またはダイアログなどにするが、ここでは連番）
        num_scenarios = len(self.scenarios) + 1
        name = f"プラン {num_scenarios}"
        if num_scenarios == 1:
            name = "オリジナル (プラン A)"
        elif num_scenarios == 2:
            name = "変更案 (プラン B)"
        elif num_scenarios == 3:
            name = "最適化案 (プラン C)"

        # 現在のシミュレーション結果を記録
        self.scenarios[name] = copy.deepcopy(self.vm.sim_results)
        self._update_ui_and_chart()

    def _clear_scenarios(self):
        self.scenarios.clear()
        self._update_ui_and_chart()

    @Slot(list)
    def on_current_simulation_updated(self, results):
        # 現在実行中のリアルタイム結果も「現在編集中のプラン」として一時重ね合わせに含めます
        self.current_results = results
        self.draw_chart()

    def _update_ui_and_chart(self):
        # テーブル更新
        self.table_scenarios.setRowCount(0)
        for name, results in self.scenarios.items():
            row = self.table_scenarios.rowCount()
            self.table_scenarios.insertRow(row)
            self.table_scenarios.setItem(row, 0, QTableWidgetItem(name))
            
            # 最後の年の純資産
            final_net_worth = results[-1]["net_worth"] if results else 0
            self.table_scenarios.setItem(row, 1, QTableWidgetItem(f"{final_net_worth / 10000.0:.0f}"))
            
        self.draw_chart()

    def draw_chart(self):
        self.ax.clear()
        
        # 1. 保存済みシナリオのプロット
        for name, results in self.scenarios.items():
            years = [r["year"] for r in results]
            net_worths = [(r["cash_balance"] + r["investment_balance"]) / 10000.0 for r in results]
            self.ax.plot(years, net_worths, label=name, marker="o", markersize=3, linewidth=2)

        # 2. 現在進行形のシミュレーション値のプロット (点線)
        if hasattr(self, "current_results") and self.current_results:
            years = [r["year"] for r in self.current_results]
            net_worths = [(r["cash_balance"] + r["investment_balance"]) / 10000.0 for r in self.current_results]
            self.ax.plot(years, net_worths, label="現在編集中の案 (リアルタイム)", linestyle="--", color="#6b6b6b")

        self.ax.set_xlabel("シミュレーション経過年数")
        self.ax.set_ylabel("金融資産高 (万円)")
        self.ax.grid(True, linestyle=":", alpha=0.5)
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()
