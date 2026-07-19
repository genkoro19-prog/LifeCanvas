from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QButtonGroup, QComboBox
from PySide6.QtCore import Qt, Signal

class Sidebar(QFrame):
    """
    左側メニュー（Notion風ナビゲーションバー）。
    メニューボタンのクリックによって画面切り替えを行います。
    """
    # 選択インデックスの切り替えを通知するシグナル
    menu_changed = Signal(int)
    # プリセットロードを通知するシグナル
    preset_selected = Signal(str)
    # 手動再計算を通知するシグナル
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.setFixedWidth(200)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(6)

        # ロゴ・アプリアイコンラベル
        logo = QLabel("🎨 LifeCanvas", self)
        logo.setStyleSheet("font-size: 16px; font-weight: bold; padding-left: 10px; margin-bottom: 5px; color: #1a1a1a;")
        layout.addWidget(logo)

        # プリセット選択コンボボックス
        self.combo_preset = QComboBox(self)
        self.combo_preset.addItem("空のプロジェクト (新規)", "empty")
        self.combo_preset.addItem("genki_family (サンプル)", "sample/genki_family.json")
        # デフォルトは空のプロジェクトに設定
        self.combo_preset.setCurrentIndex(0)
        self.combo_preset.setObjectName("PresetCombo")
        self.combo_preset.activated.connect(self._on_preset_changed)
        layout.addWidget(self.combo_preset)
        
        # スペーサー
        layout.addSpacing(10)

        # メニューグループの管理
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # 各メニューボタンの定義 (表示テキスト, QStackedWidget用のインデックス)
        menus = [
            ("📊 ダッシュボード", 0),
            ("📅 年次表 (1年ごと)", 10),
            ("👨\u200d👩\u200d👧 家族構成", 1),
            ("🏠 住宅ローン・計画", 2),
            ("📈 iDeCo / NISA", 3),
            ("🚗 車・移動プラン", 4),
            ("🔔 保険・保障", 5),
            ("📚 教育費プラン", 6),
            ("🕰️ タイムライン編集", 7),
            ("⚖️ シナリオ比較", 8),
            ("📄 レポート出力", 9),
        ]

        for text, index in menus:
            btn = QPushButton(text, self)
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            
            # 初期選択
            if index == 0:
                btn.setChecked(True)
                
            self.button_group.addButton(btn, index)
            layout.addWidget(btn)

        layout.addStretch()

        # 手動更新（再計算）ボタン
        self.btn_refresh = QPushButton("🔄 再計算/更新", self)
        self.btn_refresh.setObjectName("SecondaryButton")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self.btn_refresh)
        
        layout.addSpacing(10)

        # フッター情報
        version_label = QLabel("v1.1.0 (Windows)", self)
        version_label.setStyleSheet("color: #a0a0a0; font-size: 10px; padding-left: 10px;")
        layout.addWidget(version_label)

        # イベントハンドリング
        self.button_group.idClicked.connect(self._on_button_clicked)

    def _on_button_clicked(self, menu_id: int):
        self.menu_changed.emit(menu_id)

    def _on_preset_changed(self, index: int):
        preset_id = self.combo_preset.itemData(index)
        if preset_id and preset_id != "empty":
            self.preset_selected.emit(preset_id)

    def _on_refresh_clicked(self):
        self.refresh_requested.emit()
