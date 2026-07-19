from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CarLoan:
    """マイカーローンデータモデル"""
    borrowed_amount: float
    term_years: int
    interest_rate: float
    start_year: int = 0

    def get_annual_repayment(self, elapsed_years: int) -> float:
        """指定した年の年間返済額を算出します。"""
        years_in_loan = elapsed_years - self.start_year
        if 0 <= years_in_loan < self.term_years:
            # 簡易金利計算 (元利均等)
            rate = self.interest_rate / 100.0
            if rate == 0:
                return self.borrowed_amount / self.term_years
            # 年間返済額
            r = rate
            n = self.term_years
            annual_payment = self.borrowed_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
            return annual_payment
        return 0.0


@dataclass
class CarPlan:
    """自動車プランデータモデル"""
    car_type: str                   # 軽自動車、普通車、ミニバンなど
    purchase_price: float           # 車両購入価格 (円)
    purchase_year: int              # 初回購入年（シミュレーション開始から何年目か）
    replacement_cycle_years: int = 7 # 買い替えサイクル (例: 7年)
    
    # 維持費関連（年間）
    annual_maintenance_cost: float = 150000.0  # ガソリン、税金、消耗品など
    annual_insurance_cost: float = 50000.0      # 任意保険料
    inspection_cycle_years: int = 2          # 車検サイクル (通常2年ごと)
    inspection_cost: float = 100000.0         # 各車検の費用
    
    # ローン設定 (オプション)
    loan: Optional[CarLoan] = None

    def get_annual_cost(self, elapsed_years: int) -> dict:
        """指定された年における自動車関連コストを算出します。"""
        costs = {
            "purchase": 0.0,
            "maintenance": 0.0,
            "insurance": 0.0,
            "inspection": 0.0,
            "loan_repayment": 0.0
        }

        # シミュレーション年において車を所有しているかを判定
        # 初回購入年以降に所有
        if elapsed_years < self.purchase_year:
            return costs

        # 1. 買い替え/新規購入費用
        years_since_first_purchase = elapsed_years - self.purchase_year
        is_purchase_year = (years_since_first_purchase % self.replacement_cycle_years == 0)
        
        if is_purchase_year:
            # ローンを組まない場合は一括購入費用が発生
            if not self.loan:
                costs["purchase"] = self.purchase_price
            else:
                # ローンを組む場合は頭金などがあればここに（今回はシンプルにローンシミュレーション）
                # ローン開始年を自動調整する等が必要ですが、ここでは購入した時点でローンがスタートする構造とします
                pass

        # 2. 定常維持費
        costs["maintenance"] = self.annual_maintenance_cost
        costs["insurance"] = self.annual_insurance_cost

        # 3. 車検費用（購入年と、それ以降の車検サイクル年に発生。ただし購入年は車検不要）
        if years_since_first_purchase > 0 and (years_since_first_purchase % self.inspection_cycle_years == 0):
            costs["inspection"] = self.inspection_cost

        # 4. ローン返済額の加算
        # 買い替えるたびにローンが再設定される簡易シミュレーション
        if self.loan:
            # 最新の購入サイクルから数えてローン期間中かどうか
            cycle_idx = years_since_first_purchase // self.replacement_cycle_years
            last_purchase_year = self.purchase_year + cycle_idx * self.replacement_cycle_years
            
            # ローン借入の開始を購入年にあわせる
            loan_start = last_purchase_year
            years_in_current_cycle = elapsed_years - loan_start
            
            if 0 <= years_in_current_cycle < self.loan.term_years:
                # ローン一時インスタンスでの計算
                temp_loan = CarLoan(
                    borrowed_amount=self.loan.borrowed_amount,
                    term_years=self.loan.term_years,
                    interest_rate=self.loan.interest_rate,
                    start_year=loan_start
                )
                costs["loan_repayment"] = temp_loan.get_annual_repayment(elapsed_years)

        return costs
