from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
    QDoubleSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Slot, QTimer
from core.models import FamilyMember, LifeEvent, HousePlan, LoanPlan, InvestmentAccount, CarPlan, InsurancePlan, EducationPlan


class _BasePanel(QWidget):
    """入力パネルの基底クラス。遅延再計算のデバウンスタイマーを提供。"""
    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(500)  # 500msのデバウンス
        self._debounce_timer.timeout.connect(self._apply_and_recalc)

    def _schedule_recalc(self):
        """入力変更時にデバウンス付き再計算をスケジュール"""
        self._debounce_timer.start()

    def _apply_and_recalc(self):
        """サブクラスでオーバーライド: データ適用→再計算"""
        pass


# ============================================================
# 1. 家族構成パネル
# ============================================================
class FamilyPanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("👨\u200d👩\u200d👧 世帯メンバー情報", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels([
            "氏名", "続柄", "年齢", "就業状況", "年収 (万円)", "定年年齢", "昇給率 (%)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ メンバー追加", self)
        btn_add.setObjectName("SecondaryButton")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"家族_{row+1}"))
        
        combo_rel = QComboBox(); combo_rel.addItems(["husband", "wife", "child", "other"])
        combo_rel.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 1, combo_rel)

        spin_age = QSpinBox(); spin_age.setRange(0, 100); spin_age.setValue(30)
        spin_age.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 2, spin_age)

        combo_job = QComboBox(); combo_job.addItems(["会社員", "公務員", "自営業", "パート", "無職"])
        combo_job.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 3, combo_job)

        spin_inc = QSpinBox(); spin_inc.setRange(0, 5000); spin_inc.setValue(400)
        spin_inc.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 4, spin_inc)

        spin_ret = QSpinBox(); spin_ret.setRange(50, 80); spin_ret.setValue(65)
        spin_ret.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 5, spin_ret)

        spin_gro = QDoubleSpinBox(); spin_gro.setRange(-5.0, 10.0); spin_gro.setValue(0.0)
        spin_gro.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 6, spin_gro)

    def _apply_and_recalc(self):
        members = []
        for r in range(self.table.rowCount()):
            item_name = self.table.item(r, 0)
            if not item_name:
                continue
            name = item_name.text()
            relation = self.table.cellWidget(r, 1).currentText()
            age = self.table.cellWidget(r, 2).value()
            job = self.table.cellWidget(r, 3).currentText()
            income = self.table.cellWidget(r, 4).value() * 10000.0
            retire = self.table.cellWidget(r, 5).value()
            growth = self.table.cellWidget(r, 6).value()
            
            modifiers = {}
            if relation == "wife":
                modifiers = {
                    "before_birth": 3500000.0, "childcare_leave_continuous": True,
                    "nursery": 576000.0, "elementary": 960000.0, "junior_high": 1152000.0
                }
            members.append(FamilyMember(
                name=name, relation=relation, age=age, annual_income=income,
                retirement_age=retire, current_occupation=job,
                salary_growth_rate=growth, income_modifiers=modifiers
            ))
        self.vm.project_data["family_members"] = members
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        self.table.setRowCount(0)
        for m in self.vm.project_data.get("family_members", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(m.name))
            
            combo_rel = QComboBox(); combo_rel.addItems(["husband", "wife", "child", "other"])
            combo_rel.setCurrentText(m.relation)
            combo_rel.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 1, combo_rel)

            spin_age = QSpinBox(); spin_age.setRange(0, 100); spin_age.setValue(m.age)
            spin_age.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 2, spin_age)

            combo_job = QComboBox(); combo_job.addItems(["会社員", "公務員", "自営業", "パート", "無職"])
            combo_job.setCurrentText(m.current_occupation)
            combo_job.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 3, combo_job)

            spin_inc = QSpinBox(); spin_inc.setRange(0, 5000)
            spin_inc.setValue(int(m.annual_income / 10000.0))
            spin_inc.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 4, spin_inc)

            spin_ret = QSpinBox(); spin_ret.setRange(50, 80); spin_ret.setValue(m.retirement_age)
            spin_ret.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 5, spin_ret)

            spin_gro = QDoubleSpinBox(); spin_gro.setRange(-5.0, 10.0); spin_gro.setValue(m.salary_growth_rate)
            spin_gro.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 6, spin_gro)


