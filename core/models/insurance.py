from dataclasses import dataclass

@dataclass
class InsurancePlan:
    """保険契約データモデル"""
    name: str                       # 保険名称（例: '定期死亡保険', '医療保険'）
    insurance_type: str             # 保険タイプ ('life', 'medical', 'education_saving', 'fire', 'car')
    annual_premium: float           # 年間保険料 (円)
    start_year: int                 # 開始年 (シミュレーション経過年数ベース)
    insurance_term_years: int       # 保障期間 (年)
    benefit_amount: float = 0.0     # 保障金額 / 給付金 (万が一の時など)
    
    # 積立型（学資保険など）の場合の満期設定
    maturity_year: int = -1         # 満期年 (例: 開始から18年後)
    maturity_payment: float = 0.0   # 満期返戻金 (円)

    def get_annual_cost(self, elapsed_years: int) -> float:
        """指定年における年間保険料を算出します。"""
        years_active = elapsed_years - self.start_year
        if 0 <= years_active < self.insurance_term_years:
            return self.annual_premium
        return 0.0

    def get_maturity_payout(self, elapsed_years: int) -> float:
        """満期時の受け取り給付金を算出します。"""
        if self.maturity_year != -1:
            maturity_absolute_year = self.start_year + self.maturity_year
            if elapsed_years == maturity_absolute_year:
                return self.maturity_payment
        return 0.0
