from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class LoanPlan:
    """住宅ローンデータモデル"""
    borrowed_amount: float          # 借入金額 (円)
    term_years: int                 # 借入期間 (年)
    interest_rate: float            # 金利 (例: 1.68%)
    loan_type: str                  # ローンタイプ ('variable' 変動, 'fixed' 固定)
    start_year: int = 0             # 返済開始年（経過年数ベース）
    repayment_method: str = "equal_payment" # 返済方式 ('equal_payment' 元利均等, 'equal_principal' 元金均等)
    interest_adjustments: dict = field(default_factory=dict) # 将来の金利シナリオ {経過年数: 新金利} (例: {10: 2.0})

    def get_monthly_payment(self, elapsed_years: int, current_balance: Optional[float] = None) -> float:
        """
        指定された年の毎月の返済額を計算します。
        変動金利や金利変動、残高をもとに再計算に対応します。
        """
        rate = self.interest_rate
        # 金利シナリオの適用
        for yr, val in sorted(self.interest_adjustments.items()):
            if elapsed_years >= yr:
                rate = val
        
        monthly_rate = (rate / 100.0) / 12
        total_months = self.term_years * 12
        months_elapsed = (elapsed_years - self.start_year) * 12
        
        if months_elapsed < 0 or months_elapsed >= total_months:
            return 0.0

        # 残りの返済月数
        remaining_months = total_months - months_elapsed
        
        # 借換や金利更新時に残高から再計算する場合
        if current_balance is not None:
            balance = current_balance
            calc_months = remaining_months
        else:
            # 当初借入額からの元金均等・元利均等計算
            balance = self.borrowed_amount
            calc_months = total_months

        # 簡易的な元利均等の毎月返済額計算
        if monthly_rate == 0:
            return balance / calc_months

        monthly_payment = balance * (monthly_rate * (1 + monthly_rate) ** calc_months) / ((1 + monthly_rate) ** calc_months - 1)
        return monthly_payment


@dataclass
class HousePlan:
    """住宅データモデル"""
    purchase_price: float           # 購入価格 (円)
    location: str = ""              # 立地
    purchase_year: int = 0          # シミュレーション開始から何年目に購入するか
    loan: Optional[LoanPlan] = None # ローン計画
    
    # 維持費・その他
    maintenance_cost_cycle_years: int = 10  # リフォーム/修繕費サイクル（年）
    maintenance_cost: float = 1000000.0     # 修繕費用（サイクルごと）
    annual_property_tax: float = 120000.0   # 年間固定資産税（目安）
    annual_fire_insurance: float = 20000.0  # 年間火災保険料（目安）
    
    # 転居・売却・賃貸運用 (housing_planの要件に対応)
    is_sold: bool = False
    sale_year: int = 26                     # シミュレーション開始から数えて売却する年
    sale_price: float = 0.0                 # 売却価格
    
    is_rented: bool = False                 # 賃貸運用するか
    rental_start_year: int = 26             # 賃貸運用開始年
    annual_net_rental_income: float = 0.0   # 年間純家賃収入 (例: 750,000円)

    # 住宅ローン控除 (住宅ローン減税) の関係
    has_loan_deduction: bool = True
    deduction_rate: float = 0.007           # 現行0.7%
    deduction_limit_years: int = 13         # 控除対象年数（13年）
    max_deduction_limit: float = 210000.0    # 年間最大控除額 (例: 一般住宅なら21万円)

    def get_annual_cost(self, elapsed_years: int, loan_balance: float) -> dict:
        """
        指定された年における住宅関連のコストと、住宅ローン控除の額を計算します。
        """
        costs = {
            "loan_repayment": 0.0,
            "rent": 0.0,
            "maintenance": 0.0,
            "property_tax": 0.0,
            "insurance": 0.0,
            "deduction": 0.0,
            "rental_income": 0.0
        }
        
        # 購入前
        if elapsed_years < self.purchase_year:
            # 購入前は賃貸で家賃が発生している場合はシミュレーションエンジン側で引きます
            return costs

        # 売却後の場合
        if self.is_sold and elapsed_years >= self.sale_year:
            # 住宅をすでに売却した場合、固定資産税や保険料は発生しない
            # 賃貸に移行した場合は、シミュレーション側の家賃支出が別に入ります
            return costs

        # 賃貸運用している場合
        if self.is_rented and elapsed_years >= self.rental_start_year:
            # 自分で住んでいないが、維持費用や固定資産税は発生する
            costs["rental_income"] = self.annual_net_rental_income
            costs["property_tax"] = self.annual_property_tax
            costs["insurance"] = self.annual_fire_insurance
            # ローンが残っているなら返済も続く
            if self.loan and loan_balance > 0:
                monthly = self.loan.get_monthly_payment(elapsed_years, current_balance=loan_balance)
                costs["loan_repayment"] = monthly * 12
            return costs

        # 通常の居住期間中のコスト
        # 1. ローン返済
        if self.loan and elapsed_years >= self.loan.start_year:
            years_in_loan = elapsed_years - self.loan.start_year
            if years_in_loan < self.loan.term_years:
                monthly = self.loan.get_monthly_payment(elapsed_years, current_balance=loan_balance)
                costs["loan_repayment"] = monthly * 12
        
        # 2. 固定資産税 & 保険
        costs["property_tax"] = self.annual_property_tax
        costs["insurance"] = self.annual_fire_insurance

        # 3. 修繕費 (修繕サイクル年での支払)
        years_since_purchase = elapsed_years - self.purchase_year
        if years_since_purchase > 0 and (years_since_purchase % self.maintenance_cost_cycle_years == 0):
            costs["maintenance"] = self.maintenance_cost

        # 4. 住宅ローン控除 (所得税・住民税から戻ってくる)
        if self.has_loan_deduction and self.loan and elapsed_years >= self.loan.start_year:
            years_in_loan = elapsed_years - self.loan.start_year
            if years_in_loan < self.deduction_limit_years and loan_balance > 0:
                # ローン残高の0.7%
                raw_deduction = loan_balance * self.deduction_rate
                costs["deduction"] = min(raw_deduction, self.max_deduction_limit)

        return costs
