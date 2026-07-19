from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SocialInsuranceMode(StrEnum):
    EMPLOYEE = "employee"
    DEPENDENT = "dependent"
    NATIONAL = "national"
    NONE = "none"


class PersonPlan(BaseModel):
    name: str
    current_age: int = Field(ge=0, le=100)
    annual_gross_income: float = Field(ge=0)
    retirement_age: int = Field(ge=18, le=100)
    pension_start_age: int = Field(default=65, ge=50, le=100)
    annual_pension: float = Field(default=0, ge=0)
    social_insurance_mode: SocialInsuranceMode = SocialInsuranceMode.EMPLOYEE


class IncomePeriod(BaseModel):
    owner: Literal["husband", "wife"]
    label: str
    start_age: int = Field(ge=0, le=100)
    end_age: int | None = Field(default=None, ge=0, le=101)
    annual_gross_income: float = Field(default=0, ge=0)
    annual_benefit: float = Field(default=0, ge=0)
    social_insurance_mode: SocialInsuranceMode = SocialInsuranceMode.EMPLOYEE

    def active(self, age: int) -> bool:
        return age >= self.start_age and (self.end_age is None or age < self.end_age)

    @model_validator(mode="after")
    def validate_age_range(self) -> "IncomePeriod":
        if self.end_age is not None and self.end_age <= self.start_age:
            raise ValueError("収入期間の終了年齢は開始年齢より後にしてください")
        return self


class OneTimeIncome(BaseModel):
    owner: Literal["husband", "wife", "household"] = "household"
    label: str
    age: int = Field(ge=0, le=100)
    amount: float = Field(default=0, ge=0)


class WifeWorkStage(BaseModel):
    key: str
    label: str
    start_offset: int = Field(ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    annual_gross_income: float = Field(ge=0)
    annual_benefit: float = Field(default=0, ge=0)
    social_insurance_mode: SocialInsuranceMode = SocialInsuranceMode.DEPENDENT

    def active(self, offset: int) -> bool:
        return offset >= self.start_offset and (self.end_offset is None or offset < self.end_offset)


class ChildPlan(BaseModel):
    name: str
    birth_offset: int = Field(ge=0)


class EducationCostPlan(BaseModel):
    age_0_2: float = 150_000
    age_3_5: float = 200_000
    elementary: float = 350_000
    junior_high: float = 550_000
    high_school: float = 550_000
    university: float = 1_500_000

    def annual_cost(self, age: int) -> float:
        if age < 0:
            return 0.0
        if age <= 2:
            return self.age_0_2
        if age <= 5:
            return self.age_3_5
        if age <= 11:
            return self.elementary
        if age <= 14:
            return self.junior_high
        if age <= 17:
            return self.high_school
        if age <= 21:
            return self.university
        return 0.0


class MortgagePlan(BaseModel):
    principal: float = Field(ge=0)
    term_years: int = Field(ge=1, le=50)
    initial_rate_percent: float = Field(ge=0, le=20)
    annual_rate_step_percent: float = Field(default=0.2, ge=0, le=5)
    max_rate_percent: float = Field(default=3.0, ge=0, le=20)
    property_tax_annual: float = Field(default=120_000, ge=0)
    insurance_annual: float = Field(default=20_000, ge=0)
    maintenance_annual: float = Field(default=0, ge=0)


class HousingPlan(BaseModel):
    purchase_price: float = Field(ge=0)
    mortgage: MortgagePlan
    move_offset: int | None = Field(default=26, ge=0)
    move_cost: float = Field(default=1_000_000, ge=0)
    new_home_monthly_cost: float = Field(default=150_000, ge=0)
    old_home_net_rent_annual: float = Field(default=750_000, ge=0)
    land_ratio: float = Field(default=0.5, ge=0, le=1)
    building_floor_ratio: float = Field(default=0.2, ge=0, le=1)
    building_depreciation_years: int = Field(default=30, ge=1)


class CarPlan(BaseModel):
    purchase_offset: int = Field(default=1, ge=0)
    purchase_price: float = Field(default=1_500_000, ge=0)
    annual_running_cost: float = Field(default=350_000, ge=0)
    replacement_cycle_years: int | None = Field(default=7, ge=1)
    replacement_price: float = Field(default=1_200_000, ge=0)


class NisaPlan(BaseModel):
    owner: Literal["husband", "wife"]
    monthly_contribution: float = Field(ge=0)
    contribution_changes: dict[int, float] = Field(default_factory=dict)
    annual_return_percent: float = Field(default=4.0, ge=-100, le=100)
    annual_limit: float = Field(default=1_200_000, ge=0)
    lifetime_limit: float = Field(default=18_000_000, ge=0)

    def monthly_for_offset(self, offset: int) -> float:
        value = self.monthly_contribution
        for start in sorted(self.contribution_changes):
            if offset >= start:
                value = self.contribution_changes[start]
        return value


class LivingCostPlan(BaseModel):
    monthly_amount: float = Field(default=250_000, ge=0)
    scope: Literal["includes_initial_housing", "excludes_housing"] = "includes_initial_housing"
    annual_child_increment: float = Field(default=0, ge=0)


class SystemRules(BaseModel):
    income_tax_basic_deduction_2025_low: float = 950_000
    income_tax_basic_deduction_standard: float = 580_000
    resident_tax_basic_deduction: float = 430_000
    employee_social_insurance_rate: float = Field(default=0.15, ge=0, le=1)
    national_social_insurance_rate: float = Field(default=0.18, ge=0, le=1)
    minimum_cash_reserve: float = Field(default=1_200_000, ge=0)
    child_allowance_age_0_2_monthly: float = 15_000
    child_allowance_age_3_18_monthly: float = 10_000


class ProjectPlan(BaseModel):
    name: str = "LifeCanvas Plan"
    start_year: int = 2026
    start_month: int = Field(default=9, ge=1, le=12)
    simulation_years: int = Field(default=45, ge=1, le=100)
    initial_cash: float = Field(default=1_200_000, ge=0)
    husband: PersonPlan
    wife: PersonPlan
    income_periods: list[IncomePeriod] = Field(default_factory=list)
    one_time_incomes: list[OneTimeIncome] = Field(default_factory=list)
    wife_work_stages: list[WifeWorkStage]
    children: list[ChildPlan]
    education: EducationCostPlan
    housing: HousingPlan
    car: CarPlan
    nisa_accounts: list[NisaPlan]
    living_cost: LivingCostPlan
    rules: SystemRules = Field(default_factory=SystemRules)

    @model_validator(mode="after")
    def validate_stages(self) -> "ProjectPlan":
        if not self.wife_work_stages:
            raise ValueError("wife_work_stages must not be empty")
        return self


class YearResult(BaseModel):
    offset: int
    calendar_year: int
    months: int
    husband_age: int
    wife_age: int
    children_ages: dict[str, int]
    husband_gross: float
    wife_gross: float
    salary_net: float
    pension_income: float = 0
    one_time_income: float = 0
    benefits: float
    rental_income: float
    total_income: float
    core_living_cost: float
    housing_cost: float
    mortgage_payment: float
    mortgage_interest: float
    mortgage_principal: float
    education_cost: float
    car_cost: float
    consumption_total: float
    living_surplus: float
    nisa_planned: float
    nisa_contributed: float
    nisa_sold: float
    cash_end: float
    investments_market_value: float
    investments_book_value: float
    property_value: float
    mortgage_balance: float
    net_worth: float
    events: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