# ============================================================
# 2. 住宅計画パネル
# ============================================================
class HousePanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🏠 住宅ローンおよび経費設定", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        form = QFormLayout()
        self.txt_location = QLineEdit("埼玉県吉川市栄町")
        self.spin_price = QSpinBox(); self.spin_price.setRange(0, 20000); self.spin_price.setValue(3170); self.spin_price.setSuffix(" 万円")
        self.spin_term = QSpinBox(); self.spin_term.setRange(5, 50); self.spin_term.setValue(40); self.spin_term.setSuffix(" 年")
        self.dbl_rate = QDoubleSpinBox(); self.dbl_rate.setRange(0.0, 10.0); self.dbl_rate.setValue(1.68); self.dbl_rate.setSuffix(" %")
        self.combo_type = QComboBox(); self.combo_type.addItems(["variable", "fixed"])
        self.spin_tax = QSpinBox(); self.spin_tax.setRange(0, 100); self.spin_tax.setValue(12); self.spin_tax.setSuffix(" 万円/年")
        self.spin_insurance = QSpinBox(); self.spin_insurance.setRange(0, 50); self.spin_insurance.setValue(2); self.spin_insurance.setSuffix(" 万円/年")
        self.spin_sale_year = QSpinBox(); self.spin_sale_year.setRange(0, 50); self.spin_sale_year.setValue(26); self.spin_sale_year.setSuffix(" 年後")

        form.addRow("立地・物件名:", self.txt_location)
        form.addRow("物件購入価格:", self.spin_price)
        form.addRow("ローン返済期間:", self.spin_term)
        form.addRow("ローン金利:", self.dbl_rate)
        form.addRow("金利タイプ:", self.combo_type)
        form.addRow("固定資産税:", self.spin_tax)
        form.addRow("火災保険:", self.spin_insurance)
        form.addRow("売却・賃貸化時期:", self.spin_sale_year)
        layout.addLayout(form)

        # 自動再計算の接続
        for w in [self.spin_price, self.spin_term, self.spin_tax, self.spin_insurance, self.spin_sale_year]:
            w.valueChanged.connect(self._schedule_recalc)
        self.dbl_rate.valueChanged.connect(self._schedule_recalc)
        self.combo_type.currentIndexChanged.connect(self._schedule_recalc)

        layout.addStretch()

    def _apply_and_recalc(self):
        price = self.spin_price.value() * 10000.0
        loan = LoanPlan(
            borrowed_amount=price, term_years=self.spin_term.value(),
            interest_rate=self.dbl_rate.value(), loan_type=self.combo_type.currentText(), start_year=0
        )
        house = HousePlan(
            purchase_price=price, location=self.txt_location.text(), purchase_year=0,
            loan=loan, sale_year=self.spin_sale_year.value(),
            annual_property_tax=self.spin_tax.value() * 10000.0,
            annual_fire_insurance=self.spin_insurance.value() * 10000.0,
            is_rented=False
        )
        self.vm.project_data["housing_plans"] = [house]
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        housing = self.vm.project_data.get("housing_plans", [])
        if housing:
            h = housing[0]
            self.txt_location.setText(h.location)
            self.spin_price.setValue(int(h.purchase_price / 10000.0))
            self.spin_tax.setValue(int(h.annual_property_tax / 10000.0))
            self.spin_insurance.setValue(int(h.annual_fire_insurance / 10000.0))
            self.spin_sale_year.setValue(h.sale_year)
            if h.loan:
                self.spin_term.setValue(h.loan.term_years)
                self.dbl_rate.setValue(h.loan.interest_rate)
                self.combo_type.setCurrentText(h.loan.loan_type)


