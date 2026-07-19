import sys
from PySide6.QtWidgets import QApplication
from ui.viewmodels.main_vm import MainViewModel
from ui.views.main_window import MainWindow
from core.models import (
    FamilyMember, HousePlan, LoanPlan, InvestmentAccount, 
    CarPlan, InsurancePlan, EducationPlan, LifeEvent
)

def setup_sample_project(vm: MainViewModel):
    """
    指示書で定義された「4人家族ライフプラン」のサンプルシナリオデータを
    初期データとして ViewModel にセットアップします。
    ユーザーがアプリを開いた瞬間にリアルタイム計算とグラフが動作します。
    """
    project_data = vm.project_data

    # メタデータ
    project_data["metadata"] = {
        "name": "4人家族ライフプラン (サンプル)",
        "initial_cash": 1200000.0,  # 初期預貯金（基準）
        "base_living_cost": 1920000.0  # 食費・光熱費等 (月16万 × 12). これに住宅ローン等の別計算が乗ります。
    }

    # 1. 家族構成
    # 夫: 34歳、年収620万、定年65歳
    husband = FamilyMember(
        name="夫 (主世帯主)",
        relation="husband",
        age=34,
        annual_income=6200000.0,
        bonus=0.0,
        retirement_age=65,
        current_occupation="会社員",
        salary_growth_rate=0.0
    )
    
    # 妻: 28歳、年収350万
    # 就業ワークフロー: before_birth 350万, childcare_leave, nursery 57.6万, elementary 96万, junior_high 115.2万
    wife = FamilyMember(
        name="妻 (配偶者)",
        relation="wife",
        age=28,
        annual_income=3500000.0,
        bonus=0.0,
        retirement_age=60,
        current_occupation="会社員",
        salary_growth_rate=0.0,
        income_modifiers={
            "before_birth": 3500000.0,
            "childcare_leave_continuous": True,
            "nursery": 600000.0,
            "elementary": 1200000.0,
            "junior_high": 2200000.0,
            "high_school": 2200000.0
        }
    )
    
    # 子供たち: 5年後・6年後に誕生
    child1 = FamilyMember(name="第一子", relation="child", age=0, birth_year_offset=5)
    child2 = FamilyMember(name="第二子", relation="child", age=0, birth_year_offset=6)
    
    project_data["family_members"] = [husband, wife, child1, child2]

    # 2. 住宅計画
    # 購入価格 3170万円, 埼玉県吉川市栄町
    # 変動金利ローン 40年, 1.68%
    loan = LoanPlan(
        borrowed_amount=31700000.0,
        term_years=40,
        interest_rate=1.68,
        loan_type="variable",
        start_year=0
    )
    house = HousePlan(
        purchase_price=31700000.0,
        location="埼玉県吉川市栄町",
        purchase_year=0,
        loan=loan,
        # 26年後の返済・賃貸化トリガーを付与
        sale_year=26,
        is_rented=False
    )
    project_data["housing_plans"] = [house]

    # 3. 投資計画
    # 夫: NISA月6万（5年後から月10万に変更）、年利4%、現金積立月4万
    # 妻: NISA月3万、年利4%
    nisa_husband = InvestmentAccount(
        account_type="nisa",
        owner="husband",
        initial_balance=0.0,
        monthly_deposit=60000.0,
        annual_return_rate=4.0,
        changes_schedule={5: {"monthly_deposit": 100000.0}}
    )
    cash_husband = InvestmentAccount(
        account_type="cash",
        owner="husband",
        initial_balance=0.0,
        monthly_deposit=40000.0,
        annual_return_rate=0.0
    )
    nisa_wife = InvestmentAccount(
        account_type="nisa",
        owner="wife",
        initial_balance=0.0,
        monthly_deposit=30000.0,
        annual_return_rate=4.0
    )
    project_data["investment_accounts"] = [nisa_husband, cash_husband, nisa_wife]

    # 4. 自動車計画
    # 1年後に購入、軽自動車、年間維持費35万
    car = CarPlan(
        car_type="軽自動車",
        purchase_price=1500000.0, # 購入価格目安
        purchase_year=1,
        replacement_cycle_years=7,
        annual_maintenance_cost=300000.0,
        annual_insurance_cost=50000.0, # 合算で35万
        inspection_cost=100000.0
    )
    project_data["car_plans"] = [car]

    # 5. 教育計画の年代別テンプレート
    # 幼稚園, 保育園, 小学校, 中学校, 高校, 大学の費用
    edu_child1 = EducationPlan(
        child_name="第一子",
        birth_year_offset=5,
        stage_costs={
            "nursery": 150000.0,
            "kindergarten": 200000.0,
            "elementary": 350000.0,
            "junior_high": 550000.0,
            "high_school": 550000.0,
            "university": 1500000.0
        }
    )
    edu_child2 = EducationPlan(
        child_name="第二子",
        birth_year_offset=6,
        stage_costs={
            "nursery": 150000.0,
            "kindergarten": 200000.0,
            "elementary": 350000.0,
            "junior_high": 550000.0,
            "high_school": 550000.0,
            "university": 1500000.0
        }
    )
    project_data["education_plans"] = [edu_child1, edu_child2]

    # 6. その他の標準的なライフイベント（結婚、転職などの参考データ）
    # （必要に応じてユーザーがUIから追加。初期は空か最小限）
    event_marriage = LifeEvent(
        event_id="initial_marriage",
        name="ライフプランシミュレーション開始",
        category="other",
        elapsed_year=0,
        one_time_cost=0.0
    )
    project_data["life_events"] = [event_marriage]


def main():
    app = QApplication(sys.argv)
    
    vm = MainViewModel()
    setup_sample_project(vm)
    
    window = MainWindow(vm)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
