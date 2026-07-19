from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from ui.views.event_dialogs import JobChangeDialog, OneTimeEventDialog, InvestmentChangeDialog

class TimelineView(QWidget):
    """
    マトリックス型（年表型）のタイムラインエディタ。
    家族の状況や資金・イベント状況をスプレッドシート形式で一元可視化し、
    直感的にイベントを追加できるコントロールセンター。
    """
    def __init__(self, vm, parent=None):
        super().__init__(parent)
        self.vm = vm
        self._init_ui()
        self._bind_to_vm()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ヘッダー領域
        header_layout = QHBoxLayout()
        header = QLabel("🕰️ ライフイベント・総合年表 (Timeline Matrix)")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        btn_export = QPushButton("Excelへ書き出し ⬇️")
        btn_export.setStyleSheet("background-color: #217346; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        btn_export.clicked.connect(self._export_to_excel)
        header_layout.addWidget(btn_export)
        
        main_layout.addLayout(header_layout)

        desc = QLabel("シミュレーションの全貌が一目で分かります。イベントを追加したい行を選択して「イベント追加」を押してください。")
        desc.setStyleSheet("color: #666;")
        main_layout.addWidget(desc)

        # コントロールバー
        ctrl_layout = QHBoxLayout()
        
        self.event_type_combo = QComboBox()
        self.event_type_combo.addItems([
            "基本イベント（一時出費・収入）",
            "就業変更（転職・育休開始）",
            "投資変更（NISA増額など）",
            "住宅変更（繰上返済・賃貸化）"
        ])
        
        btn_add = QPushButton("選択した年にイベントを追加 ➕")
        btn_add.setStyleSheet("background-color: #2F80ED; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        btn_add.clicked.connect(self._add_event_from_selection)
        
        ctrl_layout.addWidget(QLabel("追加するイベント種別:"))
        ctrl_layout.addWidget(self.event_type_combo)
        ctrl_layout.addWidget(btn_add)
        
        # コピーボタン追加
        btn_copy = QPushButton("選択セルをコピー 📋")
        btn_copy.setStyleSheet("background-color: #ECEFF1; color: #333; padding: 6px 12px; border-radius: 4px; border: 1px solid #CCC;")
        btn_copy.clicked.connect(self._copy_selected_cell)
        ctrl_layout.addWidget(btn_copy)
        
        ctrl_layout.addStretch()
        
        main_layout.addLayout(ctrl_layout)

        # 年表テーブル
        self.table = QTableWidget()
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "西暦", "年後", "夫 (年齢/年収)", "妻 (年齢/年収)", 
            "子供", "発生イベント (手動追加分)", "資金・キャッシュフロー", "純資産"
        ])
        
        # テーブル設定
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch) # イベント列を伸ばす
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setStyleSheet("QTableWidget { alternate-background-color: #f9f9f9; border: 1px solid #ddd; }")
        
        main_layout.addWidget(self.table)

    def _bind_to_vm(self):
        self.vm.simulation_updated.connect(self._refresh_timeline)
        self._refresh_timeline()

    def _refresh_timeline(self, *args, **kwargs):
        """シミュレーション結果とLifeEventリストをマージしてテーブルに描画する"""
        results = self.vm.sim_results
        if not results:
            self.table.setRowCount(0)
            return
            
        events = self.vm.project_data.get("life_events", [])
        
        self.table.setRowCount(len(results))
        
        for y, dat in enumerate(results):
            # 西暦と年後
            current_year = 2026 + y
            self.table.setItem(y, 0, self._create_item(f"{current_year}年", bold=True))
            self.table.setItem(y, 1, self._create_item(f"{y}年後"))
            
            # 夫の状態
            h_age = dat.get("husband_age", "-")
            h_inc = dat.get("husband_gross_income", 0) / 10000
            h_pen = dat.get("husband_pension", 0) / 10000
            h_ben = dat.get("husband_benefit", 0) / 10000
            
            if h_pen > 0 and h_inc == 0:
                h_text = f"{h_age}歳 / 年金{h_pen:.0f}万"
            else:
                h_text = f"{h_age}歳 / 年収{h_inc:.0f}万"
                if h_ben > 0:
                    h_text += f"\n(給付{h_ben:.0f}万)"
            self.table.setItem(y, 2, self._create_item(h_text if h_age != "-" else "-"))
            
            # 妻の状態
            w_age = dat.get("wife_age", "-")
            w_inc = dat.get("wife_gross_income", 0) / 10000
            w_pen = dat.get("wife_pension", 0) / 10000
            w_ben = dat.get("wife_benefit", 0) / 10000
            
            if w_pen > 0 and w_inc == 0:
                w_text = f"{w_age}歳 / 年金{w_pen:.0f}万"
            else:
                w_text = f"{w_age}歳 / 年収{w_inc:.0f}万"
                if w_ben > 0:
                    w_text += f"\n(給付{w_ben:.0f}万)"
            self.table.setItem(y, 3, self._create_item(w_text if w_age != "-" else "-"))
            
            # 子供
            c_ages = dat.get("children_ages", [])
            c_text = ", ".join(c_ages) if c_ages else "-"
            self.table.setItem(y, 4, self._create_item(c_text))
            
            # 当該年のLifeEventとSystemEventをマージして整理
            year_events = [e for e in events if e.elapsed_year == y]
            system_events = dat.get("system_events", [])
            
            category_icons = {
                "job": "💼", "investment": "📈", "housing": "🏠", 
                "family": "👨", "car": "🚗", "education": "🎓", "other": "📌"
            }
            
            ev_str_list = []
            for e in year_events:
                # ユーザー追加イベント
                c_icon = category_icons.get(getattr(e, "category", "other"), "📌")
                ev_str_list.append(f"{c_icon} {e.name}")
            for se in system_events:
                ev_str_list.append(f"🏛️ {se}")
                
            ev_item = self._create_item("\n".join(ev_str_list) if ev_str_list else "-")
            if ev_str_list:
                ev_item.setForeground(QColor("#D32F2F"))
                ev_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(y, 5, ev_item)
            
            # 資金フロー
            inc = dat.get("inflow", 0) / 10000
            out = dat.get("outflow", 0) / 10000
            ncf = dat.get("net_cash_flow", 0) / 10000
            inv_dep = dat.get("investment_deposit", 0) / 10000
            inv_sold = dat.get("investment_sold", 0) / 10000
            cash = dat.get("cash_balance", 0) / 10000
            
            flow_text = f"通常収支:{ncf:+,.0f}万\n投資:{inv_dep:,.0f}万 売却:{inv_sold:,.0f}万\n現預金:{cash:,.0f}万"
            full_flow_tooltip = (f"【現金フロー詳細】\n通常収入: {inc:,.0f}万円\n通常支出: {out:,.0f}万円\n"
                                 f"通常収支: {ncf:+,.0f}万円\n\nNISA等積立: -{inv_dep:,.0f}万円\n"
                                 f"NISA等売却: +{inv_sold:,.0f}万円\n\n最終現金残高: {cash:,.0f}万円")
            flow_item = self._create_item(flow_text)
            flow_item.setToolTip(full_flow_tooltip)
            
            if cash < 0:
                # 現金が見事にマイナス（ショート）した場合は太字の赤字で目立たせる
                flow_item.setForeground(QColor("#B71C1C"))
                flow_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif ncf < 0:
                flow_item.setForeground(QColor("#E53935"))
            self.table.setItem(y, 6, flow_item)
            
            # 純資産
            nw = dat.get("net_worth", 0) / 10000
            nw_item = self._create_item(f"{nw:.0f}万", bold=True)
            if nw < 0:
                nw_item.setForeground(QColor("#E53935"))
            self.table.setItem(y, 7, nw_item)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(5, 300) 
        
        # 行の高さを制限して無駄な余白を防ぐ
        self.table.verticalHeader().setDefaultSectionSize(75)

    def _create_item(self, text, bold=False):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # 編集不可
        item.setToolTip(text) # 見切れた場合もマウスオーバーで確認できる
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        return item

    def _copy_selected_cell(self):
        from PySide6.QtGui import QGuiApplication
        
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "コピー", "コピーしたい行を選択してください。")
            return
            
        row = selected_rows[0].row()
        cols = self.table.columnCount()
        
        row_text_parts = []
        for col in range(cols):
            item = self.table.item(row, col)
            if item:
                # ツールチップがある場合（改行を含んだ詳細データ）はそれを優先して平坦化
                val = item.toolTip() if item.toolTip() else item.text()
                val = val.replace("\n", " ") # 1行の中に改行があると面倒なのでスペース置換
                row_text_parts.append(val)
                
        text_to_copy = "\t".join(row_text_parts)
        
        cb = QGuiApplication.clipboard()
        cb.setText(text_to_copy)
        
        QMessageBox.information(self, "コピー完了", "選択した行（1年分の詳細データ）をクリップボードにコピーしました！")

    def _add_event_from_selection(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "エラー", "イベントを追加したい『年』の行を選択してください。")
            return
            
        elapsed_year = selected_rows[0].row()
        year = 2026 + elapsed_year
        ev_type = self.event_type_combo.currentText()

        # サブダイアログの起動
        if "基本イベント" in ev_type:
            dlg = OneTimeEventDialog("基本イベントの追加", year, self)
        elif "就業変更" in ev_type:
            dlg = JobChangeDialog("就業変更・年収変更の追加", year, self)
        elif "投資変更" in ev_type:
            dlg = InvestmentChangeDialog("投資積立変更の追加", year, self)
        else:
            QMessageBox.information(self, "未実装", f"『{ev_type}』のダイアログは準備中です。")
            return

        if dlg.exec():
            res = dlg.result_data
            if res:
                from core.models.event import LifeEvent
                import uuid
                
                new_event = LifeEvent(
                    event_id=str(uuid.uuid4())[:8],
                    name=res["name"],
                    category=res["category"],
                    elapsed_year=elapsed_year,
                    one_time_cost=res.get("one_time_cost", 0.0),
                    one_time_income=res.get("one_time_income", 0.0),
                    details=res.get("details", {})
                )
                
                if "life_events" not in self.vm.project_data:
                    self.vm.project_data["life_events"] = []
                    
                self.vm.project_data["life_events"].append(new_event)
                self.vm.trigger_recalculation()

    def _export_to_excel(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from core.report_generator import ReportGenerator

        if not self.vm.sim_results:
            QMessageBox.warning(self, "エラー", "シミュレーションデータがありません。")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(self, "Excelファイルを保存", "", "Excel Files (*.xlsx)")
        if filepath:
            try:
                events = self.vm.project_data.get("life_events", [])
                meta = self.vm.project_data.get("metadata", {})
                ReportGenerator.export_timeline_to_excel(filepath, self.vm.sim_results, events, meta)
                QMessageBox.information(self, "成功", f"タイムラインExcelの出力が完了しました:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "書き出しエラー", f"失敗しました:\n{e}")

    def _on_cell_double_clicked(self, row, col):
        if col == 5:
            from ui.views.event_dialogs import YearEventManagerDialog
            year = 2026 + row
            dlg = YearEventManagerDialog(row, year, self.vm, self)
            dlg.exec()