# ============================================================
# 3. 投資計画パネル
# ============================================================
class InvestmentPanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("📈 積立投資（NISA / iDeCo）の設定", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["口座タイプ", "所有者", "毎月積立額 (万円)", "想定年利 (%)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ 投資口座追加", self)
        btn_add.setObjectName("SecondaryButton")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        combo_type = QComboBox(); combo_type.addItems(["nisa", "ideco", "taxable_investment", "cash"])
        combo_type.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 0, combo_type)

        combo_owner = QComboBox(); combo_owner.addItems(["husband", "wife"])
        combo_owner.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 1, combo_owner)

        spin_monthly = QSpinBox(); spin_monthly.setRange(0, 100); spin_monthly.setValue(3)
        spin_monthly.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 2, spin_monthly)

        spin_ret = QDoubleSpinBox(); spin_ret.setRange(0.0, 15.0); spin_ret.setValue(4.0)
        spin_ret.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 3, spin_ret)

    def _apply_and_recalc(self):
        accounts = []
        for r in range(self.table.rowCount()):
            a_type = self.table.cellWidget(r, 0).currentText()
            owner = self.table.cellWidget(r, 1).currentText()
            monthly = self.table.cellWidget(r, 2).value() * 10000.0
            ret = self.table.cellWidget(r, 3).value()
            changes = {}
            if owner == "husband" and a_type == "nisa" and monthly == 60000.0:
                changes = {5: {"monthly_deposit": 100000.0}}
            accounts.append(InvestmentAccount(
                account_type=a_type, owner=owner, initial_balance=0.0,
                monthly_deposit=monthly, annual_return_rate=ret, changes_schedule=changes
            ))
        self.vm.project_data["investment_accounts"] = accounts
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        self.table.setRowCount(0)
        for inv in self.vm.project_data.get("investment_accounts", []):
            row = self.table.rowCount()
            self.table.insertRow(row)

            combo_type = QComboBox(); combo_type.addItems(["nisa", "ideco", "taxable_investment", "cash"])
            combo_type.setCurrentText(inv.account_type)
            combo_type.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 0, combo_type)

            combo_owner = QComboBox(); combo_owner.addItems(["husband", "wife"])
            combo_owner.setCurrentText(inv.owner)
            combo_owner.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 1, combo_owner)

            spin_monthly = QSpinBox(); spin_monthly.setRange(0, 100)
            spin_monthly.setValue(int(inv.monthly_deposit / 10000.0))
            spin_monthly.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 2, spin_monthly)

            spin_ret = QDoubleSpinBox(); spin_ret.setRange(0.0, 15.0); spin_ret.setValue(inv.annual_return_rate)
            spin_ret.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 3, spin_ret)


# ============================================================
# 4. 自動車計画パネル
# ============================================================
class CarPanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🚗 マイカー買替・維持費設定", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        form = QFormLayout()
        self.txt_type = QLineEdit("軽自動車")
        self.spin_price = QSpinBox(); self.spin_price.setRange(0, 1000); self.spin_price.setValue(200); self.spin_price.setSuffix(" 万円")
        self.spin_cycle = QSpinBox(); self.spin_cycle.setRange(1, 20); self.spin_cycle.setValue(7); self.spin_cycle.setSuffix(" 年")
        self.spin_annual = QSpinBox(); self.spin_annual.setRange(0, 100); self.spin_annual.setValue(35); self.spin_annual.setSuffix(" 万円/年")

        form.addRow("車種:", self.txt_type)
        form.addRow("購入想定価格:", self.spin_price)
        form.addRow("買替サイクル:", self.spin_cycle)
        form.addRow("年間維持費:", self.spin_annual)
        layout.addLayout(form)

        for w in [self.spin_price, self.spin_cycle, self.spin_annual]:
            w.valueChanged.connect(self._schedule_recalc)

        layout.addStretch()

    def _apply_and_recalc(self):
        annual = self.spin_annual.value() * 10000.0
        car = CarPlan(
            car_type=self.txt_type.text(), purchase_price=self.spin_price.value() * 10000.0,
            purchase_year=1, replacement_cycle_years=self.spin_cycle.value(),
            annual_maintenance_cost=annual - 50000.0, annual_insurance_cost=50000.0
        )
        self.vm.project_data["car_plans"] = [car]
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        cars = self.vm.project_data.get("car_plans", [])
        if cars:
            c = cars[0]
            self.txt_type.setText(c.car_type)
            self.spin_price.setValue(int(c.purchase_price / 10000.0))
            self.spin_cycle.setValue(c.replacement_cycle_years)
            self.spin_annual.setValue(int((c.annual_maintenance_cost + c.annual_insurance_cost) / 10000.0))


