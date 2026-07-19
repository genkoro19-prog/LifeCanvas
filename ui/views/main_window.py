from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QFrame, 
    QFileDialog, QMessageBox, QMenuBar, QMenu, QStatusBar, QLabel
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Slot, QDateTime

from ui.views.sidebar import Sidebar
from ui.views.dashboard import Dashboard
from ui.views.input_panels import FamilyPanel, HousePanel, InvestmentPanel, CarPanel, InsurancePanel, EducationPanel
from ui.views.timeline_view import TimelineView
from ui.views.table_view import DataTableView
from ui.views.comparison_view import ComparisonView
from ui.views.report_view import ReportView
from ui.styles import NOTION_STYLE

class MainWindow(QMainWindow):
    """
    LifeCanvas のメインアプリケーションウィンドウ。
    サイドバー、各種ビューを保持する QStackedWidget、
    およびプロジェクト管理メニュー（新規作成、保存、ロード）を統合。
    """
    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        
        self.setWindowTitle("LifeCanvas - ライフプランシミュレーター")
        self.resize(1200, 800)
        self.setStyleSheet(NOTION_STYLE)
        
        self._init_menu()
        self._init_ui()
        self._init_statusbar()
        
        # シミュレーション更新時にステータスバーを更新
        self.vm.simulation_updated.connect(self._on_simulation_updated)
        
        # 初期シミュレーション実行
        self.vm.trigger_recalculation()

    def _init_menu(self):
        """メニューバー（ファイル管理等）の初期化"""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("ファイル(&F)")

        # 新規作成
        new_action = QAction("新規作成", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        # JSON読込
        load_json_action = QAction("JSONインポート...", self)
        load_json_action.triggered.connect(self._load_json)
        file_menu.addAction(load_json_action)

        # JSON保存
        save_json_action = QAction("JSONエクスポート...", self)
        save_json_action.setShortcut("Ctrl+S")
        save_json_action.triggered.connect(self._save_json)
        file_menu.addAction(save_json_action)

        # --- 設定メニュー ---
        settings_menu = menubar.addMenu("設定(&S)")
        master_settings_action = QAction("制度マスタ設定(税・NISA等)...", self)
        master_settings_action.triggered.connect(self._show_master_settings)
        settings_menu.addAction(master_settings_action)
        
        # --- ヘルプメニュー ---
        help_menu = menubar.addMenu("ヘルプ(&H)")
        about_action = QAction("LifeCanvasについて", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        help_menu.addAction(about_action)

        file_menu.addSeparator()

        # SQLite読込
        load_db_action = QAction("読み込み (SQLite)...", self)
        load_db_action.setShortcut("Ctrl+O")
        load_db_action.triggered.connect(self._load_sqlite)
        file_menu.addAction(load_db_action)

        # SQLite保存
        save_db_action = QAction("名前を付けて保存 (SQLite)...", self)
        save_db_action.setShortcut("Ctrl+S")
        save_db_action.triggered.connect(self._save_sqlite)
        file_menu.addAction(save_db_action)

    def _init_statusbar(self):
        """ステータスバーの初期化"""
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        
        self.lbl_project_name = QLabel("プロジェクト: サンプル")
        self.lbl_project_name.setStyleSheet("color: #666; padding-left: 5px;")
        self.status_bar.addWidget(self.lbl_project_name)
        
        self.lbl_calc_time = QLabel("")
        self.lbl_calc_time.setStyleSheet("color: #888; padding-right: 10px;")
        self.status_bar.addPermanentWidget(self.lbl_calc_time)

    def _init_ui(self):
        # メインウィジェット
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左側サイドバー
        self.sidebar = Sidebar(central_widget)
        main_layout.addWidget(self.sidebar)

        # 右側コンテンツコンテナ
        self.content_frame = QFrame(central_widget)
        self.content_frame.setObjectName("ContentFrame")
        
        content_layout = QHBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 各種ビュー（独立したウィジェットとして登録）
        self.stacked_widget = QStackedWidget(self.content_frame)
        
        self.view_dashboard = Dashboard(self.vm, self.stacked_widget)           # 0
        self.view_family = FamilyPanel(self.vm, self.stacked_widget)            # 1
        self.view_house = HousePanel(self.vm, self.stacked_widget)              # 2
        self.view_investment = InvestmentPanel(self.vm, self.stacked_widget)    # 3
        self.view_car = CarPanel(self.vm, self.stacked_widget)                  # 4
        self.view_insurance = InsurancePanel(self.vm, self.stacked_widget)      # 5
        self.view_education = EducationPanel(self.vm, self.stacked_widget)      # 6
        self.view_event = TimelineView(self.vm, self.stacked_widget)            # 7
        self.view_comparison = ComparisonView(self.vm, self.stacked_widget)     # 8
        self.view_report = ReportView(self.vm, self.stacked_widget)             # 9
        self.view_table = DataTableView(self.vm, self.stacked_widget)           # 10

        # QStackedWidget への登録（各画面が独立インスタンス、順序は重要ではない。インデックスで管理）
        # addWidget は追加順に 0, 1, ... を返すため、sidebar.py と合致させます
        self._add_to_stack(self.view_dashboard, 0)
        self._add_to_stack(self.view_family, 1)
        self._add_to_stack(self.view_house, 2)
        self._add_to_stack(self.view_investment, 3)
        self._add_to_stack(self.view_car, 4)
        self._add_to_stack(self.view_insurance, 5)
        self._add_to_stack(self.view_education, 6)
        self._add_to_stack(self.view_event, 7)
        self._add_to_stack(self.view_comparison, 8)
        self._add_to_stack(self.view_report, 9)
        self._add_to_stack(self.view_table, 10)

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(self.content_frame)

        # サイドバー切り替えシグナルのバインド
        self.sidebar.menu_changed.connect(self._on_menu_changed)
        # プリセット選択のバインド
        self.sidebar.preset_selected.connect(self._load_preset)
        # 手動更新のバインド
        self.sidebar.refresh_requested.connect(self.vm.trigger_recalculation)

    def _add_to_stack(self, widget, target_index):
        """指定のインデックスに配置されるようパディングするヘルパー"""
        while self.stacked_widget.count() < target_index:
            self.stacked_widget.addWidget(QWidget())
        if self.stacked_widget.count() == target_index:
            self.stacked_widget.addWidget(widget)
        else:
            self.stacked_widget.insertWidget(target_index, widget)

    def _show_master_settings(self):
        QMessageBox.information(self, "制度マスタ設定", "ここで将来、NISAの上限枠、税率、児童手当の金額などを自由に変更できる設定ウィンドウを表示します。")
        
    def _show_about(self):
        QMessageBox.about(self, "LifeCanvasについて", "LifeCanvas (v1.0)\n\n究極のリッチ・イベントドリブンな人生シムです。\nPowered by AI.")

    def _on_menu_changed(self, index: int):
        """サイドバーメニュー切り替え時に対応するビューを表示"""
        self.stacked_widget.setCurrentIndex(index)

    @Slot(list)
    def _on_simulation_updated(self, results):
        """シミュレーション完了時にステータスバーを更新"""
        now = QDateTime.currentDateTime().toString("HH:mm:ss")
        years = len(results) if results else 0
        self.lbl_calc_time.setText(f"最終計算: {now} ({years}年間)")

    # --- プロジェクトファイルメニューイベント ---

    def _load_preset(self, filepath: str):
        """プリセットを読み込む（genki_family用）"""
        try:
            self.vm.load_from_json(filepath)
            QMessageBox.information(self, "成功", f"プリセット '{filepath}' を読み込みました。")
            self.lbl_project_name.setText(f"プロジェクト: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プリセットの読み込みに失敗しました:\n{e}")

    def _new_project(self):
        reply = QMessageBox.question(
            self, "確認", "現在の編集データを破棄し、新規プロジェクトを作成しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.vm.new_project()

    def _load_json(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "JSONインポート", "", "JSON Files (*.json)")
        if filepath:
            try:
                self.vm.load_from_json(filepath)
                QMessageBox.information(self, "成功", "JSONインポートが完了しました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"インポート中にエラーが発生しました:\n{e}")

    def _save_json(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "JSONエクスポート", "", "JSON Files (*.json)")
        if filepath:
            try:
                self.vm.save_to_json(filepath)
                QMessageBox.information(self, "成功", "JSONエクスポートが完了しました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"エクスポート中にエラーが発生しました:\n{e}")

    def _load_sqlite(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "プロジェクト読み込み (SQLite)", "", "LifeCanvas DB (*.sqlite *.db)")
        if filepath:
            try:
                self.vm.load_from_sqlite(filepath)
                QMessageBox.information(self, "成功", "プロジェクトファイルをロードしました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"読み込み中にエラーが発生しました:\n{e}")

    def _save_sqlite(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "名前を付けて保存 (SQLite)", "", "LifeCanvas DB (*.sqlite *.db)")
        if filepath:
            try:
                self.vm.save_to_sqlite(filepath)
                QMessageBox.information(self, "成功", "プロジェクトファイルを保存しました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"保存中にエラーが発生しました:\n{e}")
