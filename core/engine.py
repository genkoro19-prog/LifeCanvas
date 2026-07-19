from typing import Dict, Any, List
from core.models import Family, FamilyMember, LifeEvent, HousePlan, InvestmentAccount, CarPlan, InsurancePlan, EducationPlan
from core.calculator.tax import TaxCalculator
from core.calculator.loan import LoanCalculator
from core.system_master import SystemMaster

class SimulationEngine:
    """LifeCanvas の中核シミュレーションエンジン"""
    
    def __init__(self, project_data: Dict[str, Any]):
        self.project_data = project_data
        self.years = 40  # デフォルトのシミュレーション期間 (40年間)
        
    def run(self) -> List[Dict[str, Any]]:
        """
        40年間の期別キャッシュフローシミュレーションを実行します。
        """
        # アセットの抽出
        family_members: List[FamilyMember] = self.project_data.get("family_members", [])
        life_events: List[LifeEvent] = self.project_data.get("life_events", [])
        housing_plans: List[HousePlan] = self.project_data.get("housing_plans", [])
        investment_accounts: List[InvestmentAccount] = self.project_data.get("investment_accounts", [])
        car_plans: List[CarPlan] = self.project_data.get("car_plans", [])
        insurance_plans: List[InsurancePlan] = self.project_data.get("insurance_plans", [])
        education_plans: List[EducationPlan] = self.project_data.get("education_plans", [])

        # シミュレーション初期状態
        # サンプル初期現金などの設定をメタデータから、なければ0で初期化
        meta = self.project_data.get("metadata", {})
        cash_balance = float(meta.get("initial_cash", 1000000.0))  # 初期手元現金（デフォルト100万）
        
        # 投資口座の現在額。初期値は InvestmentAccount の initial_balance とする
        investments_state = {}
        investments_principal = {} # 累積元本トラッキング用
        for idx, inv in enumerate(investment_accounts):
            investments_state[idx] = inv.initial_balance
            investments_principal[idx] = inv.initial_balance

        # 夫婦・子供の取得
        husband = next((m for m in family_members if m.relation == "husband"), None)
        wife = next((m for m in family_members if m.relation == "wife"), None)
        children = [m for m in family_members if m.relation == "child"]

        # ローン残高の管理
        # 住宅ローン残高初期化
        house_loans_balance = {}
        for idx, h in enumerate(housing_plans):
            if h.loan:
                house_loans_balance[idx] = h.loan.borrowed_amount

        # 基本生活費の定義（デフォルト240万円、家族の人数で動的変化）
        base_living_cost = float(meta.get("base_living_cost", 2400000.0))

        # 記録用辞書の初期化（各年でリセット）
        results = []

        # シミュレーション開始月（デフォルト1月）
        start_month = int(meta.get("start_month", 1))

        # シミュレーションループ（毎年計算）
        global_state = {}
        for year in range(self.years):
            
            months_in_year = (12 - start_month + 1) if year == 0 else 12
            month_ratio = months_in_year / 12.0
            
            year_data = {"year": year, "system_events": []}
            system_events = year_data["system_events"]

            # --- Phase 1: イベントドリブンな状態上書き ---
            for e in life_events:
                if e.elapsed_year == year:
                    global_state = e.apply_to_state(global_state)

            # 家族年齢の記録
            if husband:
                year_data["husband_age"] = husband.age + year
            if wife:
                year_data["wife_age"] = wife.age + year
                
            child_docs = []
            prefix_names = ["第一子", "第二子", "第三子", "第四子", "第五子"]
            for i, child in enumerate(children):
                age_offset = year - child.birth_year_offset
                if age_offset >= 0:
                    prefix = prefix_names[i] if i < len(prefix_names) else f"第{i+1}子"
                    child_docs.append(f"{prefix} {age_offset}歳")
            year_data["children_ages"] = child_docs

            # 1. 収入
            # 家族状態辞書の構成（妻の動的就業ワークフロー判定で必要）
            family_state = {
                "children": children,
                "husband": husband,
                "wife": wife
            }

            h_income = husband.get_income_for_simulation_year(year, family_state) if husband else 0.0
            w_income = wife.get_income_for_simulation_year(year, family_state) if wife else 0.0
            
            # イベントによる給与の上書きがあれば適用
            overrides = global_state.get("salary_overrides", {})
            if "husband" in overrides:
                h_income = overrides["husband"]
            if "wife" in overrides:
                w_income = overrides["wife"]
                
            # 定年チェック: 特別な継続雇用イベントがない限り、定年を超えたら強制0
            if husband and (husband.age + year) >= husband.retirement_age:
                h_income = 0.0
            if wife and (wife.age + year) >= wife.retirement_age:
                w_income = 0.0
                
            # --- 収入の変動（働き方変更・退職等）を自動検知して年表イベント化 ---
            if year > 0:
                prev_w = global_state.get("prev_w_income")
                if prev_w is not None and prev_w != w_income:
                    if w_income == 0.0 and wife and (wife.age + year) >= wife.retirement_age:
                        system_events.append(f"【ライフ】妻 {wife.retirement_age}歳退職 (給与終了)")
                    elif prev_w == 0.0 and w_income > 0:
                        system_events.append(f"【就業】妻 育休等から職場復帰 (年収{w_income/10000:.0f}万円)")
                    else:
                        direction = "増加" if w_income > prev_w else "減少"
                        system_events.append(f"【就業】妻 働き方変更・収入{direction} ({prev_w/10000:.0f}万→{w_income/10000:.0f}万)")
                        
                prev_h = global_state.get("prev_h_income")
                if prev_h is not None and prev_h != h_income:
                    if h_income == 0.0 and husband and (husband.age + year) >= husband.retirement_age:
                        system_events.append(f"【ライフ】夫 {husband.retirement_age}歳退職 (給与終了)")
                    else:
                        direction = "増加" if h_income > prev_h else "減少"
                        system_events.append(f"【就業】夫 働き方変更・収入{direction} ({prev_h/10000:.0f}万→{h_income/10000:.0f}万)")
                        
            global_state["prev_w_income"] = w_income
            global_state["prev_h_income"] = h_income
            
            # 年金受給 (規定の年齢以上なら支給)
            h_pension = 0.0
            if husband and (husband.age + year) >= husband.pension_start_age:
                # 会社員の場合、平均的な厚生年金約 180万円/年と仮定
                h_pension = 1800000.0 if husband.current_occupation == "会社員" else 780000.0
            w_pension = 0.0
            if wife and (wife.age + year) >= wife.pension_start_age:
                # 妻の平均厚生年金（あるいは国民年金）120万円/年と仮定
                w_pension = 1200000.0 if wife.current_occupation == "会社員" else 780000.0

            # 2. 住宅ローン控除の仮計算（所得税手取り計算用）
            # 住宅ローン残高の合計に対する控除額を取得
            total_housing_deduction = 0.0
            sys_master = SystemMaster.get_instance()
            for idx, h in enumerate(housing_plans):
                balance = house_loans_balance.get(idx, 0.0)
                # 控除対象年数以内かどうかの判定 (簡略化で h.deduction_limit_years を使用)
                years_in_loan = year - h.loan.start_year if h.loan else 0
                if h.has_loan_deduction and h.loan and 0 <= years_in_loan < h.deduction_limit_years and balance > 0:
                    house_type = getattr(h, "house_type", "new")
                    rate = sys_master.config["housing_loan_deduction"]["rate"]
                    max_limit = sys_master.get_housing_loan_deduction_limit(house_type)
                    
                    raw_ded = balance * rate
                    total_housing_deduction += min(raw_ded, max_limit)

            # 所得税・住民税・社会保険料および手取り計算
            h_tax_data = TaxCalculator.get_net_income(h_income, is_employee=(husband.current_occupation == "会社員" if husband else True), housing_deduction=total_housing_deduction)
            w_tax_data = TaxCalculator.get_net_income(w_income, is_employee=(wife.current_occupation == "会社員" if wife else True), housing_deduction=0.0)

            # 月割り調整（基本収入）
            h_income *= month_ratio
            w_income *= month_ratio
            h_pension *= month_ratio
            w_pension *= month_ratio
            h_tax_data["net_income"] *= month_ratio
            w_tax_data["net_income"] *= month_ratio

            total_salary_income = h_income + w_income
            total_net_income = h_tax_data["net_income"] + w_tax_data["net_income"] + h_pension + w_pension

            # --- 3. 各種給付金 (SystemMaster 使用) ---
            sys_master = SystemMaster.get_instance()
            benefits = 0.0
            wife_benefit = 0.0
            husband_benefit = 0.0
            
            # イベント経由での給付金上書き（育児休業給付金など）
            benefit_overrides = global_state.get("benefit_overrides", {})
            if "wife" in benefit_overrides:
                wife_benefit += benefit_overrides["wife"]
            if "husband" in benefit_overrides:
                husband_benefit += benefit_overrides["husband"]
            benefits += wife_benefit + husband_benefit
                
            # 児童手当の加算 (マスター設定から動的に取得)
            for child in children:
                child_age = year - child.birth_year_offset
                if child_age == 0:
                    system_events.append(f"【制度】{child.name}誕生 / 児童手当開始")
                elif child_age == 3:
                    system_events.append(f"【制度】{child.name} 児童手当 減額(3歳〜)")
                elif child_age == 18:
                    system_events.append(f"【制度】{child.name} 児童手当 終了(18歳)")
                elif child_age == 22:
                    system_events.append(f"【ライフ】{child.name} 大学卒業・自立")

                if child_age >= 0:
                    benefits += sys_master.get_child_allowance_monthly(child_age) * 12
                    
            # 給付金の月割り
            wife_benefit *= month_ratio
            husband_benefit *= month_ratio
            benefits *= month_ratio

            # 4. 生活費
            # 家族人数（夫婦＋同居している子供＝18歳未満）
            living_persons = 2 if (husband and wife) else 1
            for child in children:
                child_age = year - child.birth_year_offset
                if 0 <= child_age < 22: # 22歳（大学卒業）までは同居と仮定
                    living_persons += 1
            
            # 生活費算出: 基本生活費 + 子供1人につき36万円加算 (月3万)
            num_kids = max(0, living_persons - 2)
            living_cost = (base_living_cost + (num_kids * 360000.0)) * month_ratio

            # 5. 教育費
            education_cost = 0.0
            education_breakdown = {}
            for edu in education_plans:
                cost = edu.get_annual_cost(year) * month_ratio
                education_cost += cost
                if cost > 0:
                    education_breakdown[edu.child_name] = cost

            # 6. 住宅関連費用
            housing_cost = 0.0
            housing_breakdown = {"loan": 0.0, "property_tax": 0.0, "insurance": 0.0, "maintenance": 0.0, "renovation": 0.0, "moving_cost": 0.0, "rent_paid": 0.0}
            rental_income = 0.0
            
            # ライフプラン変更: 返済・売却・賃貸化トリガー
            for idx, h in enumerate(housing_plans):
                # 従来の設定(sale_year) または イベントによるトリガー
                housing_commands = global_state.get("housing_commands", {})
                is_trigger_year = (year == h.sale_year)
                
                # イベントドリブンによる発火（この年に初めてコマンドが届いた場合）
                if idx in housing_commands and not h.is_sold and not h.is_rented:
                    cmd = housing_commands[idx]
                    if cmd == "sell_and_rent":
                        is_trigger_year = True

                if is_trigger_year:
                    # サンプルプロジェクト: 住宅プラン変更: 繰上完済、駅チカ転居、旧宅を賃貸にして年間75万円の収益
                    # 繰上返済として残高を一括償還
                    if h.loan and house_loans_balance.get(idx, 0.0) > 0:
                        repay_amount = house_loans_balance[idx]
                        housing_cost += repay_amount  # キャッシュアウト
                        house_loans_balance[idx] = 0.0 # ローン完済
                        
                    # 賃貸設定を有効化
                    h.is_rented = True
                    h.rental_start_year = year
                    h.annual_net_rental_income = 750000.0  # サンプルデータに基づく
                    
                    # 転居に伴う引っ越し・初期費用
                    moving_expense = 1000000.0
                    housing_cost += moving_expense
                    housing_breakdown["moving_cost"] += moving_expense
                    system_events.append("【住居】駅チカ転居（引っ越し・初期費用 100万円）")

            # 住宅計画ごとの集計
            for idx, h in enumerate(housing_plans):
                balance = house_loans_balance.get(idx, 0.0)
                h_costs = h.get_annual_cost(year, balance)
                
                # キャッシュフロー上の支出を加算
                housing_cost += h_costs["loan_repayment"] + h_costs["property_tax"] + h_costs["insurance"] + h_costs["maintenance"]
                housing_breakdown["loan"] += h_costs["loan_repayment"]
                housing_breakdown["property_tax"] += h_costs["property_tax"]
                housing_breakdown["insurance"] += h_costs["insurance"]
                housing_breakdown["maintenance"] += h_costs["maintenance"]
                
                rental_income += h_costs["rental_income"]
                
                # 新居の家賃（旧居を賃貸に出している＝自分たちは別の賃貸に住んでいると仮定）
                if h.is_rented and year >= h.rental_start_year:
                    new_rent_annual = 1800000.0 # 月15万
                    housing_cost += new_rent_annual
                    housing_breakdown["rent_paid"] += new_rent_annual
                
                # 税金の還付としてのローン控除適用
                # ここでは税金控除による実質所得増として相殺
                total_net_income += h_costs["deduction"]

                # ローン残高の更新（支払われた元金分を引く）
                if h.loan and year >= h.loan.start_year and balance > 0:
                    years_in_loan = year - h.loan.start_year
                    if years_in_loan < h.loan.term_years:
                        # 毎年のローン返済詳細から、支払元金を取得
                        # 年間支払元金額を算出
                        schedule = LoanCalculator.calculate_amortization_schedule(
                            principal=h.loan.borrowed_amount,
                            term_years=h.loan.term_years,
                            interest_rate=h.loan.interest_rate,
                            loan_type=h.loan.loan_type,
                            repayment_method=h.loan.repayment_method,
                            start_year=h.loan.start_year
                        )
                        # 当該年の支払元金を引く
                        for step in schedule:
                            if step["year"] == year:
                                house_loans_balance[idx] = max(0.0, balance - step["principal_paid"])
                                break
                    
                    # 駅チカ転居による新規家賃（生活費等へ加算するか、住宅コストへ加算するか？）
                    # サンプルでは「年間賃貸利益75万円」として算出されているため、純増にする

            # 7. 車
            car_cost = 0.0
            car_breakdown = {"purchase": 0.0, "loan": 0.0, "maintenance": 0.0, "inspection": 0.0, "insurance": 0.0}
            for car in car_plans:
                c_costs = car.get_annual_cost(year)
                car_cost += c_costs["purchase"] + c_costs["maintenance"] + c_costs["insurance"] + c_costs["inspection"] + c_costs["loan_repayment"]
                car_breakdown["purchase"] += c_costs["purchase"]
                car_breakdown["loan"] += c_costs["loan_repayment"]
                car_breakdown["maintenance"] += c_costs["maintenance"]
                car_breakdown["inspection"] += c_costs["inspection"]
                car_breakdown["insurance"] += c_costs["insurance"]

            # 8. 保険
            insurance_cost = 0.0
            insurance_income = 0.0
            for ins in insurance_plans:
                insurance_cost += ins.get_annual_cost(year)
                insurance_income += ins.get_maturity_payout(year)
                
            housing_cost *= month_ratio
            car_cost *= month_ratio
            insurance_cost *= month_ratio
            rental_income *= month_ratio

            # 9. 現金計算（キャッシュフロー総括・投資前）
            # 流入
            inflow = total_net_income + benefits + rental_income + insurance_income
            # 流出
            outflow = living_cost + education_cost + housing_cost + car_cost + insurance_cost
            
            # 通常収支 (ordinary cash flow)
            net_cash_flow = inflow - outflow
            
            # 10. 投資のシミュレーション（積立＋売却・簿価管理）
            investment_deposit = 0.0
            investment_growth = 0.0
            investment_sold = 0.0
            
            cash_balance += net_cash_flow # まず通常収支を現金に反映
            
            inv_overrides = global_state.get("investment_overrides", {})
            sys_master = SystemMaster.get_instance()
            
            # 10-1. 投資の「積立」フェーズ
            for idx, inv in enumerate(investment_accounts):
                current_bal = investments_state.get(idx, 0.0)
                current_principal = investments_principal.get(idx, 0.0)
                
                target_key = f"{inv.account_type}_{inv.owner}"
                
                # スケジュールからの当年の予定積立額を取得
                actual_monthly_dep = inv.get_monthly_deposit(year)
                
                if target_key in inv_overrides:
                    actual_monthly_dep = inv_overrides[target_key]
                
                # --- SystemMaster: NISAの生涯投資枠トラッキング ---
                if inv.account_type == "nisa":
                    limit = sys_master.get_nisa_limit()
                    annual_dep = actual_monthly_dep * 12
                    
                    if current_principal >= limit:
                        actual_monthly_dep = 0.0
                    elif current_principal + annual_dep > limit:
                        allowed_annual = max(0, limit - current_principal)
                        actual_monthly_dep = allowed_annual / 12.0
                        
                    if actual_monthly_dep > 0 and (current_principal + actual_monthly_dep * 12) >= limit:
                        role_name = "夫" if inv.owner == "husband" else "妻"
                        system_events.append(f"【資産】{role_name} NISA生涯投資枠({limit/10000:.0f}万)到達・積立停止")
                
                # 積立可能額のチェック（現預金不足なら減額・停止）
                desired_annual_dep = actual_monthly_dep * months_in_year
                if desired_annual_dep > 0:
                    if cash_balance >= desired_annual_dep:
                        cash_balance -= desired_annual_dep
                        deposited = desired_annual_dep
                    elif cash_balance > 0:
                        # 全額は無理だが現金残高の分だけ積立
                        deposited = cash_balance
                        cash_balance = 0.0
                        system_events.append("【自動対応】手元現金不足のため投資等積立を減額")
                        actual_monthly_dep = (deposited / months_in_year) if months_in_year > 0 else 0
                    else:
                        deposited = 0.0
                        actual_monthly_dep = 0.0
                        if inv.get_monthly_deposit(year) > 0: # 元々は積立予定だった
                            system_events.append("【自動対応】手元現金枯渇のため投資等積立を停止")
                else:
                    deposited = 0.0
                
                # 運用計算
                sim_res = inv.simulate_year(year, current_bal, months_in_year, override_monthly_dep=actual_monthly_dep)
                investments_state[idx] = sim_res["end_balance"]
                investments_principal[idx] += sim_res["deposited"]
                investment_deposit += sim_res["deposited"]
                investment_growth += sim_res["interest"]

            # 10-2. 投資の「売却（取り崩し）」フェーズ
            if cash_balance < 0:
                shortfall = -cash_balance
                sold_total = 0.0
                for idx in investments_state:
                    if shortfall <= 0: break
                    available = investments_state[idx]
                    if available > 0:
                        sell = min(available, shortfall)
                        investments_state[idx] -= sell
                        
                        # 簿価も「売却価額の割合」に応じて減らす (売却による枠復活対応)
                        if available > 0:
                            principal_ratio = investments_principal.get(idx, 0.0) / available
                        else:
                            principal_ratio = 1.0
                        sold_principal = sell * principal_ratio
                        investments_principal[idx] = max(0.0, investments_principal.get(idx, 0.0) - sold_principal)
                        
                        shortfall -= sell
                        sold_total += sell
                        cash_balance += sell # 現金に補填
                        
                investment_sold = sold_total
                if investment_sold > 0:
                    system_events.append(f"【制度】資金不足のため投資・NISA等を {investment_sold/10000:.0f}万円 売却 (現預金へ補填)")
                    
                if cash_balance < 0:
                    system_events.append(f"【警告!!】資金ショート判定({-cash_balance/10000:.0f}万不足)")

            # 11. 純資産
            # 純資産 = 現金残高 ＋ 投資残高 ＋ 不動産評価額(簡易化して購入額の50%など、または購入額維持) - ローン残高
            total_investments = sum(investments_state.values())
            total_loans = sum(house_loans_balance.values())
            
            # 不動産評価額 (簡易的に購入額、または経年劣化)
            property_value = sum(h.purchase_price for h in housing_plans if not h.is_sold)
            
            net_worth = cash_balance + total_investments + property_value - total_loans

            # イベントによる一時的の割り込み処理（ライフイベントの one_time_cost と one_time_income）
            event_cost_total = 0.0
            event_income_total = 0.0
            event_names = []
            for e in life_events:
                e_res = e.process_event(year)
                if e_res:
                    event_income_total += e_res["income"]
                    event_cost_total += e_res["cost"]
                    cash_balance += e_res["income"]
                    cash_balance -= e_res["cost"]
                    if e_res["cost"] > 0 or e_res["income"] > 0:
                        event_names.append(e.name)

            # 記録
            year_data.update({
                "inflow": inflow,
                "outflow": outflow,
                "net_cash_flow": net_cash_flow,
                # --- 詳細項目 (フラット) ---
                "husband_gross_income": h_income,
                "husband_net_income": h_tax_data["net_income"],
                "husband_pension": h_pension,
                "husband_benefit": husband_benefit,
                "wife_gross_income": w_income,
                "wife_net_income": w_tax_data["net_income"],
                "wife_pension": w_pension,
                "wife_benefit": wife_benefit,
                "benefits": benefits,
                "living_cost": living_cost,
                "education_cost": education_cost,
                "housing_cost": housing_cost,
                "housing_loan_deduction": total_housing_deduction,
                "rental_income": rental_income,
                "car_cost": car_cost,
                "insurance_cost": insurance_cost,
                "investment_deposit": investment_deposit,
                "investment_growth": investment_growth,
                "investment_sold": investment_sold,
                "event_cost": event_cost_total,
                "event_income": event_income_total,
                "event_names": event_names,
                # --- 残高 ---
                "cash_balance": cash_balance,
                "investment_balance": total_investments,
                "loan_balance": total_loans,
                "net_worth": net_worth,
                # --- 内訳辞書 (詳細ダイアログ用) ---
                "h_tax_data": h_tax_data,
                "w_tax_data": w_tax_data,
                "housing_breakdown": housing_breakdown,
                "car_breakdown": car_breakdown,
                "education_breakdown": education_breakdown
            })
            
            results.append(year_data)

        return results
