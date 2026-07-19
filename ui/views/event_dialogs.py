from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QSpinBox, QComboBox, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt

class BaseEventDialog(QDialog):
    """イベント編集・追加用の汎用ダイアログベース"""
    def __init__(self, title, year, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        self.year = year
        self.result_data = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        
        # 共通ヘッダー
        lbl = QLabel(f"{year}年のイベント設定")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(lbl)
        
        # フォーム部分
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        
        # サブクラスでフィールドを追加するメソッドを呼ぶ
        self._setup_fields()
        
        # 共通ボタン
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存")
        self.btn_save.setStyleSheet("background-color: #2F80ED; color: white; padding: 5px; font-weight: bold;")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("キャンセル")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        self.layout.addLayout(btn_layout)

    def _setup_fields(self):
        pass

    def _on_save(self):
        self.accept()


class JobChangeDialog(BaseEventDialog):
    """就業変更・年収変更のダイアログ"""
    def _setup_fields(self):
        self.name_edit = QLineEdit("転職・就業変更")
        self.form_layout.addRow("イベント名:", self.name_edit)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["husband", "wife"]) # TODO: vmから家族一覧を取得するのがベスト
        self.form_layout.addRow("対象者:", self.target_combo)
        
        self.salary_spin = QSpinBox()
        self.salary_spin.setRange(0, 100000000)
        self.salary_spin.setSingleStep(100000)
        self.salary_spin.setSuffix(" 円")
        self.form_layout.addRow("変更後年収:", self.salary_spin)
        
    def _on_save(self):
        self.result_data = {
            "name": self.name_edit.text(),
            "category": "job",
            "details": {
                "action": "update_salary",
                "target": self.target_combo.currentText(),
                "value": self.salary_spin.value()
            }
        }
        super()._on_save()


class OneTimeEventDialog(BaseEventDialog):
    """一時的な支出・収入イベント用ダイアログ"""
    def _setup_fields(self):
        self.name_edit = QLineEdit("一時イベント")
        self.form_layout.addRow("イベント名:", self.name_edit)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["支出 (出費)", "収入 (受取)"])
        self.form_layout.addRow("タイプ:", self.type_combo)
        
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(0, 100000000)
        self.amount_spin.setSingleStep(10000)
        self.amount_spin.setSuffix(" 円")
        self.form_layout.addRow("金額:", self.amount_spin)
        
    def _on_save(self):
        amount = self.amount_spin.value()
        is_cost = self.type_combo.currentIndex() == 0
        self.result_data = {
            "name": self.name_edit.text(),
            "category": "other",
            "one_time_cost": amount if is_cost else 0.0,
            "one_time_income": 0.0 if is_cost else amount,
            "details": {}
        }
        super()._on_save()

class InvestmentChangeDialog(BaseEventDialog):
    """NISAなどの積立額変更用ダイアログ"""
    def _setup_fields(self):
        self.name_edit = QLineEdit("積立額変更")
        self.form_layout.addRow("イベント名:", self.name_edit)
        
        self.target_combo = QComboBox()
        # TODO: 厳密には口座名など。現状のサンプル仕様にあわせる
        self.target_combo.addItems(["nisa_husband", "nisa_wife", "cash_husband"])
        self.form_layout.addRow("対象口座:", self.target_combo)
        
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(0, 10000000)
        self.amount_spin.setSingleStep(10000)
        self.amount_spin.setSuffix(" 円")
        self.form_layout.addRow("新月額積立金:", self.amount_spin)

    def _on_save(self):
        self.result_data = {
            "name": self.name_edit.text(),
            "category": "investment",
            "details": {
                "action": "update_nisa_deposit",
                "target": self.target_combo.currentText(),
                "value": self.amount_spin.value()
            }
        }
        super()._on_save()

from PySide6.QtWidgets import QListWidget


from PySide6.QtWidgets import QListWidget

class YearEventManagerDialog(QDialog):
    def __init__(self, elapsed_year, sim_year, vm, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{sim_year}年のイベント管理")
        self.setMinimumWidth(400)
        
        self.elapsed_year = elapsed_year
        self.vm = vm
        self.year_events = []
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"{sim_year}年の手動イベント一覧")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
        desc = QLabel("※システム制御の自動イベント（年齢変更等）は表示されません。")
        desc.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("選択イベントを削除")
        btn_delete.setStyleSheet("background-color: #E53935; color: white; padding: 5px; font-weight: bold;")
        btn_delete.clicked.connect(self._delete_selected)
        
        btn_close = QPushButton("閉じる")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
    def refresh_list(self):
        self.list_widget.clear()
        events = self.vm.project_data.get("life_events", [])
        self.year_events = [e for e in events if e.elapsed_year == self.elapsed_year]
        for e in self.year_events:
            self.list_widget.addItem(f"[{e.category}] {e.name}")
            
    def _delete_selected(self):
        idx = self.list_widget.currentRow()
        if idx >= 0:
            ev = self.year_events[idx]
            if ev in self.vm.project_data["life_events"]:
                self.vm.project_data["life_events"].remove(ev)
                self.vm.trigger_recalculation()
                self.refresh_list()
