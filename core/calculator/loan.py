class LoanCalculator:
    """住宅ローン返済スケジュール計算を行うヘルパー"""

    @staticmethod
    def calculate_amortization_schedule(
        principal: float,
        term_years: int,
        interest_rate: float,
        loan_type: str = "variable",
        repayment_method: str = "equal_payment",
        start_year: int = 0
    ) -> list:
        """
        毎年のローン残高、支払金利、支払元金の推移を配列で返します。
        """
        schedule = []
        monthly_rate = (interest_rate / 100.0) / 12
        total_months = term_years * 12
        balance = principal
        
        # 毎年はじめに1年間の集計
        for year in range(term_years):
            annual_principal_paid = 0.0
            annual_interest_paid = 0.0
            
            for month in range(12):
                if balance <= 0:
                    break
                
                # 金利支払
                interest_payment = balance * monthly_rate
                
                # 元金および元利均等の毎月返済額算出
                if repayment_method == "equal_payment":
                    # 元利均等
                    # 毎月の返済金額
                    n = total_months - (year * 12 + month)
                    if monthly_rate == 0:
                        monthly_payment = balance / n
                    else:
                        monthly_payment = balance * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
                    
                    principal_payment = monthly_payment - interest_payment
                else:
                    # 元金均等
                    # 毎月均等の元金を返済: (借入総額 / 全返済月数)
                    principal_payment = principal / total_months
                    # 残高を超過しないように調整
                    principal_payment = min(principal_payment, balance)

                # 利息および元金支払額の累積
                annual_interest_paid += interest_payment
                annual_principal_paid += principal_payment
                balance -= principal_payment

            schedule.append({
                "year": start_year + year,
                "start_balance": balance + annual_principal_paid,
                "principal_paid": annual_principal_paid,
                "interest_paid": annual_interest_paid,
                "end_balance": max(0.0, balance)
            })

            if balance <= 0:
                break
                
        return schedule
