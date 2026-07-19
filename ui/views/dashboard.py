from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QScrollArea, QSplitter, QDoubleSpinBox, QSlider
)
from PySide6.QtCore import Qt, Slot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
import numpy as np
from ui.styles import NOTION_STYLE

# --- matplotlib 日本語フォント設定 ---
import matplotlib.font_manager as fm
import os

_JP_FONT_FOUND = False
for font_name in ["Meiryo", "Yu Gothic", "MS Gothic", "Hiragino Sans"]:
    try:
        fp = fm.findfont(fm.FontProperties(family=font_name), fallback_to_default=False)
        if fp and os.path.exists(fp):
            matplotlib.rcParams["font.family"] = font_name
            _JP_FONT_FOUND = True
            break
    except Exception:
        continue

if not _JP_FONT_FOUND:
    # Windows のシステムフォントを直接指定
    _WIN_FONTS = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
    ]
    for fpath in _WIN_FONTS:
        if os.path.exists(fpath):
            fm.fontManager.addfont(fpath)
            prop = fm.FontProperties(fname=fpath)
            matplotlib.rcParams["font.family"] = prop.get_name()
            _JP_FONT_FOUND = True
            break

matplotlib.rcParams["axes.unicode_minus"] = False


class Dashboard(QWidget):
    """
    ダッシュボード画面。
    サマリーカード、キャッシュフロー・資産推移グラフ、およびリアルタイムパラメータ調整スライダーを表示。
    """
    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        self._init_ui()
        
        # ViewModelのシミュレーション更新シグナルに接続
        self.vm.simulation_updated.connect(self.update_dashboard)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. 画面タイトル
        header = QLabel("📊 ダッシュボード", self)
        header.setObjectName("SectionHeader")
        main_layout.addWidget(header)

        # 2. 上部サマリーカード領域
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(12)
        
        # 4つのカードを用意
        self.card_asset_life = self._create_card("想定資産寿命", "未計算")
        self.card_lifetime_deficit = self._create_card("生涯赤字の有無", "未計算")
        self.card_nisa_total = self._create_card("NISA運用到達額", "未計算")
        self.card_fire_age = self._create_card("FIRE可能判定", "未計算")

        self.cards_layout.addWidget(self.card_asset_life)
        self.cards_layout.addWidget(self.card_lifetime_deficit)
        self.cards_layout.addWidget(self.card_nisa_total)
        self.cards_layout.addWidget(self.card_fire_age)
        main_layout.addLayout(self.cards_layout)

        # 3. グラフ領域 (Matplotlib)
        self.fig = Figure(facecolor="#ffffff", edgecolor="#ffffff", tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax_cashflow = self.fig.add_subplot(111)
        self.ax_asset = self.ax_cashflow.twinx()  # 右Y軸に資産推移
        
        main_layout.addWidget(self.canvas, stretch=3)

        # 4. リアルタイム・パラメータ変更（クイック調整スライダー部）
        control_frame = QFrame(self)
        control_frame.setStyleSheet("background-color: #fafafa; border: 1px solid #e9e9e7; border-radius: 6px; padding: 10px;")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(20)

        # 調整用のスライダーと入力枠
        lbl_info = QLabel("🔄 リアルタイム調整", self)
        lbl_info.setStyleSheet("font-weight: bold; color: #555555;")
        control_layout.addWidget(lbl_info)

        # 夫の年収スライダー
        vbox_husband = QVBoxLayout()
        vbox_husband.addWidget(QLabel("夫の年収 (万円)"))
        self.slider_h_income = QSlider(Qt.Horizontal)
        self.slider_h_income.setRange(200, 1500)
        self.slider_h_income.setValue(620)
        self.slider_h_income.valueChanged.connect(self._on_slider_changed)
        self.lbl_h_income_val = QLabel("620万円")
        self.lbl_h_income_val.setStyleSheet("font-weight: bold;")
        vbox_husband.addWidget(self.slider_h_income)
        vbox_husband.addWidget(self.lbl_h_income_val)
        control_layout.addLayout(vbox_husband)

        # NISA利回りスライダー
        vbox_return = QVBoxLayout()
        vbox_return.addWidget(QLabel("NISA想定利回り (%)"))
        self.slider_return = QSlider(Qt.Horizontal)
        self.slider_return.setRange(0, 100) # 0.0%〜10.0% の 10倍値
        self.slider_return.setValue(40) # デフォルト 4.0%
        self.slider_return.valueChanged.connect(self._on_slider_changed)
        self.lbl_return_val = QLabel("4.0%")
        self.lbl_return_val.setStyleSheet("font-weight: bold;")
        vbox_return.addWidget(self.slider_return)
        vbox_return.addWidget(self.lbl_return_val)
        control_layout.addLayout(vbox_return)

        main_layout.addWidget(control_frame)

    def _create_card(self, title: str, init_val: str) -> QFrame:
        card = QFrame(self)
        card.setObjectName("SummaryCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(4)
        
        lbl_title = QLabel(title, card)
        lbl_title.setObjectName("CardTitle")
        
        lbl_value = QLabel(init_val, card)
        lbl_value.setObjectName("CardValue")
        
        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_value)
        
        # 参照用のプロパティを動的追加
        card.lbl_value = lbl_value
        return card

    def _on_slider_changed(self):
        # スライダーの値を取得
        h_income_val = self.slider_h_income.value()
        ret_val = self.slider_return.value() / 10.0

        # ラベルの更新
        self.lbl_h_income_val.setText(f"{h_income_val}万円")
        self.lbl_return_val.setText(f"{ret_val:.1f}%")

        # ViewModelのモデル値を更新
        family_members = self.vm.project_data.get("family_members", [])
        husband = next((m for m in family_members if m.relation == "husband"), None)
        if husband:
            husband.annual_income = h_income_val * 10000.0

        # つみたて口座の金利を更新
        investments = self.vm.project_data.get("investment_accounts", [])
        for inv in investments:
            inv.annual_return_rate = ret_val

        # 再計算を同期的にトリガー（リアルタイムシミュレーション）
        self.vm.trigger_recalculation()

    @Slot(list)
    def update_dashboard(self, results: list):
        """
        再計算結果を受け取り、サマリーとグラフを更新します。
        """
        if not results:
            return

        # 1. 各種分析指標の算出 (Analysis)
        cash_flow = [r["net_cash_flow"] for r in results]
        cash_balances = [r["cash_balance"] for r in results]
        investment_balances = [r["investment_balance"] for r in results]
        nisa_end = results[-1]["investment_balance"]

        # 生涯赤字（手元現金が0円を下回る年齢）の検知
        deficit_year = -1
        for idx, cash in enumerate(cash_balances):
            if cash < 0:
                deficit_year = idx
                break
        
        if deficit_year != -1:
            h_start_age = results[0]["husband_age"] if "husband_age" in results[0] else 30
            self.card_lifetime_deficit.lbl_value.setText(f"あり ({h_start_age + deficit_year}歳〜)")
            self.card_lifetime_deficit.lbl_value.setStyleSheet("color: #d11a2a; font-weight: bold;")
        else:
            self.card_lifetime_deficit.lbl_value.setText("なし（健全）")
            self.card_lifetime_deficit.lbl_value.setStyleSheet("color: #2e7d32; font-weight: bold;")

        # 資産寿命
        if deficit_year != -1:
            h_start_age = results[0]["husband_age"] if "husband_age" in results[0] else 30
            self.card_asset_life.lbl_value.setText(f"{h_start_age + deficit_year}歳")
        else:
            self.card_asset_life.lbl_value.setText("80歳超 (十分)")

        # NISA残高
        self.card_nisa_total.lbl_value.setText(f"{nisa_end / 10000.0:.0f}万円")

        # FIRE可能年齢判定
        fire_year = -1
        for idx, r in enumerate(results):
            annual_spending = r["outflow"]
            total_assets = r["cash_balance"] + r["investment_balance"]
            if annual_spending > 0 and total_assets >= annual_spending * 25:
                fire_year = idx
                break
        
        if fire_year != -1:
            h_start_age = results[0]["husband_age"] if "husband_age" in results[0] else 30
            self.card_fire_age.lbl_value.setText(f"{h_start_age + fire_year}歳可")
        else:
            self.card_fire_age.lbl_value.setText("困難")

        # 2. グラフ描画 (Matplotlib)
        self.ax_cashflow.clear()
        self.ax_asset.clear()

        years_range = np.arange(len(results))
        ages = []
        for r in results:
            if "husband_age" in r:
                ages.append(f"{r['husband_age']}歳")
            else:
                ages.append(f"{r['year']}年目")

        # キャッシュフロー (棒グラフで収支を示す)
        flow_colors = ["#2383e2" if f >= 0 else "#eb5757" for f in cash_flow]
        cash_flow_man = [f / 10000.0 for f in cash_flow]
        self.ax_cashflow.bar(years_range, cash_flow_man, color=flow_colors, alpha=0.6, label="年間キャッシュフロー")
        self.ax_cashflow.set_ylabel("年間収支 (万円)", color="#37352f")
        self.ax_cashflow.axhline(0, color="gray", linewidth=0.8, linestyle="--")

        # 総資産推移 (現預金＋運用資産の折れ線)
        total_assets_man = [(r["cash_balance"] + r["investment_balance"]) / 10000.0 for r in results]
        self.ax_asset.plot(years_range, total_assets_man, color="#2e7d32", linewidth=2.5, marker="o", markersize=3, label="純金融資産高")
        self.ax_asset.set_ylabel("総資産残高 (万円)", color="#2e7d32")

        # X軸ラベルの間引き設定 (5年おき)
        self.ax_cashflow.set_xticks(years_range[::5])
        self.ax_cashflow.set_xticklabels(ages[::5], rotation=30)
        self.ax_cashflow.set_xlabel("年度・年齢 (夫)")

        # タイトルと美装
        self.ax_cashflow.grid(True, linestyle=":", alpha=0.3)
        self.fig.tight_layout()
        self.canvas.draw()
