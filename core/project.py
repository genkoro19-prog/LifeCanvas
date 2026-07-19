import json
from typing import Dict, Any, List
from core.models import (
    FamilyMember, LifeEvent, HousePlan, LoanPlan,
    InvestmentAccount, CarPlan, CarLoan, InsurancePlan, EducationPlan
)

class ProjectManager:
    """JSONベースのインポート・エクスポートおよびプロジェクトファイルのセーブ・ロードを管理します。"""

    @staticmethod
    def serialize_project(project_data: Dict[str, Any]) -> Dict[str, Any]:
        """各種データオブジェクトのリストをJSON直列化可能な辞書型に変換します。"""
        serialized = {
            "metadata": project_data.get("metadata", {}),
            "family_members": [],
            "life_events": [],
            "housing_plans": [],
            "investment_accounts": [],
            "car_plans": [],
            "insurance_plans": [],
            "education_plans": []
        }

        # 1. 家族
        for m in project_data.get("family_members", []):
            serialized["family_members"].append({
                "name": m.name,
                "relation": m.relation,
                "age": m.age,
                "annual_income": m.annual_income,
                "bonus": m.bonus,
                "retirement_age": m.retirement_age,
                "pension_start_age": m.pension_start_age,
                "birth_year_offset": m.birth_year_offset,
                "current_occupation": m.current_occupation,
                "salary_growth_rate": m.salary_growth_rate,
                "income_modifiers": m.income_modifiers
            })

        # 2. ライフイベント
        for e in project_data.get("life_events", []):
            serialized["life_events"].append({
                "event_id": e.event_id,
                "name": e.name,
                "category": e.category,
                "elapsed_year": e.elapsed_year,
                "one_time_cost": e.one_time_cost,
                "one_time_income": e.one_time_income,
                "details": e.details,
                "target_member_name": e.target_member_name
            })

        # 3. 住宅
        for h in project_data.get("housing_plans", []):
            loan_data = None
            if h.loan:
                loan_data = {
                    "borrowed_amount": h.loan.borrowed_amount,
                    "term_years": h.loan.term_years,
                    "interest_rate": h.loan.interest_rate,
                    "loan_type": h.loan.loan_type,
                    "start_year": h.loan.start_year,
                    "repayment_method": h.loan.repayment_method,
                    "interest_adjustments": h.loan.interest_adjustments
                }
            serialized["housing_plans"].append({
                "purchase_price": h.purchase_price,
                "location": h.location,
                "purchase_year": h.purchase_year,
                "loan": loan_data,
                "maintenance_cost": h.maintenance_cost,
                "maintenance_cost_cycle_years": h.maintenance_cost_cycle_years,
                "annual_property_tax": h.annual_property_tax,
                "annual_fire_insurance": h.annual_fire_insurance,
                "is_sold": h.is_sold,
                "sale_year": h.sale_year,
                "sale_price": h.sale_price,
                "is_rented": h.is_rented,
                "rental_start_year": h.rental_start_year,
                "annual_net_rental_income": h.annual_net_rental_income
            })

        # 4. 投資
        for inv in project_data.get("investment_accounts", []):
            serialized["investment_accounts"].append({
                "account_type": inv.account_type,
                "owner": inv.owner,
                "initial_balance": inv.initial_balance,
                "monthly_deposit": inv.monthly_deposit,
                "annual_return_rate": inv.annual_return_rate,
                "changes_schedule": inv.changes_schedule
            })

        # 5. 車
        for car in project_data.get("car_plans", []):
            loan_data = None
            if car.loan:
                loan_data = {
                    "borrowed_amount": car.loan.borrowed_amount,
                    "term_years": car.loan.term_years,
                    "interest_rate": car.loan.interest_rate,
                    "start_year": car.loan.start_year
                }
            serialized["car_plans"].append({
                "car_type": car.car_type,
                "purchase_price": car.purchase_price,
                "purchase_year": car.purchase_year,
                "replacement_cycle_years": car.replacement_cycle_years,
                "annual_maintenance_cost": car.annual_maintenance_cost,
                "annual_insurance_cost": car.annual_insurance_cost,
                "inspection_cycle_years": car.inspection_cycle_years,
                "inspection_cost": car.inspection_cost,
                "loan": loan_data
            })

        # 6. 保険
        for ins in project_data.get("insurance_plans", []):
            serialized["insurance_plans"].append({
                "name": ins.name,
                "insurance_type": ins.insurance_type,
                "annual_premium": ins.annual_premium,
                "start_year": ins.start_year,
                "insurance_term_years": ins.insurance_term_years,
                "benefit_amount": ins.benefit_amount,
                "maturity_year": ins.maturity_year,
                "maturity_payment": ins.maturity_payment
            })

        # 7. 教育費
        for edu in project_data.get("education_plans", []):
            serialized["education_plans"].append({
                "child_name": edu.child_name,
                "birth_year_offset": edu.birth_year_offset,
                "stage_costs": edu.stage_costs
            })

        return serialized

    @staticmethod
    def deserialize_project(serialized: Dict[str, Any]) -> Dict[str, Any]:
        """直列化された辞書型から各種モデルオブジェクトを復元します。"""
        project_data = {
            "metadata": serialized.get("metadata", {}),
            "family_members": [],
            "life_events": [],
            "housing_plans": [],
            "investment_accounts": [],
            "car_plans": [],
            "insurance_plans": [],
            "education_plans": []
        }

        # 1. 家族
        for m in serialized.get("family_members", []):
            project_data["family_members"].append(FamilyMember(
                name=m.get("name", "名称未設定"),
                relation=m.get("relation", "other"),
                age=m.get("age", 0),
                annual_income=m.get("annual_income", 0.0),
                bonus=m.get("bonus", 0.0),
                retirement_age=m.get("retirement_age", 65),
                pension_start_age=m.get("pension_start_age", 65),
                birth_year_offset=m.get("birth_year_offset", 0),
                current_occupation=m.get("current_occupation", "会社員"),
                salary_growth_rate=m.get("salary_growth_rate", 0.0),
                income_modifiers=m.get("income_modifiers", {})
            ))

        # 2. ライフイベント
        for e in serialized.get("life_events", []):
            project_data["life_events"].append(LifeEvent(
                event_id=e["event_id"],
                name=e["name"],
                category=e["category"],
                elapsed_year=e["elapsed_year"],
                one_time_cost=e.get("one_time_cost", 0.0),
                one_time_income=e.get("one_time_income", 0.0),
                details=e.get("details", {}),
                target_member_name=e.get("target_member_name")
            ))

        # 3. 住宅
        for h in serialized.get("housing_plans", []):
            loan = None
            if h.get("loan"):
                l = h["loan"]
                raw_adj = l.get("interest_adjustments", {})
                interest_adjustments = {int(k): v for k, v in raw_adj.items()} if isinstance(raw_adj, dict) else {}
                loan = LoanPlan(
                    borrowed_amount=l["borrowed_amount"],
                    term_years=l["term_years"],
                    interest_rate=l["interest_rate"],
                    loan_type=l["loan_type"],
                    start_year=l.get("start_year", 0),
                    repayment_method=l.get("repayment_method", "equal_payment"),
                    interest_adjustments=interest_adjustments
                )
            project_data["housing_plans"].append(HousePlan(
                purchase_price=h["purchase_price"],
                location=h.get("location", ""),
                purchase_year=h["purchase_year"],
                loan=loan,
                maintenance_cost=h.get("maintenance_cost", 1000000.0),
                maintenance_cost_cycle_years=h.get("maintenance_cost_cycle_years", 10),
                annual_property_tax=h.get("annual_property_tax", 120000.0),
                annual_fire_insurance=h.get("annual_fire_insurance", 20000.0),
                is_sold=h.get("is_sold", False),
                sale_year=h.get("sale_year", 26),
                sale_price=h.get("sale_price", 0.0),
                is_rented=h.get("is_rented", False),
                rental_start_year=h.get("rental_start_year", 26),
                annual_net_rental_income=h.get("annual_net_rental_income", 0.0)
            ))

        # 4. 投資
        for inv in serialized.get("investment_accounts", []):
            raw_sched = inv.get("changes_schedule", {})
            changes_schedule = {int(k): v for k, v in raw_sched.items()} if isinstance(raw_sched, dict) else {}
            project_data["investment_accounts"].append(InvestmentAccount(
                account_type=inv["account_type"],
                owner=inv["owner"],
                initial_balance=inv.get("initial_balance", 0.0),
                monthly_deposit=inv["monthly_deposit"],
                annual_return_rate=inv["annual_return_rate"],
                changes_schedule=changes_schedule
            ))

        # 5. 車
        for car in serialized.get("car_plans", []):
            loan = None
            if car.get("loan"):
                l = car["loan"]
                loan = CarLoan(
                    borrowed_amount=l["borrowed_amount"],
                    term_years=l["term_years"],
                    interest_rate=l["interest_rate"],
                    start_year=l.get("start_year", 0)
                )
            project_data["car_plans"].append(CarPlan(
                car_type=car["car_type"],
                purchase_price=car["purchase_price"],
                purchase_year=car["purchase_year"],
                replacement_cycle_years=car.get("replacement_cycle_years", 7),
                annual_maintenance_cost=car.get("annual_maintenance_cost", 150000.0),
                annual_insurance_cost=car.get("annual_insurance_cost", 50000.0),
                inspection_cycle_years=car.get("inspection_cycle_years", 2),
                inspection_cost=car.get("inspection_cost", 100000.0),
                loan=loan
            ))

        # 6. 保険
        for ins in serialized.get("insurance_plans", []):
            project_data["insurance_plans"].append(InsurancePlan(
                name=ins["name"],
                insurance_type=ins["insurance_type"],
                annual_premium=ins["annual_premium"],
                start_year=ins["start_year"],
                insurance_term_years=ins["insurance_term_years"],
                benefit_amount=ins.get("benefit_amount", 0.0),
                maturity_year=ins.get("maturity_year", -1),
                maturity_payment=ins.get("maturity_payment", 0.0)
            ))

        # 7. 教育費
        for edu in serialized.get("education_plans", []):
            project_data["education_plans"].append(EducationPlan(
                child_name=edu["child_name"],
                birth_year_offset=edu["birth_year_offset"],
                stage_costs=edu.get("stage_costs", {})
            ))

        return project_data

    @classmethod
    def save_to_json(cls, filepath: str, project_data: Dict[str, Any]):
        """JSONファイルにセーブします"""
        serialized = cls.serialize_project(project_data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, filepath: str) -> Dict[str, Any]:
        """JSONファイルからロードします"""
        with open(filepath, "r", encoding="utf-8") as f:
            serialized = json.load(f)
        return cls.deserialize_project(serialized)
