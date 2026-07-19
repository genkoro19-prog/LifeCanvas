class TaxCalculator:
    """
    所得税・住民税・社会保険料を年収から概算する簡易計算機。
    FP相談実務で広く使われる簡易速算式に基づき、手取りを算出します。
    """
    
    @staticmethod
    def calculate_social_insurance(annual_income: float, is_employee: bool = True) -> float:
        """
        社会保険料の概算。
        会社員の場合: 給与収入の約 14.5%〜15.0%（健康保険・厚生年金・雇用保険）。
        パート・自営業の場合: 国民年金＋国民健康保険（ここでは簡易化）。
        """
        if annual_income <= 0:
            return 0.0
            
        if is_employee:
            # 会社員の場合、一般的に約 14.5% が目安
            return annual_income * 0.145
        else:
            # 自営業・パートの場合 (国民年金約20万/年 + 健康保険約10%)
            national_pension = 16500 * 12 # 20万円弱
            health_insurance = min(annual_income * 0.08, 800000.0) # 上限を考慮
            return national_pension + health_insurance

    @staticmethod
    def calculate_income_tax(annual_income: float, social_ins: float, is_employee: bool = True) -> float:
        """
        所得税の概算。
        1. 給与所得控除を差し引く
        2. 社会保険料控除、基礎控除（48万円）、および配偶者控除などを差し引き「課税所得」を算出
        3. 所得税の超過累進税率を適用
        """
        if annual_income <= 0:
            return 0.0

        # 1. 給与所得控除 (日本の税制に準ずる簡略化)
        if is_employee:
            if annual_income <= 1625000:
                salary_deduction = 550000
            elif annual_income <= 1800000:
                salary_deduction = annual_income * 0.4 - 100000
            elif annual_income <= 3600000:
                salary_deduction = annual_income * 0.3 + 80000
            elif annual_income <= 6600000:
                salary_deduction = annual_income * 0.2 + 440000
            elif annual_income <= 8500000:
                salary_deduction = annual_income * 0.1 + 1100000
            else:
                salary_deduction = 1950000
        else:
            # 自営業の場合は給与所得控除はなし (代わりに事業経費を差し引くが、ここではモデル化を簡易にするため0)
            salary_deduction = 0.0

        # 所得額
        income_after_deduction = max(0.0, annual_income - salary_deduction)

        # 2. 所得控除 (基礎控除 48万 + 社会保険料控除)
        basic_deduction = 480000.0
        total_deduction = basic_deduction + social_ins

        # 課税所得
        taxable_income = max(0.0, income_after_deduction - total_deduction)

        # 3. 所得税率の適用 (累進課税)
        if taxable_income <= 1950000:
            tax = taxable_income * 0.05
        elif taxable_income <= 3300000:
            tax = taxable_income * 0.10 - 97500
        elif taxable_income <= 6950000:
            tax = taxable_income * 0.20 - 427500
        elif taxable_income <= 9000000:
            tax = taxable_income * 0.23 - 636000
        elif taxable_income <= 18000000:
            tax = taxable_income * 0.33 - 1536000
        elif taxable_income <= 40000000:
            tax = taxable_income * 0.40 - 2796000
        else:
            tax = taxable_income * 0.45 - 4796000

        # 復興特別所得税 (2.1%を加算)
        tax *= 1.021
        return round(tax)

    @staticmethod
    def calculate_inhabitants_tax(annual_income: float, social_ins: float, is_employee: bool = True) -> float:
        """
        住民税の概算。
        所得割（課税所得の約 10%）＋均等割（約 5,000円）で算出します。
        住民税の基礎控除は43万円です。
        """
        if annual_income <= 0:
            return 0.0

        # 1. 給与所得控除
        if is_employee:
            if annual_income <= 1625000:
                salary_deduction = 550000
            elif annual_income <= 1800000:
                salary_deduction = annual_income * 0.4 - 100000
            elif annual_income <= 3600000:
                salary_deduction = annual_income * 0.3 + 80000
            elif annual_income <= 6600000:
                salary_deduction = annual_income * 0.2 + 440000
            elif annual_income <= 8500000:
                salary_deduction = annual_income * 0.1 + 1100000
            else:
                salary_deduction = 1950000
        else:
            salary_deduction = 0.0

        income_after_deduction = max(0.0, annual_income - salary_deduction)

        # 住民税の基礎控除は 43万円
        basic_deduction = 430000.0
        total_deduction = basic_deduction + social_ins
        
        # 課税所得
        taxable_income = max(0.0, income_after_deduction - total_deduction)

        # 所得割 (10%) + 均等割 (5,000円)
        tax = (taxable_income * 0.10) + 5000.0
        return round(tax)

    @classmethod
    def get_net_income(cls, annual_income: float, is_employee: bool = True, housing_deduction: float = 0.0) -> dict:
        """
        年間の手取り額を計算します。
        住宅ローン控除（所得税・住民税からの控除）も加味します。
        """
        if annual_income <= 0:
            return {"net_income": 0.0, "social_insurance": 0.0, "income_tax": 0.0, "inhabitants_tax": 0.0, "housing_deduction_applied": 0.0}

        social_ins = cls.calculate_social_insurance(annual_income, is_employee)
        income_tax = cls.calculate_income_tax(annual_income, social_ins, is_employee)
        inhabitants_tax = cls.calculate_inhabitants_tax(annual_income, social_ins, is_employee)

        # 住宅ローン控除の適用
        # 控除は所得税から優先的に引かれ、引ききれなかった分は住民税から一定上限（最大13.65万円）引かれます。
        applied_deduction = 0.0
        if housing_deduction > 0:
            # 所得税からの控除
            tax_deducted = min(income_tax, housing_deduction)
            income_tax -= tax_deducted
            applied_deduction += tax_deducted
            
            remaining_deduction = housing_deduction - tax_deducted
            if remaining_deduction > 0:
                # 住民税からの控除 (最大136,500円の上限あり)
                inhabitants_limit = min(136500.0, remaining_deduction)
                inhabitants_deducted = min(inhabitants_tax, inhabitants_limit)
                inhabitants_tax -= inhabitants_deducted
                applied_deduction += inhabitants_deducted

        net_income = annual_income - (social_ins + income_tax + inhabitants_tax)
        
        return {
            "net_income": max(0.0, net_income),
            "social_insurance": social_ins,
            "income_tax": income_tax,
            "inhabitants_tax": inhabitants_tax,
            "housing_deduction_applied": applied_deduction
        }
