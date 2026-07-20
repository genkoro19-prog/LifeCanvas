import pytest

from lifecanvas.models import (
    CarPlan,
    EducationCostPlan,
    HousingPlan,
    LivingCostPlan,
    MortgagePlan,
    NisaPlan,
    PersonalDebt,
    PersonPlan,
    ProjectPlan,
    SocialInsuranceMode,
    WalletPlan,
    WifeWorkStage,
    YearResult,
)
from lifecanvas.policy_engine import SimulationEngine
import lifecanvas.policy_engine as policy_engine


def _plan(*, wife_income=1_200_000, household=3_600_000, years=1):
    plan = ProjectPlan(
        simulation_years=years,
        initial_cash=0,
        husband=PersonPlan(
            name="夫",
            current_age=30,
            annual_gross_income=6_000_000,
            retirement_age=60,
            social_insurance_mode=SocialInsuranceMode.NONE,
        ),
        wife=PersonPlan(
            name="妻",
            current_age=30,
            annual_gross_income=wife_income,
            retirement_age=60,
            social_insurance_mode=SocialInsuranceMode.NONE,
        ),
        wife_work_stages=[
            WifeWorkStage(
                key="full_time",
                label="勤務",
                start_offset=0,
                annual_gross_income=wife_income,
                social_insurance_mode=SocialInsuranceMode.NONE,
            )
        ],
        children=[],
        education=EducationCostPlan(),
        housing=HousingPlan(
            purchase_price=0,
            mortgage=MortgagePlan(principal=0, term_years=35, initial_rate_percent=0),
            move_mode="none",
            move_offset=None,
        ),
        car=CarPlan(enabled=False),
        cars=[],
        nisa_accounts=[
            NisaPlan(owner="husband", monthly_contribution=0),
            NisaPlan(owner="wife", monthly_contribution=30_000),
        ],
        living_cost=LivingCostPlan(monthly_amount=0),
        wallets=WalletPlan(
            mode="separate",
            initial_husband_cash=2_000_000,
            initial_wife_cash=0,
            wife_household_monthly=100_000,
            wife_personal_spending_monthly=40_000,
            wife_contribution_threshold_monthly=30_000,
            husband_minimum_cash=0,
            husband_target_cash=0,
            husband_monthly_saving_until_target=0,
            auto_invest_enabled=False,
        ),
    )
    rows = []
    for offset in range(years):
        rows.append(
            YearResult(
                offset=offset,
                calendar_year=2026 + offset,
                months=12,
                husband_age=30 + offset,
                wife_age=30 + offset,
                children_ages={},
                husband_gross=6_000_000,
                wife_gross=wife_income,
                salary_net=6_000_000 + wife_income,
                benefits=0,
                rental_income=0,
                total_income=6_000_000 + wife_income,
                core_living_cost=household,
                housing_cost=0,
                mortgage_payment=0,
                mortgage_interest=0,
                mortgage_principal=0,
                education_cost=0,
                car_cost=0,
                consumption_total=household,
                living_surplus=0,
                nisa_planned=0,
                nisa_contributed=0,
                nisa_sold=0,
                cash_end=0,
                investments_market_value=0,
                investments_book_value=0,
                property_value=0,
                mortgage_balance=0,
                net_worth=0,
            )
        )
    policy_engine.HousingSimulationEngine = lambda _plan: type(
        "RawEngine", (), {"run": lambda self: rows}
    )()
    return plan, rows


def test_wife_contributes_zero_when_monthly_surplus_is_threshold_or_less():
    plan, _ = _plan(wife_income=1_200_000)
    row = SimulationEngine(plan).run()[0]
    assert row.wife_household_paid == 0
    assert row.husband_household_paid == pytest.approx(3_600_000)
    assert row.wife_cash_end >= 0


def test_wife_contribution_uses_surplus_above_threshold_and_cap():
    plan, _ = _plan(wife_income=2_400_000)
    row = SimulationEngine(plan).run()[0]
    assert row.wife_household_paid == pytest.approx(1_200_000)
    assert row.husband_household_paid == pytest.approx(2_400_000)


def test_debt_is_paid_before_wife_household_contribution():
    plan, _ = _plan(wife_income=1_800_000)
    plan.personal_debts = [
        PersonalDebt(
            debt_id="student",
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=12,
        )
    ]
    row = SimulationEngine(plan).run()[0]
    assert row.wife_debt_payment == pytest.approx(180_000)
    assert row.wife_household_paid == pytest.approx(420_000)


def test_cash_never_goes_negative_and_unmet_is_separate():
    plan, rows = _plan(wife_income=0, household=1_200_000)
    plan.wallets.initial_husband_cash = 0
    plan.husband.annual_gross_income = 0
    rows[0].husband_gross = 0
    rows[0].wife_gross = 0
    rows[0].salary_net = 0
    rows[0].total_income = 0
    row = SimulationEngine(plan).run()[0]
    assert row.husband_cash_end == 0
    assert row.wife_cash_end == 0
    assert row.unmet_amount > 0


def test_spousal_nisa_transfer_is_capped_at_annual_management_limit():
    plan, _ = _plan(wife_income=0, household=0)
    plan.wallets.initial_husband_cash = 10_000_000
    plan.wallets.husband_target_cash = 1_000_000
    plan.wallets.auto_invest_enabled = True
    plan.wallets.spouse_nisa_transfer_enabled = True
    plan.wallets.spouse_nisa_annual_management_limit = 1_100_000
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.lifetime_limit = 0
    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")
    wife.monthly_contribution = 0
    row = SimulationEngine(plan).run()[0]
    assert row.spouse_nisa_transfer == pytest.approx(1_100_000)
    assert row.wife_nisa_contributed == pytest.approx(1_100_000)
