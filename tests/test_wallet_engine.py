from copy import deepcopy

import pytest

from lifecanvas.ito_sample import build_ito_family_plan
from lifecanvas.sample import build_genki_family_plan
from lifecanvas.wallet_engine import SimulationEngine, recommend_monthly_contributions


def _separate_plan(years: int = 3):
    plan = build_ito_family_plan()
    plan.simulation_years = years
    plan.initial_cash = 0
    plan.wallets.mode = "separate"
    plan.wallets.initial_husband_cash = 10_000_000
    plan.wallets.initial_wife_cash = 10_000_000
    plan.wallets.minimum_personal_cash = 1_000_000
    plan.wallets.target_personal_cash = 1_000_000
    plan.wallets.husband_personal_spending_monthly = 0
    plan.wallets.wife_personal_spending_monthly = 0
    plan.wallets.auto_invest_enabled = False
    for account in plan.nisa_accounts:
        account.monthly_contribution = 0
        account.contribution_changes = {}
    return plan


def test_two_personal_accounts_have_no_joint_cash():
    plan = _separate_plan(2)

    results = SimulationEngine(plan).run()

    for row in results:
        assert row.household_cash_end == 0
        assert row.cash_end == pytest.approx(
            row.husband_cash_end + row.wife_cash_end
        )
        assert row.net_worth == pytest.approx(
            row.cash_end
            + row.investments_market_value
            + row.property_value
            - row.mortgage_balance
        )


def test_household_shortfall_uses_configured_ratio():
    plan = _separate_plan(1)
    plan.wallets.husband_household_monthly = 0
    plan.wallets.wife_household_monthly = 0
    plan.wallets.household_shortfall_husband_percent = 70
    plan.wallets.household_shortfall_wife_percent = 30

    row = SimulationEngine(plan).run()[0]

    assert row.household_shortfall == pytest.approx(row.household_cost_net)
    assert row.husband_household_paid == pytest.approx(
        row.household_shortfall * 0.70
    )
    assert row.wife_household_paid == pytest.approx(
        row.household_shortfall * 0.30
    )
    assert any("夫70%・妻30%" in event for event in row.events)


def test_all_benefits_enter_wife_account():
    plan = build_genki_family_plan()
    plan.simulation_years = 6
    plan.initial_cash = 0
    plan.wallets.initial_husband_cash = 10_000_000
    plan.wallets.initial_wife_cash = 10_000_000
    plan.wife.annual_pension = 0
    plan.one_time_incomes = [
        item for item in plan.one_time_incomes if item.owner != "wife"
    ]
    for stage in plan.wife_work_stages:
        stage.annual_gross_income = 0
    for account in plan.nisa_accounts:
        account.monthly_contribution = 0
        account.contribution_changes = {}

    birth_year = SimulationEngine(plan).run()[5]

    assert birth_year.benefits > 0
    assert birth_year.wife_personal_income == pytest.approx(birth_year.benefits)
    assert any("妻口座へ入金" in event for event in birth_year.events)


def test_child_birth_increases_husband_household_payment():
    plan = _separate_plan(6)
    plan.wallets.husband_household_monthly = 100_000
    plan.wallets.wife_household_monthly = 0
    plan.wallets.husband_child_household_increment_monthly = 50_000
    plan.wallets.wife_child_household_increment_monthly = 0
    plan.wallets.household_shortfall_husband_percent = 0
    plan.wallets.household_shortfall_wife_percent = 100

    results = SimulationEngine(plan).run()
    before_child = results[4]
    birth_year = results[5]

    assert before_child.husband_household_paid / before_child.months == pytest.approx(
        100_000
    )
    assert birth_year.husband_household_paid / birth_year.months == pytest.approx(
        150_000
    )
    assert any("夫の家計負担上限" in event for event in birth_year.events)


def test_wife_money_never_funds_husband_nisa():
    plan = _separate_plan(1)
    plan.wallets.initial_husband_cash = 1_000_000
    plan.wallets.initial_wife_cash = 20_000_000
    plan.wallets.husband_household_monthly = 0
    plan.wallets.wife_household_monthly = 0
    plan.wallets.household_shortfall_husband_percent = 0
    plan.wallets.household_shortfall_wife_percent = 100
    plan.husband.annual_gross_income = 0
    for period in plan.income_periods:
        if period.owner == "husband":
            period.annual_gross_income = 0
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.monthly_contribution = 300_000

    row = SimulationEngine(plan).run()[0]

    assert row.husband_nisa_contributed == 0
    assert row.husband_nisa_market_value == 0
    assert row.wife_cash_end > row.husband_cash_end


def test_nisa_stops_before_owner_cash_drops_below_one_million():
    plan = _separate_plan(1)
    plan.wallets.initial_husband_cash = 1_050_000
    plan.wallets.husband_household_monthly = 0
    plan.wallets.wife_household_monthly = 0
    plan.wallets.household_shortfall_husband_percent = 0
    plan.wallets.household_shortfall_wife_percent = 100
    plan.husband.annual_gross_income = 0
    for period in plan.income_periods:
        if period.owner == "husband":
            period.annual_gross_income = 0
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    husband.monthly_contribution = 100_000

    row = SimulationEngine(plan).run()[0]

    assert row.husband_cash_end == pytest.approx(1_000_000)
    assert row.husband_nisa_contributed == pytest.approx(50_000)
    assert any("手元現金100万円" in event for event in row.events)


def test_recommendation_keeps_both_accounts_above_floor():
    plan = _separate_plan(3)
    plan.wallets.initial_husband_cash = 20_000_000
    plan.wallets.initial_wife_cash = 20_000_000

    recommendation = recommend_monthly_contributions(plan)

    assert 0 < recommendation.husband_monthly <= 300_000
    assert 0 < recommendation.wife_monthly <= 300_000

    trial = deepcopy(plan)
    next(
        account for account in trial.nisa_accounts if account.owner == "husband"
    ).monthly_contribution = recommendation.husband_monthly
    next(
        account for account in trial.nisa_accounts if account.owner == "wife"
    ).monthly_contribution = recommendation.wife_monthly
    results = SimulationEngine(trial).run()

    assert min(row.husband_cash_end for row in results) >= trial.wallets.minimum_personal_cash
    assert min(row.wife_cash_end for row in results) >= trial.wallets.minimum_personal_cash
