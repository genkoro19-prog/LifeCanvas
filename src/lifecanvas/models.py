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


class CashFlowEvent(BaseModel):
    """A user-defined one-off income or expense on the life timeline."""

    label: str
    offset: int = Field(ge=0)
    flow_type: Literal["income", "expense"] = "expense"
    amount: float = Field(default=0, ge=0)
    category: Literal["family", "work", "housing", "car", "travel", "other"] = "other"


class PersonalDebt(BaseModel):
    """A personal or household repayment that may be entered with only amount and term."""

    debt_id: str
    name: str
    borrower: Literal["husband", "wife", "household"] = "household"
    monthly_payment: float = Field(default=0, ge=0)
    start_offset_months: int = Field(default=0, ge=0)
    remaining_months: int = Field(default=0, ge=0)
    current_balance: float = Field(default=0, ge=0)
    principal: float = Field(default=0, ge=0)
    annual_interest_rate: float = Field(default=0, ge=0, le=100)
    repayment_method: Literal["fixed", "equal_payment", "equal_principal"] = "fixed"
    bonus_payment: float = Field(default=0, ge=0)
    payment_source: Literal["borrower", "spouse", "household", "unmet"] = "borrower"
    notes: str = ""

    @model_validator(mode="after")
    def validate_debt(self) -> "PersonalDebt":
        if self.monthly_payment <= 0 and self.bonus_payment <= 0:
            raise ValueError("個人借入は月額またはボーナス返済額を入力してください")
        if self.remaining_months <= 0 and self.current_balance <= 0:
            raise ValueError("個人借入は残り期間または現在残高を入力してください")
        return self


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
    move_mode: Literal["none", "sell", "keep"] = "keep"
    move_offset: int | None = Field(default=26, ge=0)
    move_cost: float = Field(default=1_000_000, ge=0)
    new_home_monthly_cost: float = Field(default=150_000, ge=0)
    old_home_net_rent_annual: float = Field(default=750_000, ge=0)
    sale_price: float = Field(default=0, ge=0)
    new_home_purchase_price: float = Field(default=0, ge=0)
    new_mortgage_principal: float = Field(default=0, ge=0)
    new_mortgage_term_years: int = Field(default=35, ge=1, le=50)
    new_mortgage_rate_percent: float = Field(default=1.5, ge=0, le=20)
    land_ratio: float = Field(default=0.5, ge=0, le=1)
    building_floor_ratio: float = Field(default=0.2, ge=0, le=1)
    building_depreciation_years: int = Field(default=30, ge=1)

    @model_validator(mode="after")
    def normalize_move(self) -> "HousingPlan":
        if self.move_mode == "none":
            self.move_offset = None
        elif self.move_offset is None:
            self.move_mode = "none"
        if self.new_mortgage_principal > self.new_home_purchase_price and self.new_home_purchase_price > 0:
            raise ValueError("新居の住宅ローンは新居購入額以下にしてください")
        return self


class CarPlan(BaseModel):
    name: str = "車1"
    enabled: bool = True
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
    annual_limit: float = Field(default=3_600_000, ge=0)
    lifetime_limit: float = Field(default=18_000_000, ge=0)

    @model_validator(mode="after")
    def migrate_legacy_annual_limit(self) -> "NisaPlan":
        if self.annual_limit == 1_200_000:
            self.annual_limit = 3_600_000
        return self

    def monthly_for_offset(self, offset: int) -> float:
        value = self.monthly_contribution
        for start in sorted(self.contribution_changes):
            if offset >= start:
                value = self.contribution_changes[start]
        return value


