import pytest
from core.models import (
    FamilyMember, LifeEvent, HousePlan, LoanPlan,
    InvestmentAccount, CarPlan, CarLoan, InsurancePlan, EducationPlan
)
from core.engine import SimulationEngine
from core.calculator.tax import TaxCalculator
from core.calculator.loan import LoanCalculator

def test_tax_calculator():
    # 簡易手取り計算のテスト
    res = TaxCalculator.get_net_income(6200000.0, is_employee=True)
    assert res["net_income"] > 0
    assert res["social_insurance"] > 0
    assert res["income_tax"] > 0
    assert res["inhabitants_tax"] > 0
    
    # 住宅ローン控除が適用されるかのテスト
    res_deduction = TaxCalculator.get_net_income(6200000.0, is_employee=True, housing_deduction=210000.0)
    # 控除なしより手取りが増えていること
    assert res_deduction["net_income"] > res["net_income"]


def test_loan_calculator():
    # ローン返済のテスト
    schedule = LoanCalculator.calculate_amortization_schedule(
        principal=30000000.0,
        term_years=35,
        interest_rate=1.5,
        repayment_method="equal_payment"
    )
    assert len(schedule) == 35
    assert schedule[-1]["end_balance"] == 0.0
    # 毎年の支払額が妥当か
    assert schedule[0]["principal_paid"] > 0
    assert schedule[0]["interest_paid"] > 0


def test_simulation_engine_run():
    # サンプルプロジェクトに近い最小限データでのシミュレーション実行テスト
    project_data = {
        "metadata": {
            "initial_cash": 1000000.0,
            "base_living_cost": 2400000.0
        },
        "family_members": [
            FamilyMember(name="夫", relation="husband", age=34, annual_income=6200000.0),
            FamilyMember(name="妻", relation="wife", age=28, annual_income=3500000.0)
        ],
        "housing_plans": [
            HousePlan(
                purchase_price=31700000.0,
                purchase_year=0,
                loan=LoanPlan(
                    borrowed_amount=31700000.0,
                    term_years=40,
                    interest_rate=1.68,
                    loan_type="variable"
                )
            )
        ],
        "investment_accounts": [
            InvestmentAccount(account_type="nisa", owner="husband", initial_balance=0.0, monthly_deposit=60000.0, annual_return_rate=4.0)
        ],
        "car_plans": [],
        "insurance_plans": [],
        "education_plans": []
    }

    engine = SimulationEngine(project_data)
    results = engine.run()

    assert len(results) == 40  # デフォルト40年間分
    assert results[0]["husband_age"] == 34
    assert results[0]["wife_age"] == 28
    
    # 収支・現金・純資産などの確認
    assert "cash_balance" in results[0]
    assert "net_worth" in results[0]
    # NISA運用残高が年々上がっているか
    assert results[1]["investment_balance"] >= results[0]["investment_balance"]
