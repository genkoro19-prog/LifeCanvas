import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from core.models import (
    FamilyMember, LifeEvent, HousePlan, LoanPlan,
    InvestmentAccount, CarPlan, CarLoan, InsurancePlan, EducationPlan
)

class LifeCanvasDB:
    """SQLite データベース永続化マネージャー"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_tables(self):
        """データベーステーブルの作成（初期マイグレーション）"""
        cursor = self.conn.cursor()
        
        # 1. プロジェクト設定テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        # 2. 家族メンバーテーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            relation TEXT,
            age INTEGER,
            annual_income REAL,
            bonus REAL,
            retirement_age INTEGER,
            pension_start_age INTEGER,
            birth_year_offset INTEGER,
            current_occupation TEXT,
            salary_growth_rate REAL,
            income_modifiers TEXT  -- JSON文字列
        )
        """)

        # 3. ライフイベントテーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS life_events (
            event_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            elapsed_year INTEGER,
            one_time_cost REAL,
            one_time_income REAL,
            details TEXT,          -- JSON文字列
            target_member_name TEXT
        )
        """)

        # 4. 住宅計画テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS housing_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_price REAL,
            location TEXT,
            purchase_year INTEGER,
            loan_borrowed REAL,
            loan_term INTEGER,
            loan_interest REAL,
            loan_type TEXT,
            loan_start INTEGER,
            loan_repayment_method TEXT,
            loan_interest_adjustments TEXT, -- JSON文字列
            maintenance_cost REAL,
            maintenance_cycle INTEGER,
            property_tax REAL,
            fire_insurance REAL,
            is_sold INTEGER,       -- 0: False, 1: True
            sale_year INTEGER,
            sale_price REAL,
            is_rented INTEGER,     -- 0: False, 1: True
            rental_start_year INTEGER,
            annual_net_rental_income REAL
        )
        """)

        # 5. 投資口座テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS investment_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT,
            owner TEXT,
            initial_balance REAL,
            monthly_deposit REAL,
            annual_return_rate REAL,
            changes_schedule TEXT  -- JSON文字列
        )
        """)

        # 6. 自動車計画テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS car_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_type TEXT,
            purchase_price REAL,
            purchase_year INTEGER,
            replacement_cycle_years INTEGER,
            annual_maintenance_cost REAL,
            annual_insurance_cost REAL,
            inspection_cycle_years INTEGER,
            inspection_cost REAL,
            loan_borrowed REAL,
            loan_term INTEGER,
            loan_interest REAL,
            loan_start INTEGER
        )
        """)

        # 7. 保険計画テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_plans (
            name TEXT PRIMARY KEY,
            insurance_type TEXT,
            annual_premium REAL,
            start_year INTEGER,
            insurance_term_years INTEGER,
            benefit_amount REAL,
            maturity_year INTEGER,
            maturity_payment REAL
        )
        """)

        # 8. 教育計画テーブル
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS education_plans (
            child_name TEXT PRIMARY KEY,
            birth_year_offset INTEGER,
            stage_costs TEXT       -- JSON文字列
        )
        """)

        self.conn.commit()

    # --- セーブ＆ロード関数 ---

    def save_project(self, project_data: Dict[str, Any]):
        """プロジェクトデータを一括してデータベースに保存（既存データはクリアして上書き）"""
        cursor = self.conn.cursor()
        
        # トランザクション処理
        try:
            # 既存のテーブルをクリア
            cursor.execute("DELETE FROM project_meta")
            cursor.execute("DELETE FROM family_members")
            cursor.execute("DELETE FROM life_events")
            cursor.execute("DELETE FROM housing_plans")
            cursor.execute("DELETE FROM investment_accounts")
            cursor.execute("DELETE FROM car_plans")
            cursor.execute("DELETE FROM insurance_plans")
            cursor.execute("DELETE FROM education_plans")

            # 1. メタデータ
            metadata = project_data.get("metadata", {})
            for k, v in metadata.items():
                cursor.execute("INSERT INTO project_meta (key, value) VALUES (?, ?)", (k, str(v)))

            # 2. 家族
            for m in project_data.get("family_members", []):
                cursor.execute("""
                INSERT INTO family_members (
                    name, relation, age, annual_income, bonus, retirement_age, 
                    pension_start_age, birth_year_offset, current_occupation, 
                    salary_growth_rate, income_modifiers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    m.name, m.relation, m.age, m.annual_income, m.bonus, m.retirement_age,
                    m.pension_start_age, m.birth_year_offset, m.current_occupation,
                    m.salary_growth_rate, json.dumps(m.income_modifiers)
                ))

            # 3. ライフイベント
            for e in project_data.get("life_events", []):
                cursor.execute("""
                INSERT INTO life_events (
                    event_id, name, category, elapsed_year, one_time_cost, 
                    one_time_income, details, target_member_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e.event_id, e.name, e.category, e.elapsed_year, e.one_time_cost,
                    e.one_time_income, json.dumps(e.details), e.target_member_name
                ))

            # 4. 住宅
            for h in project_data.get("housing_plans", []):
                loan_b = h.loan.borrowed_amount if h.loan else None
                loan_t = h.loan.term_years if h.loan else None
                loan_i = h.loan.interest_rate if h.loan else None
                loan_type = h.loan.loan_type if h.loan else None
                loan_start = h.loan.start_year if h.loan else None
                loan_method = h.loan.repayment_method if h.loan else None
                loan_adj = json.dumps(h.loan.interest_adjustments) if h.loan else "{}"

                cursor.execute("""
                INSERT INTO housing_plans (
                    purchase_price, location, purchase_year, loan_borrowed, loan_term, 
                    loan_interest, loan_type, loan_start, loan_repayment_method, 
                    loan_interest_adjustments, maintenance_cost, maintenance_cycle, 
                    property_tax, fire_insurance, is_sold, sale_year, sale_price, 
                    is_rented, rental_start_year, annual_net_rental_income
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h.purchase_price, h.location, h.purchase_year, loan_b, loan_t,
                    loan_i, loan_type, loan_start, loan_method, loan_adj,
                    h.maintenance_cost, h.maintenance_cost_cycle_years,
                    h.annual_property_tax, h.annual_fire_insurance,
                    1 if h.is_sold else 0, h.sale_year, h.sale_price,
                    1 if h.is_rented else 0, h.rental_start_year, h.annual_net_rental_income
                ))

            # 5. 投資
            for inv in project_data.get("investment_accounts", []):
                cursor.execute("""
                INSERT INTO investment_accounts (
                    account_type, owner, initial_balance, monthly_deposit, 
                    annual_return_rate, changes_schedule
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    inv.account_type, inv.owner, inv.initial_balance, inv.monthly_deposit,
                    inv.annual_return_rate, json.dumps(inv.changes_schedule)
                ))

            # 6. 車
            for car in project_data.get("car_plans", []):
                loan_b = car.loan.borrowed_amount if car.loan else None
                loan_t = car.loan.term_years if car.loan else None
                loan_i = car.loan.interest_rate if car.loan else None
                loan_start = car.loan.start_year if car.loan else None

                cursor.execute("""
                INSERT INTO car_plans (
                    car_type, purchase_price, purchase_year, replacement_cycle_years,
                    annual_maintenance_cost, annual_insurance_cost, inspection_cycle_years,
                    inspection_cost, loan_borrowed, loan_term, loan_interest, loan_start
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    car.car_type, car.purchase_price, car.purchase_year, car.replacement_cycle_years,
                    car.annual_maintenance_cost, car.annual_insurance_cost, car.inspection_cycle_years,
                    car.inspection_cost, loan_b, loan_t, loan_i, loan_start
                ))

            # 7. 保険
            for ins in project_data.get("insurance_plans", []):
                cursor.execute("""
                INSERT INTO insurance_plans (
                    name, insurance_type, annual_premium, start_year, 
                    insurance_term_years, benefit_amount, maturity_year, maturity_payment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ins.name, ins.insurance_type, ins.annual_premium, ins.start_year,
                    ins.insurance_term_years, ins.benefit_amount, ins.maturity_year, ins.maturity_payment
                ))

            # 8. 教育費
            for edu in project_data.get("education_plans", []):
                cursor.execute("""
                INSERT INTO education_plans (
                    child_name, birth_year_offset, stage_costs
                ) VALUES (?, ?, ?)
                """, (
                    edu.child_name, edu.birth_year_offset, json.dumps(edu.stage_costs)
                ))

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def load_project(self) -> Dict[str, Any]:
        """データベースから全設定データを読み込み、モデルオブジェクトとして復元します。"""
        cursor = self.conn.cursor()
        project_data = {
            "metadata": {},
            "family_members": [],
            "life_events": [],
            "housing_plans": [],
            "investment_accounts": [],
            "car_plans": [],
            "insurance_plans": [],
            "education_plans": []
        }

        # 1. メタデータ
        cursor.execute("SELECT key, value FROM project_meta")
        for row in cursor.fetchall():
            project_data["metadata"][row["key"]] = row["value"]

        # 2. 家族
        cursor.execute("SELECT * FROM family_members")
        for row in cursor.fetchall():
            member = FamilyMember(
                name=row["name"],
                relation=row["relation"],
                age=row["age"],
                annual_income=row["annual_income"],
                bonus=row["bonus"],
                retirement_age=row["retirement_age"],
                pension_start_age=row["pension_start_age"],
                birth_year_offset=row["birth_year_offset"],
                current_occupation=row["current_occupation"],
                salary_growth_rate=row["salary_growth_rate"],
                income_modifiers=json.loads(row["income_modifiers"] or "{}")
            )
            project_data["family_members"].append(member)

        # 3. ライフイベント
        cursor.execute("SELECT * FROM life_events")
        for row in cursor.fetchall():
            event = LifeEvent(
                event_id=row["event_id"],
                name=row["name"],
                category=row["category"],
                elapsed_year=row["elapsed_year"],
                one_time_cost=row["one_time_cost"],
                one_time_income=row["one_time_income"],
                details=json.loads(row["details"] or "{}"),
                target_member_name=row["target_member_name"]
            )
            project_data["life_events"].append(event)

        # 4. 住宅
        cursor.execute("SELECT * FROM housing_plans")
        for row in cursor.fetchall():
            loan = None
            if row["loan_borrowed"] is not None:
                loan = LoanPlan(
                    borrowed_amount=row["loan_borrowed"],
                    term_years=row["loan_term"],
                    interest_rate=row["loan_interest"],
                    loan_type=row["loan_type"],
                    start_year=row["loan_start"] or 0,
                    repayment_method=row["loan_repayment_method"] or "equal_payment",
                    interest_adjustments=json.loads(row["loan_interest_adjustments"] or "{}")
                )
            
            h = HousePlan(
                purchase_price=row["purchase_price"],
                location=row["location"],
                purchase_year=row["purchase_year"],
                loan=loan,
                maintenance_cost=row["maintenance_cost"],
                maintenance_cost_cycle_years=row["maintenance_cycle"],
                annual_property_tax=row["property_tax"],
                annual_fire_insurance=row["fire_insurance"],
                is_sold=True if row["is_sold"] == 1 else False,
                sale_year=row["sale_year"],
                sale_price=row["sale_price"],
                is_rented=True if row["is_rented"] == 1 else False,
                rental_start_year=row["rental_start_year"],
                annual_net_rental_income=row["annual_net_rental_income"]
            )
            project_data["housing_plans"].append(h)

        # 5. 投資
        cursor.execute("SELECT * FROM investment_accounts")
        for row in cursor.fetchall():
            inv = InvestmentAccount(
                account_type=row["account_type"],
                owner=row["owner"],
                initial_balance=row["initial_balance"],
                monthly_deposit=row["monthly_deposit"],
                annual_return_rate=row["annual_return_rate"],
                changes_schedule=json.loads(row["changes_schedule"] or "{}")
            )
            project_data["investment_accounts"].append(inv)

        # 6. 車
        cursor.execute("SELECT * FROM car_plans")
        for row in cursor.fetchall():
            loan = None
            if row["loan_borrowed"] is not None:
                loan = CarLoan(
                    borrowed_amount=row["loan_borrowed"],
                    term_years=row["loan_term"],
                    interest_rate=row["loan_interest"],
                    start_year=row["loan_start"] or 0
                )
            car = CarPlan(
                car_type=row["car_type"],
                purchase_price=row["purchase_price"],
                purchase_year=row["purchase_year"],
                replacement_cycle_years=row["replacement_cycle_years"],
                annual_maintenance_cost=row["annual_maintenance_cost"],
                annual_insurance_cost=row["annual_insurance_cost"],
                inspection_cycle_years=row["inspection_cycle_years"],
                inspection_cost=row["inspection_cost"],
                loan=loan
            )
            project_data["car_plans"].append(car)

        # 7. 保険
        cursor.execute("SELECT * FROM insurance_plans")
        for row in cursor.fetchall():
            ins = InsurancePlan(
                name=row["name"],
                insurance_type=row["insurance_type"],
                annual_premium=row["annual_premium"],
                start_year=row["start_year"],
                insurance_term_years=row["insurance_term_years"],
                benefit_amount=row["benefit_amount"],
                maturity_year=row["maturity_year"],
                maturity_payment=row["maturity_payment"]
            )
            project_data["insurance_plans"].append(ins)

        # 8. 教育費
        cursor.execute("SELECT * FROM education_plans")
        for row in cursor.fetchall():
            edu = EducationPlan(
                child_name=row["child_name"],
                birth_year_offset=row["birth_year_offset"],
                stage_costs=json.loads(row["stage_costs"] or "{}")
            )
            project_data["education_plans"].append(edu)

        return project_data