class WalletPlan(BaseModel):
    """Rules for separately owned cash, household support, and NISA allocation."""

    mode: Literal["combined", "separate"] = "combined"
    initial_husband_cash: float = Field(default=0, ge=0)
    initial_wife_cash: float = Field(default=0, ge=0)
    husband_household_monthly: float = Field(default=0, ge=0)
    wife_household_monthly: float = Field(default=150_000, ge=0)
    husband_child_household_increment_monthly: float = Field(default=0, ge=0)
    wife_child_household_increment_monthly: float = Field(default=0, ge=0)
    husband_personal_spending_monthly: float = Field(default=0, ge=0)
    wife_personal_spending_monthly: float = Field(default=0, ge=0)
    wife_contribution_threshold_monthly: float = Field(default=30_000, ge=0)
    wife_use_existing_cash_for_household: bool = False
    husband_minimum_cash: float = Field(default=1_000_000, ge=0)
    husband_target_cash: float = Field(default=3_000_000, ge=0)
    husband_monthly_saving_until_target: float = Field(default=50_000, ge=0)
    auto_invest_enabled: bool = True
    auto_extra_monthly_cap: float = Field(default=300_000, ge=0, le=300_000)
    spouse_nisa_transfer_enabled: bool = True
    spouse_nisa_annual_management_limit: float = Field(default=1_100_000, ge=0)
    spouse_nisa_other_transfers_this_year: float = Field(default=0, ge=0)
    after_nisa_destination: Literal[
        "husband_cash", "husband_taxable", "wife_taxable", "mortgage", "other_goal"
    ] = "husband_cash"
    household_shortfall_husband_percent: float = Field(default=100, ge=0, le=100)
    household_shortfall_wife_percent: float = Field(default=0, ge=0, le=100)
    minimum_personal_cash: float = Field(default=1_000_000, ge=0)
    target_personal_cash: float = Field(default=1_000_000, ge=0)
    minimum_household_cash: float = Field(default=0, ge=0)
    target_household_cash: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_settings(self) -> "WalletPlan":
        legacy_equal_split = (
            abs(self.household_shortfall_husband_percent - 50) < 0.01
            and abs(self.household_shortfall_wife_percent - 50) < 0.01
        )
        if legacy_equal_split:
            self.household_shortfall_husband_percent = 100
            self.household_shortfall_wife_percent = 0
            if self.wife_household_monthly <= 100_000:
                self.wife_household_monthly = 150_000
        if self.husband_minimum_cash == 1_000_000 and self.minimum_personal_cash != 1_000_000:
            self.husband_minimum_cash = self.minimum_personal_cash
        if self.husband_target_cash == 3_000_000 and self.target_personal_cash > self.husband_minimum_cash:
            self.husband_target_cash = self.target_personal_cash
        if self.husband_target_cash < self.husband_minimum_cash:
            raise ValueError("夫の目標預金は最低維持預金以上にしてください")
        return self


class LivingCostPlan(BaseModel):
    monthly_amount: float = Field(default=250_000, ge=0)
    scope: Literal["includes_initial_housing", "excludes_housing"] = "includes_initial_housing"
    annual_child_increment: float = Field(default=0, ge=0)
    includes_personal_spending: bool = True


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
    cashflow_events: list[CashFlowEvent] = Field(default_factory=list)
    personal_debts: list[PersonalDebt] = Field(default_factory=list)
    wife_work_stages: list[WifeWorkStage]
    children: list[ChildPlan]
    education: EducationCostPlan
    housing: HousingPlan
    car: CarPlan
    cars: list[CarPlan] = Field(default_factory=list)
    nisa_accounts: list[NisaPlan]
    living_cost: LivingCostPlan
    wallets: WalletPlan = Field(default_factory=WalletPlan)
    wife_work_preset: Literal["custom", "early", "standard", "care"] = "custom"
    rules: SystemRules = Field(default_factory=SystemRules)

    @model_validator(mode="after")
    def validate_plan(self) -> "ProjectPlan":
        if not self.wife_work_stages:
            raise ValueError("wife_work_stages must not be empty")
        for event in self.cashflow_events:
            if event.offset >= self.simulation_years:
                raise ValueError("臨時イベントはシミュレーション期間内に設定してください")
        if not self.cars:
            self.cars = [self.car.model_copy(deep=True)] if self.car.enabled else []
        elif self.cars:
            self.car = self.cars[0].model_copy(deep=True)
        for vehicle in self.cars:
            if vehicle.purchase_offset >= self.simulation_years:
                raise ValueError("車の購入年はシミュレーション期間内に設定してください")
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
    life_event_income: float = 0
    life_event_expense: float = 0
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
    household_cash_end: float = 0
    husband_cash_end: float = 0
    wife_cash_end: float = 0
    husband_nisa_contributed: float = 0
    wife_nisa_contributed: float = 0
    husband_base_nisa_contributed: float = 0
    wife_base_nisa_contributed: float = 0
    husband_additional_nisa_contributed: float = 0
    wife_additional_nisa_contributed: float = 0
    spouse_nisa_transfer: float = 0
    husband_nisa_market_value: float = 0
    wife_nisa_market_value: float = 0
    recommended_husband_monthly: float = 0
    recommended_wife_monthly: float = 0
    household_cost_net: float = 0
    household_shortfall: float = 0
    household_unmet: float = 0
    husband_household_paid: float = 0
    wife_household_paid: float = 0
    husband_personal_spending: float = 0
    wife_personal_spending: float = 0
    husband_personal_income: float = 0
    wife_personal_income: float = 0
    husband_debt_payment: float = 0
    wife_debt_payment: float = 0
    household_debt_payment: float = 0
    husband_savings_change: float = 0
    wife_savings_change: float = 0
    husband_unmet: float = 0
    wife_unmet: float = 0
    unmet_amount: float = 0
    events: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
