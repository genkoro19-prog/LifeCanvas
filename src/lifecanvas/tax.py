from __future__ import annotations

from dataclasses import dataclass

from .models import SocialInsuranceMode, SystemRules


@dataclass(frozen=True)
class NetIncome:
    gross: float
    social_insurance: float
    income_tax: float
    resident_tax: float
    net: float


def salary_income_deduction(gross: float) -> float:
    if gross <= 0:
        return 0.0
    if gross <= 1_900_000:
        return min(gross, 650_000)
    if gross <= 3_600_000:
        return gross * 0.30 + 80_000
    if gross <= 6_600_000:
        return gross * 0.20 + 440_000
    if gross <= 8_500_000:
        return gross * 0.10 + 1_100_000
    return 1_950_000


def basic_deduction_2025(total_income: float, rules: SystemRules) -> float:
    if total_income <= 1_320_000:
        return rules.income_tax_basic_deduction_2025_low
    if total_income <= 3_360_000:
        return 880_000
    if total_income <= 4_890_000:
        return 680_000
    if total_income <= 6_550_000:
        return 630_000
    if total_income <= 23_500_000:
        return rules.income_tax_basic_deduction_standard
    if total_income <= 24_000_000:
        return 480_000
    if total_income <= 24_500_000:
        return 320_000
    if total_income <= 25_000_000:
        return 160_000
    return 0.0


def progressive_income_tax(taxable: float) -> float:
    taxable = max(0.0, taxable)
    if taxable <= 1_950_000:
        tax = taxable * 0.05
    elif taxable <= 3_300_000:
        tax = taxable * 0.10 - 97_500
    elif taxable <= 6_950_000:
        tax = taxable * 0.20 - 427_500
    elif taxable <= 9_000_000:
        tax = taxable * 0.23 - 636_000
    elif taxable <= 18_000_000:
        tax = taxable * 0.33 - 1_536_000
    elif taxable <= 40_000_000:
        tax = taxable * 0.40 - 2_796_000
    else:
        tax = taxable * 0.45 - 4_796_000
    return max(0.0, tax * 1.021)


def estimate_net_salary(
    gross: float,
    mode: SocialInsuranceMode,
    rules: SystemRules,
    housing_tax_credit: float = 0.0,
) -> NetIncome:
    if gross <= 0:
        return NetIncome(0, 0, 0, 0, 0)

    if mode == SocialInsuranceMode.EMPLOYEE:
        social = gross * rules.employee_social_insurance_rate
    elif mode == SocialInsuranceMode.NATIONAL:
        social = gross * rules.national_social_insurance_rate
    else:
        social = 0.0

    salary_income = max(0.0, gross - salary_income_deduction(gross))
    income_basic = basic_deduction_2025(salary_income, rules)
    taxable_income = max(0.0, salary_income - social - income_basic)
    income_tax = progressive_income_tax(taxable_income)

    resident_taxable = max(0.0, salary_income - social - rules.resident_tax_basic_deduction)
    resident_tax = 0.0 if gross <= 1_100_000 else resident_taxable * 0.10 + 5_000

    credit_remaining = max(0.0, housing_tax_credit)
    income_reduction = min(income_tax, credit_remaining)
    income_tax -= income_reduction
    credit_remaining -= income_reduction
    resident_reduction = min(resident_tax, min(136_500, credit_remaining))
    resident_tax -= resident_reduction

    net = max(0.0, gross - social - income_tax - resident_tax)
    return NetIncome(gross, social, income_tax, resident_tax, net)
