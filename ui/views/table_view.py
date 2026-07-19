from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout, QFrame, QDialog, QFormLayout, QGroupBox, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QBrush, QFont, QIcon


# カラーパレット定義
COLOR_POSITIVE = QColor("#2d7d46")    # 黒字（深緑）
COLOR_NEGATIVE = QColor("#c0392b")    # 赤字
COLOR_HEADER_BG = QColor("#f0f4f8")   # ヘッダー背景
COLOR_GROUP_INCOME = QColor("#eaf6ee")    # 収入セクションの背景
COLOR_GROUP_EXPENSE = QColor("#fdf2f0")   # 支出セクションの背景
COLOR_GROUP_BALANCE = QColor("#eef3fc")   # 残高セクションの背景
COLOR_SEPARATOR = QColor("#d0d7de")       # セパレータ行


class DataTableView(QWidget):
    """
    年次推移表（キャッシュフロー・資産）ビュー。
    夫・妻を分離し、収入/支出/残高の3セクションに色分けした見やすいテーブル。
    """
    # テーブルの列定義（行ではなく列に年、行に項目を配置 → 横長すぎるので通常形式で）
    # 通常形式: 行=年、列=項目

    COLUMNS = [
        # --- 基本情報 ---
        ("経過\n年数", "year",           "info"),
        ("夫\n年齢", "husband_age",      "info"),
        ("妻\n年齢", "wife_age",         "info"),
        ("子供\n年齢", "children_ages",   "info"),
        # --- 収入 ---
        ("夫 額面\n年収", "husband_gross_income", "income"),
        ("夫 手取\n年収", "husband_net_income",   "income"),
        ("妻 額面\n年収", "wife_gross_income",     "income"),
        ("妻 手取\n年収", "wife_net_income",       "income"),
        ("夫 年金", "husband_pension",             "income"),
        ("妻 年金", "wife_pension",                "income"),
        ("給付金\n児童手当等", "benefits",           "income"),
        ("賃貸\n収入", "rental_income",             "income"),
        # --- 支出 ---
        ("生活費", "living_cost",       "expense"),
        ("教育費", "education_cost",    "expense"),
        ("住宅関連\n費用", "housing_cost", "expense"),
        ("車 費用", "car_cost",         "expense"),
        ("保険料", "insurance_cost",    "expense"),
        ("ｲﾍﾞﾝﾄ\n支出", "event_cost",   "expense"),
        ("積立\n投資額", "investment_deposit", "expense"),
        # --- 収支 ---
        ("単年\n収支", "net_cash_flow",  "balance"),
        # --- 残高 ---
        ("現金\n残高", "cash_balance",        "balance"),
        ("投資\n残高", "investment_balance",  "balance"),
        ("ローン\n残高", "loan_balance",      "balance"),
        ("純資産", "net_worth",              "balance"),
        # --- メモ ---
        ("イベント・備考", "event_names",    "memo"),
    ]

    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        self.current_results = []
        self._init_ui()
        self.vm.simulation_updated.connect(self.update_table)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # ヘッダー
        header_layout = QHBoxLayout()
        header = QLabel("📅 年次キャッシュフロー詳細表", self)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a1a;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        # 凡例
        legend = QLabel(
            '<span style="color:#2d7d46;">■</span> 収入　'
            '<span style="color:#c0392b;">■</span> 支出　'
            '<span style="color:#3a6bc5;">■</span> 残高',
            self
        )
        legend.setStyleSheet("font-size: 11px; color: #555;")
        header_layout.addWidget(legend)
        layout.addLayout(header_layout)

        desc = QLabel("💡 単位：万円。赤字はﾏｲﾅｽ。任意のセルをダブルクリックすると「計算の内訳詳細」が確認できます。", self)
        desc.setStyleSheet("color: #0056b3; font-size: 12px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(desc)

        # テーブル
        col_count = len(self.COLUMNS)
        self.table = QTableWidget(0, col_count, self)

        # ヘッダー設定
        headers = [col[0] for col in self.COLUMNS]
        self.table.setHorizontalHeaderLabels(headers)

        h_header = self.table.horizontalHeader()
        h_header.setDefaultSectionSize(72)
        h_header.setSectionResizeMode(QHeaderView.Interactive)
        # 最後の「イベント・備考」列は伸縮
        h_header.setSectionResizeMode(col_count - 1, QHeaderView.Stretch)
        # 基本情報列は狭くする
        for i in range(4):
            h_header.resizeSection(i, 52)

        # ヘッダーのスタイリング
        h_header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f4f8;
                color: #333;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #ddd;
                padding: 3px;
            }
        """)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                font-size: 11px;
                selection-background-color: #d6e9ff;
            }
            QTableWidget::item {
                padding: 2px 4px;
            }
            QTableWidget::item:hover {
                background-color: #f1f8ff;
            }
        """)
        
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.table)

    def _format_man_yen(self, val: float) -> str:
        """円を万円に変換してフォーマット"""
        man = val / 10000.0
        if man == 0:
            return "-"
        return f"{man:,.1f}"

    def _make_item(self, text: str, group: str, value: float = 0.0) -> QTableWidgetItem:
        """セルアイテムを生成（色・アライメント付き）"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # グループに応じた背景色
        if group == "income":
            item.setBackground(QBrush(COLOR_GROUP_INCOME))
        elif group == "expense":
            item.setBackground(QBrush(COLOR_GROUP_EXPENSE))
        elif group == "balance":
            item.setBackground(QBrush(COLOR_GROUP_BALANCE))

        # 値がマイナスなら赤字
        if value < 0:
            item.setForeground(QBrush(COLOR_NEGATIVE))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        elif group == "income" and value > 0:
            item.setForeground(QBrush(COLOR_POSITIVE))

        return item

    @Slot(list)
    def update_table(self, results: list):
        self.current_results = results
        if not results:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(results))

        for row, r in enumerate(results):
            for col, (label, key, group) in enumerate(self.COLUMNS):
                raw = r.get(key, 0)

                # 特殊フォーマット
                if key == "year":
                    text = f"{raw}"
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    # 5年おきにハイライト
                    if raw > 0 and raw % 5 == 0:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    self.table.setItem(row, col, item)
                    continue

                elif key == "husband_age" or key == "wife_age":
                    text = f"{raw}" if raw else "-"
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)
                    continue

                elif key == "children_ages":
                    ages = r.get(key, [])
                    if ages:
                        text = "/".join(str(a) for a in ages)
                    else:
                        text = "-"
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)
                    continue

                elif key == "event_names":
                    names = r.get(key, [])
                    text = ", ".join(names) if names else ""
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    if names:
                        item.setForeground(QBrush(QColor("#8b5500")))
                    self.table.setItem(row, col, item)
                    continue

                # 数値項目（万円表示）
                val = float(raw) if raw else 0.0
                text = self._format_man_yen(val)
                item = self._make_item(text, group, val)
                self.table.setItem(row, col, item)

            # 行の高さを少し詰める
            self.table.setRowHeight(row, 26)

    def _on_cell_double_clicked(self, row: int, col: int):
        if not self.current_results or row >= len(self.current_results):
            return
        data = self.current_results[row]
        dialog = DetailDialog(data, self)
        dialog.exec()


class DetailDialog(QDialog):
    """
    特定年の詳細な計算根拠・内訳を表示するダイアログ
    """
    def __init__(self, year_data: dict, parent=None):
        super().__init__(parent)
        self.data = year_data
        year = self.data.get("year", 0)
        h_age = self.data.get("husband_age", "-")
        w_age = self.data.get("wife_age", "-")
        self.setWindowTitle(f"🔍 {year}年後 （夫: {h_age}歳 / 妻: {w_age}歳）のキャッシュフロー内訳")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(15)

        # 1. 年間収支と純資産の全体像
        inflow = self.data.get("inflow", 0) / 10000
        outflow = self.data.get("outflow", 0) / 10000
        net_cf = self.data.get("net_cash_flow", 0) / 10000
        net_worth = self.data.get("net_worth", 0) / 10000
        
        summary_group = QGroupBox("📊 全体サマリー")
        summary_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        slayout = QFormLayout(summary_group)
        slayout.addRow("総収入 (手取りなど流入合計):", QLabel(f"{inflow:,.1f} 万円"))
        slayout.addRow("総支出 (生活費・ローン・投資積立前):", QLabel(f"{outflow:,.1f} 万円"))
        lbl_net = QLabel(f"{net_cf:,.1f} 万円")
        lbl_net.setStyleSheet("color: red; font-weight: bold;" if net_cf < 0 else "color: green; font-weight: bold;")
        slayout.addRow("単年 キャッシュフロー:", lbl_net)
        slayout.addRow("純資産 (金融＋不動産－負債):", QLabel(f"{net_worth:,.1f} 万円"))
        form_layout.addWidget(summary_group)

        # 2. 収入・税金内訳
        income_group = QGroupBox("💰 収入・税金・社会保険料の内訳")
        income_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        ilayout = QFormLayout(income_group)
        
        h_tax = self.data.get("h_tax_data", {})
        h_gross = self.data.get("husband_gross_income", 0) / 10000
        h_net = h_tax.get("net_income", 0) / 10000
        h_soc = h_tax.get("social_insurance", 0) / 10000
        h_inc_tax = h_tax.get("income_tax", 0) / 10000
        h_inh_tax = h_tax.get("inhabitants_tax", 0) / 10000
        
        ilayout.addRow(QLabel("<b>【夫】</b>"))
        ilayout.addRow("額面年収:", QLabel(f"{h_gross:,.1f} 万円"))
        ilayout.addRow(" └ 社会保険料:", QLabel(f"▲ {h_soc:,.1f} 万円"))
        ilayout.addRow(" └ 所得税:", QLabel(f"▲ {h_inc_tax:,.1f} 万円"))
        ilayout.addRow(" └ 住民税:", QLabel(f"▲ {h_inh_tax:,.1f} 万円"))
        # 住宅ローン控除が適用されている場合
        h_deduct = h_tax.get("housing_deduction_applied", 0) / 10000
        if h_deduct > 0:
            lbl_d = QLabel(f"<span style='color:green;'>+ {h_deduct:,.1f} 万円</span> (還付/控除)")
            ilayout.addRow(" └ 住宅ローン控除 (所得増扱い):", lbl_d)
        ilayout.addRow("手取り収入 (実際の手元):", QLabel(f"<b>{h_net:,.1f} 万円</b>"))

        w_tax = self.data.get("w_tax_data", {})
        w_gross = self.data.get("wife_gross_income", 0) / 10000
        w_net = w_tax.get("net_income", 0) / 10000
        w_soc = w_tax.get("social_insurance", 0) / 10000
        w_inc_tax = w_tax.get("income_tax", 0) / 10000
        w_inh_tax = w_tax.get("inhabitants_tax", 0) / 10000
        ilayout.addRow(QLabel("<b>【妻】</b>"))
        ilayout.addRow("額面年収:", QLabel(f"{w_gross:,.1f} 万円"))
        ilayout.addRow(" └ 社会保険料:", QLabel(f"▲ {w_soc:,.1f} 万円"))
        ilayout.addRow(" └ 所得・住民税:", QLabel(f"▲ {w_inc_tax+w_inh_tax:,.1f} 万円"))
        ilayout.addRow("手取り収入 (実際の手元):", QLabel(f"<b>{w_net:,.1f} 万円</b>"))
        
        benefits = self.data.get("benefits", 0) / 10000
        if benefits > 0:
            ilayout.addRow("<b>【給付金】 (児童手当/育休等):</b>", QLabel(f"<span style='color:green;'>+ {benefits:,.1f} 万円</span>"))
        form_layout.addWidget(income_group)

        # 3. 住宅費などの内訳
        house_group = QGroupBox("🏠 住宅費の内訳")
        house_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        hlayout = QFormLayout(house_group)
        hb = self.data.get("housing_breakdown", {})
        h_loan = hb.get("loan", 0) / 10000
        h_prop = hb.get("property_tax", 0) / 10000
        h_mai = hb.get("maintenance", 0) / 10000
        h_ins = hb.get("insurance", 0) / 10000
        h_total = self.data.get("housing_cost", 0) / 10000
        
        hlayout.addRow("住宅ローン返済:", QLabel(f"{h_loan:,.1f} 万円"))
        hlayout.addRow("固定資産税:", QLabel(f"{h_prop:,.1f} 万円"))
        hlayout.addRow("修繕積立・リフォーム費:", QLabel(f"{h_mai:,.1f} 万円"))
        hlayout.addRow("火災・地震保険:", QLabel(f"{h_ins:,.1f} 万円"))
        hlayout.addRow("住宅関連費 合計:", QLabel(f"<b>{h_total:,.1f} 万円</b>"))
        form_layout.addWidget(house_group)

        # 4. 車費用内訳
        cb = self.data.get("car_breakdown", {})
        if cb and sum(cb.values()) > 0:
            car_group = QGroupBox("🚗 車両費用の内訳")
            car_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            clayout = QFormLayout(car_group)
            clayout.addRow("車両購入費用:", QLabel(f"{cb.get('purchase', 0)/10000:,.1f} 万円"))
            clayout.addRow("マイカーローン返済:", QLabel(f"{cb.get('loan', 0)/10000:,.1f} 万円"))
            clayout.addRow("維持費 (ガソリン/駐車場):", QLabel(f"{cb.get('maintenance', 0)/10000:,.1f} 万円"))
            clayout.addRow("車検代:", QLabel(f"{cb.get('inspection', 0)/10000:,.1f} 万円"))
            clayout.addRow("自動車保険等:", QLabel(f"{cb.get('insurance', 0)/10000:,.1f} 万円"))
            c_total = self.data.get("car_cost", 0) / 10000
            clayout.addRow("車両費用 合計:", QLabel(f"<b>{c_total:,.1f} 万円</b>"))
            form_layout.addWidget(car_group)

        # 5. 教育費
        eb = self.data.get("education_breakdown", {})
        if eb:
            edu_group = QGroupBox("📚 教育費の内訳")
            edu_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            elayout = QFormLayout(edu_group)
            for child_name, cost in eb.items():
                elayout.addRow(f"{child_name}の教育費:", QLabel(f"{cost/10000:,.1f} 万円"))
            form_layout.addWidget(edu_group)

        # 6. 一時的イベント
        event_names = self.data.get("event_names", [])
        if event_names:
            ev_group = QGroupBox("📌 ライフイベント")
            ev_group.setStyleSheet("QGroupBox { font-weight: bold; }")
            evlayout = QFormLayout(ev_group)
            evlayout.addRow("内容:", QLabel(", ".join(event_names)))
            ev_income = self.data.get("event_income", 0) / 10000
            ev_cost = self.data.get("event_cost", 0) / 10000
            if ev_income > 0:
                evlayout.addRow("一時収入:", QLabel(f"<span style='color:green;'>+ {ev_income:,.1f} 万円</span>"))
            if ev_cost > 0:
                evlayout.addRow("一時支出:", QLabel(f"<span style='color:red;'>▲ {ev_cost:,.1f} 万円</span>"))
            form_layout.addWidget(ev_group)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # ボトムボタン群
        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 詳細テキストをコピー", self)
        btn_copy.setStyleSheet("background-color: #ECEFF1; color: #333; padding: 8px; font-weight: bold; border-radius: 4px; border: 1px solid #CCC;")
        btn_copy.clicked.connect(self._copy_details)
        btn_layout.addWidget(btn_copy)

        btn_close = QPushButton("閉じる", self)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("background-color: #e0e0e0; color: #333; padding: 8px; font-weight: bold; border-radius: 4px;")
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def _copy_details(self):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QMessageBox
        
        lines = []
        lines.append(self.windowTitle())
        lines.append("-" * 40)
        
        # summary
        lines.append("【全体サマリー】")
        lines.append(f"総収入: {self.data.get('inflow', 0)/10000:,.1f} 万円")
        lines.append(f"総支出: {self.data.get('outflow', 0)/10000:,.1f} 万円")
        lines.append(f"単年収支: {self.data.get('net_cash_flow', 0)/10000:,.1f} 万円")
        lines.append(f"純資産: {self.data.get('net_worth', 0)/10000:,.1f} 万円")
        lines.append("-" * 40)
        
        # ================ 詳細な内訳を生成 ================
        # --- 収入・手取り・税金 ---
        h_tax = self.data.get("h_tax_data", {})
        h_gross = self.data.get("husband_gross_income", 0) / 10000
        h_net = h_tax.get("net_income", 0) / 10000
        h_soc = h_tax.get("social_insurance", 0) / 10000
        h_tax_total = (h_tax.get("income_tax", 0) + h_tax.get("inhabitants_tax", 0)) / 10000
        h_deduct = h_tax.get("housing_deduction_applied", 0) / 10000

        w_tax = self.data.get("w_tax_data", {})
        w_gross = self.data.get("wife_gross_income", 0) / 10000
        w_net = w_tax.get("net_income", 0) / 10000
        w_soc = w_tax.get("social_insurance", 0) / 10000
        w_tax_total = (w_tax.get("income_tax", 0) + w_tax.get("inhabitants_tax", 0)) / 10000
        
        benefits = self.data.get("benefits", 0) / 10000
        
        lines.append("【収入・税金】")
        lines.append(f"夫 額面年収: {h_gross:,.1f} 万円  (手取り: {h_net:,.1f} 万円, 保険税金等: {h_soc+h_tax_total:,.1f} 万円" + (f", 住宅控除: {h_deduct:,.1f} 万円)" if h_deduct>0 else ")"))
        lines.append(f"妻 額面年収: {w_gross:,.1f} 万円  (手取り: {w_net:,.1f} 万円, 保険税金等: {w_soc+w_tax_total:,.1f} 万円)")
        if benefits > 0:
            lines.append(f"給付金(児童手当等): {benefits:,.1f} 万円")
            
        lines.append("-" * 40)
        
        # --- 支出明細 ---
        lines.append("【支出明細】")
        living = self.data.get("living_cost", 0) / 10000
        lines.append(f"基本生活費: {living:,.1f} 万円")
        
        hb = self.data.get("housing_breakdown", {})
        if sum(hb.values()) > 0:
            h_loan = hb.get("loan", 0) / 10000
            h_prop = hb.get("property_tax", 0) / 10000
            h_mai = hb.get("maintenance", 0) / 10000
            h_ins = hb.get("insurance", 0) / 10000
            h_total = self.data.get("housing_cost", 0) / 10000
            lines.append(f"住宅費合計: {h_total:,.1f} 万円 (ローン:{h_loan:,.1f}, 固定資産税:{h_prop:,.1f}, 修繕:{h_mai:,.1f}, 保険:{h_ins:,.1f})")

        cb = self.data.get("car_breakdown", {})
        if cb and sum(cb.values()) > 0:
            c_total = self.data.get("car_cost", 0) / 10000
            lines.append(f"車両費合計: {c_total:,.1f} 万円 (購入:{cb.get('purchase',0)/10000:,.1f}, ローン:{cb.get('loan',0)/10000:,.1f}, 維持:{cb.get('maintenance',0)/10000:,.1f})")

        eb = self.data.get("education_breakdown", {})
        if eb:
            for child, cost in eb.items():
                lines.append(f"教育費 ({child}): {cost/10000:,.1f} 万円")
                
        ev_names = self.data.get("event_names", [])
        if ev_names:
            ev_cost = self.data.get("event_cost", 0) / 10000
            if ev_cost > 0:
                lines.append(f"ライフイベント支出: {ev_cost:,.1f} 万円 ({', '.join(ev_names)})")

        lines.append("-" * 40)
        
        # --- 投資・資産情報 ---
        lines.append("【投資キャッシュフロー・残高】")
        inv_dep = self.data.get("investment_deposit", 0) / 10000
        inv_sold = self.data.get("investment_sold", 0) / 10000
        cash = self.data.get("cash_balance", 0) / 10000
        lines.append(f"NISA等 本年積立: -{inv_dep:,.1f} 万円")
        if inv_sold > 0:
            lines.append(f"NISA等 本年売却: +{inv_sold:,.1f} 万円 (※資金補填)")
        lines.append(f"最終 現預金残高: {cash:,.1f} 万円")
        
        cb_app = QGuiApplication.clipboard()
        cb_app.setText("\n".join(lines))
        QMessageBox.information(self, "コピー完了", "詳細内容をクリップボードにコピーしました！")