# ============================================================
# 5. 保険計画パネル
# ============================================================
class InsurancePanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🔔 各種保険契約", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["保険名", "保険タイプ", "年間支払額 (万円)", "保障期間 (年)", "満期返戻金 (万円)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ 保険契約追加", self)
        btn_add.setObjectName("SecondaryButton")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"保険_{row+1}"))

        combo = QComboBox(); combo.addItems(["life", "medical", "fire", "car"])
        combo.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 1, combo)

        spin_prem = QSpinBox(); spin_prem.setRange(0, 100); spin_prem.setValue(12)
        spin_prem.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 2, spin_prem)

        spin_term = QSpinBox(); spin_term.setRange(1, 100); spin_term.setValue(10)
        spin_term.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 3, spin_term)

        spin_mat = QSpinBox(); spin_mat.setRange(0, 1000); spin_mat.setValue(0)
        spin_mat.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 4, spin_mat)

    def _apply_and_recalc(self):
        ins_list = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if not item:
                continue
            name = item.text()
            i_type = self.table.cellWidget(r, 1).currentText()
            prem = self.table.cellWidget(r, 2).value() * 10000.0
            term = self.table.cellWidget(r, 3).value()
            mat = self.table.cellWidget(r, 4).value() * 10000.0
            ins_list.append(InsurancePlan(
                name=name, insurance_type=i_type, annual_premium=prem,
                start_year=0, insurance_term_years=term,
                maturity_year=term if mat > 0 else -1, maturity_payment=mat
            ))
        self.vm.project_data["insurance_plans"] = ins_list
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        self.table.setRowCount(0)
        for ins in self.vm.project_data.get("insurance_plans", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ins.name))

            combo = QComboBox(); combo.addItems(["life", "medical", "fire", "car"])
            combo.setCurrentText(ins.insurance_type)
            combo.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 1, combo)

            spin_prem = QSpinBox(); spin_prem.setRange(0, 100)
            spin_prem.setValue(int(ins.annual_premium / 10000.0))
            spin_prem.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 2, spin_prem)

            spin_term = QSpinBox(); spin_term.setRange(1, 100); spin_term.setValue(ins.insurance_term_years)
            spin_term.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 3, spin_term)

            spin_mat = QSpinBox(); spin_mat.setRange(0, 1000)
            spin_mat.setValue(int(ins.maturity_payment / 10000.0))
            spin_mat.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 4, spin_mat)


# ============================================================
# 6. 教育費プランパネル（新規追加）
# ============================================================
class EducationPanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("📚 教育費プラン", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        desc = QLabel("子供ごとの年間教育費（万円）を設定します。値を変更するとグラフが自動更新されます。", self)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        self.table = QTableWidget(0, 8, self)
        self.table.setHorizontalHeaderLabels([
            "子供名", "誕生(年後)", "保育園", "幼稚園", "小学校", "中学校", "高校", "大学"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ 教育プラン追加", self)
        btn_add.setObjectName("SecondaryButton")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"子供_{row+1}"))

        spin_birth = QSpinBox(); spin_birth.setRange(0, 30); spin_birth.setValue(5)
        spin_birth.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 1, spin_birth)

        defaults = [15, 20, 35, 55, 55, 150]
        for col_idx, default_val in enumerate(defaults, start=2):
            spin = QSpinBox(); spin.setRange(0, 500); spin.setValue(default_val); spin.setSuffix(" 万")
            spin.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, col_idx, spin)

    def _apply_and_recalc(self):
        plans = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if not item:
                continue
            name = item.text()
            birth_offset = self.table.cellWidget(r, 1).value()
            costs = {}
            stage_keys = ["nursery", "kindergarten", "elementary", "junior_high", "high_school", "university"]
            for col_idx, key in enumerate(stage_keys, start=2):
                costs[key] = self.table.cellWidget(r, col_idx).value() * 10000.0
            plans.append(EducationPlan(
                child_name=name, birth_year_offset=birth_offset, stage_costs=costs
            ))
        self.vm.project_data["education_plans"] = plans
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        self.table.setRowCount(0)
        for edu in self.vm.project_data.get("education_plans", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(edu.child_name))

            spin_birth = QSpinBox(); spin_birth.setRange(0, 30); spin_birth.setValue(edu.birth_year_offset)
            spin_birth.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 1, spin_birth)

            stage_keys = ["nursery", "kindergarten", "elementary", "junior_high", "high_school", "university"]
            for col_idx, key in enumerate(stage_keys, start=2):
                spin = QSpinBox(); spin.setRange(0, 500)
                spin.setValue(int(edu.stage_costs.get(key, 0) / 10000.0))
                spin.setSuffix(" 万")
                spin.valueChanged.connect(self._schedule_recalc)
                self.table.setCellWidget(row, col_idx, spin)


