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
    return plan, rows


def _run(plan, rows, monkeypatch):
    monkeypatch.setattr(
        policy_engine,
        "HousingSimulationEngine",
        lambda _plan: type("RawEngine", (), {"run": lambda self: rows})(),
    )
    return SimulationEngine(plan).run()[0]


def test_wife_contributes_zero_when_monthly_surplus_is_threshold_or_less(monkeypatch):
    plan, rows = _plan(wife_income=1_200_000)
    row = _run(plan, rows, monkeypatch)
    assert row.wife_household_paid == 0
    assert row.husband_household_paid == pytest.approx(3_600_000)
    assert row.wife_cash_end >= 0


def test_wife_contribution_uses_surplus_above_threshold_and_cap(monkeypatch):
    plan, rows = _plan(wife_income=3_600_000)
    row = _run(plan, rows, monkeypatch)
    assert row.wife_household_paid == pytest.approx(1_200_000)
    assert row.husband_household_paid == pytest.approx(2_400_000)


def test_threshold_is_gate_not_monthly_deduction(monkeypatch):
    plan, rows = _plan(wife_income=1_800_000)
    plan.wallets.wife_household_monthly = 1_000_000
    row = _run(plan, rows, monkeypatch)
    annual_surplus = (
        row.wife_personal_income
        - row.wife_debt_payment
        - row.wife_personal_spending
        - row.wife_base_nisa_contributed
    )
    monthly_surplus = annual_surplus / 12
    assert monthly_surplus > plan.wallets.wife_contribution_threshold_monthly
    assert row.wife_household_paid == pytest.approx(annual_surplus)


def test_debt_is_paid_before_wife_household_contribution(monkeypatch):
    plan, rows = _plan(wife_income=1_800_000)
    plan.personal_debts = [
        PersonalDebt(
            debt_id="student",
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=12,
        )
    ]
    row = _run(plan, rows, monkeypatch)
    assert row.wife_debt_payment == pytest.approx(180_000)
    annual_surplus = (
        row.wife_personal_income
        - row.wife_debt_payment
        - row.wife_personal_spending
        - row.wife_base_nisa_contributed
    )
    expected = (
        min(plan.wallets.wife_household_monthly * 12, annual_surplus)
        if annual_surplus / 12 > plan.wallets.wife_contribution_threshold_monthly
        else 0
    )
    assert row.wife_household_paid == pytest.approx(expected)


def test_cash_never_goes_negative_and_unmet_is_separate(monkeypatch):
    plan, rows = _plan(wife_income=0, household=1_200_000)
    plan.wallets.initial_husband_cash = 0
    plan.husband.annual_gross_income = 0
    rows[0].husband_gross = 0
    rows[0].wife_gross = 0
    rows[0].salary_net = 0
    rows[0].total_income = 0
    row = _run(plan, rows, monkeypatch)
    assert row.husband_cash_end == 0
    assert row.wife_cash_end == 0
    assert row.unmet_amount > 0


def test_auto_invest_does_not_sweep_wife_surplus(monkeypatch):
    plan, rows = _plan(wife_income=3_600_000, household=0)
    plan.wallets.auto_invest_enabled = True
    plan.wallets.husband_target_cash = 100_000_000
    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")
    wife.monthly_contribution = 0
    row = _run(plan, rows, monkeypatch)
    assert row.wife_additional_nisa_contributed == 0
    assert row.wife_nisa_contributed == 0
    assert row.wife_cash_end == pytest.approx(
        row.wife_personal_income - row.wife_personal_spending
    )


def test_spousal_nisa_transfer_is_capped_at_annual_management_limit(monkeypatch):
    plan, rows = _plan(wife_income=0, household=0)
    plan.wallets.initial_husband_cash = 10_000_000
    plan.wallets.husband_target_cash = 1_000_000
    plan.wallets.auto_invest_enabled = True
    plan.wallets.spouse_nisa_transfer_enabled = True
    plan.wallets.spouse_nisa_annual_management_limit = 1_100_000
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.lifetime_limit = 0
    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")
    wife.monthly_contribution = 0
    row = _run(plan, rows, monkeypatch)
    assert row.spouse_nisa_transfer == pytest.approx(1_100_000)
    assert row.wife_nisa_contributed == pytest.approx(1_100_000)

def test_husband_monthly_cash_goal_is_reserved_before_base_nisa(monkeypatch):
    plan, rows = _plan(wife_income=0, household=0)
    plan.wallets.initial_husband_cash = 1_000_000
    plan.wallets.husband_minimum_cash = 1_000_000
    plan.wallets.husband_target_cash = 2_000_000
    plan.wallets.husband_monthly_saving_until_target = 50_000
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.monthly_contribution = 500_000
    husband.annual_limit = 100_000_000
    husband.lifetime_limit = 100_000_000
    rows[0].husband_gross = 4_200_000
    rows[0].salary_net = 4_200_000
    rows[0].total_income = 4_200_000
    row = _run(plan, rows, monkeypatch)
    assert row.husband_cash_end == pytest.approx(1_600_000)
    assert row.husband_minimum_cash_breach_months == 0


def test_husband_minimum_line_breach_is_reported(monkeypatch):
    plan, rows = _plan(wife_income=0, household=600_000)
    plan.wallets.initial_husband_cash = 1_000_000
    plan.wallets.husband_minimum_cash = 1_000_000
    plan.husband.annual_gross_income = 0
    rows[0].husband_gross = 0
    rows[0].salary_net = 0
    rows[0].total_income = 0
    row = _run(plan, rows, monkeypatch)
    assert row.husband_cash_end == pytest.approx(400_000)
    assert row.husband_minimum_cash_shortfall == pytest.approx(600_000)
    assert row.husband_minimum_cash_breach_months == 12
    assert any("最低維持預金" in warning for warning in row.warnings)


def test_wife_target_cash_gates_automatic_extra_nisa(monkeypatch):
    plan, rows = _plan(wife_income=1_200_000, household=0)
    plan.wallets.initial_wife_cash = 2_900_000
    plan.wallets.wife_personal_spending_monthly = 0
    plan.wallets.wife_target_cash = 3_000_000
    plan.wallets.auto_invest_enabled = True
    plan.wallets.spouse_nisa_transfer_enabled = False
    plan.wallets.husband_target_cash = 100_000_000
    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")
    wife.monthly_contribution = 0
    wife.annual_limit = 100_000_000
    wife.lifetime_limit = 100_000_000
    row = _run(plan, rows, monkeypatch)
    assert row.wife_cash_end == pytest.approx(3_000_000)
    assert row.wife_additional_nisa_contributed == pytest.approx(1_100_000)


def test_nisa_cumulative_progress_and_milestone_events(monkeypatch):
    plan, rows = _plan(wife_income=0, household=0, years=5)
    plan.wallets.husband_minimum_cash = 0
    plan.wallets.husband_target_cash = 0
    plan.wallets.husband_monthly_saving_until_target = 0
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.monthly_contribution = 300_000
    monkeypatch.setattr(
        policy_engine,
        "HousingSimulationEngine",
        lambda _plan: type("RawEngine", (), {"run": lambda self: rows})(),
    )
    results = SimulationEngine(plan).run()
    assert results[0].husband_nisa_contributed == pytest.approx(3_600_000)
    assert results[1].husband_nisa_cumulative_contributed == pytest.approx(7_200_000)
    assert any("夫NISA 1/4" in event for event in results[1].events)
    assert any("夫NISA 1/2" in event for event in results[2].events)
    assert results[4].husband_nisa_cumulative_contributed == pytest.approx(18_000_000)
    assert any("夫NISA 1/1" in event for event in results[4].events)

