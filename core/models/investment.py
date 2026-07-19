from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class InvestmentAccount:
    """投資口座（NISA、iDeCo、特定口座など）データモデル"""
    account_type: str               # 'nisa', 'ideco', 'taxable_investment', 'savings', 'cash'
    owner: str                      # 所有者 (例: 'husband', 'wife')
    initial_balance: float = 0.0    # 開始初期残高 (円)
    monthly_deposit: float = 0.0    # 毎月積立額 (円)
    annual_return_rate: float = 0.0 # 年利 (%) (例: 4.0)
    
    # 途中での値の変更（経過年数ベース）
    # 例: { 5: {"monthly_deposit": 100000} } 5年後から毎月10万に変更
    changes_schedule: dict = field(default_factory=dict)

    def get_monthly_deposit(self, elapsed_years: int) -> float:
        """
        指定された年における毎月積立額を取得します（スケジュール変動対応）。
        """
        deposit = self.monthly_deposit
        for yr, vals in sorted(self.changes_schedule.items()):
            if elapsed_years >= yr:
                if "monthly_deposit" in vals:
                    deposit = vals["monthly_deposit"]
        return deposit

    def get_annual_return_rate(self, elapsed_years: int) -> float:
        """
        指定された年における年利を取得します（スケジュール変動対応）。
        """
        rate = self.annual_return_rate
        for yr, vals in sorted(self.changes_schedule.items()):
            if elapsed_years >= yr:
                if "annual_return_rate" in vals:
                    rate = vals["annual_return_rate"]
        return rate

    def simulate_year(self, elapsed_years: int, current_balance: float, months: int = 12, override_monthly_dep: float = None) -> dict:
        """
        1年間の運用計算（複利計算と積立）
        """
        monthly_dep = self.get_monthly_deposit(elapsed_years)
        if override_monthly_dep is not None:
            monthly_dep = override_monthly_dep
            
        annual_rate = self.get_annual_return_rate(elapsed_years)
        
        # 指定ヶ月分の複利計算 (毎月拠出・毎月複利)
        rate_monthly = (annual_rate / 100.0) / 12
        balance = current_balance
        total_deposited_this_year = 0.0

        for _ in range(months):
            # 積立金を投入
            balance += monthly_dep
            total_deposited_this_year += monthly_dep
            # 利息を付与 (複利)
            balance *= (1.0 + rate_monthly)

        interest_gained = balance - (current_balance + total_deposited_this_year)
        
        return {
            "end_balance": balance,
            "deposited": total_deposited_this_year,
            "interest": interest_gained
        }