# ============================================================
# 7. ライフイベントパネル（新規追加）
# ============================================================
class LifeEventPanel(_BasePanel):
    def __init__(self, main_vm, parent=None):
        super().__init__(main_vm, parent)
        self._init_ui()
        self.vm.project_loaded.connect(self.load_from_vm)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("📅 ライフイベント", self)
        lbl.setObjectName("SectionHeader")
        layout.addWidget(lbl)

        desc = QLabel("結婚・出産・転職・相続などの一時的な収支イベントを登録します。", self)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels([
            "イベント名", "カテゴリ", "発生年 (年後)", "一時支出 (万円)", "一時収入 (万円)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ イベント追加", self)
        btn_add.setObjectName("SecondaryButton")
        btn_add.clicked.connect(self._add_row)
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem("新規イベント"))

        combo_cat = QComboBox()
        combo_cat.addItems(["marriage", "child", "job", "housing", "car", "insurance", "inheritance", "other"])
        combo_cat.currentIndexChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 1, combo_cat)

        spin_year = QSpinBox(); spin_year.setRange(0, 50); spin_year.setValue(5)
        spin_year.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 2, spin_year)

        spin_cost = QSpinBox(); spin_cost.setRange(0, 10000); spin_cost.setValue(0); spin_cost.setSuffix(" 万円")
        spin_cost.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 3, spin_cost)

        spin_income = QSpinBox(); spin_income.setRange(0, 10000); spin_income.setValue(0); spin_income.setSuffix(" 万円")
        spin_income.valueChanged.connect(self._schedule_recalc)
        self.table.setCellWidget(row, 4, spin_income)

    def _apply_and_recalc(self):
        events = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if not item:
                continue
            name = item.text()
            cat = self.table.cellWidget(r, 1).currentText()
            year = self.table.cellWidget(r, 2).value()
            cost = self.table.cellWidget(r, 3).value() * 10000.0
            income = self.table.cellWidget(r, 4).value() * 10000.0
            events.append(LifeEvent(
                event_id=f"event_{r}", name=name, category=cat,
                elapsed_year=year, one_time_cost=cost, one_time_income=income
            ))
        self.vm.project_data["life_events"] = events
        self.vm.trigger_recalculation()

    @Slot()
    def load_from_vm(self):
        self.table.setRowCount(0)
        for ev in self.vm.project_data.get("life_events", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ev.name))

            combo_cat = QComboBox()
            combo_cat.addItems(["marriage", "child", "job", "housing", "car", "insurance", "inheritance", "other"])
            combo_cat.setCurrentText(ev.category)
            combo_cat.currentIndexChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 1, combo_cat)

            spin_year = QSpinBox(); spin_year.setRange(0, 50); spin_year.setValue(ev.elapsed_year)
            spin_year.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 2, spin_year)

            spin_cost = QSpinBox(); spin_cost.setRange(0, 10000)
            spin_cost.setValue(int(ev.one_time_cost / 10000.0)); spin_cost.setSuffix(" 万円")
            spin_cost.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 3, spin_cost)

            spin_income = QSpinBox(); spin_income.setRange(0, 10000)
            spin_income.setValue(int(ev.one_time_income / 10000.0)); spin_income.setSuffix(" 万円")
            spin_income.valueChanged.connect(self._schedule_recalc)
            self.table.setCellWidget(row, 4, spin_income)
