from copy import deepcopy

import pytest

from lifecanvas.ito_sample import build_ito_family_plan
from lifecanvas.wallet_engine import SimulationEngine, recommend_monthly_contributions


def _separate_plan(years: int = 3):
    plan = build_ito_family_plan()
    plan.simulation_years = years
    plan.wallets.mode = "separate"
    plan.wallets.minimum_household_cash = 0
    plan.wallets.target_household_cash = 0
    plan.wallets.minimum_personal_cash = 0
    plan.wallets.target_personal_cash = 0
    plan.wallets.husband_household_monthly = 0
    plan.wallets.wife_household_monthly = 0
    plan.wallets.husband_personal_spending_monthly = 0
    plan.wallets.wife_personal_spending_monthly = 0
    for account in plan.nisa_accounts:
        account.contribution_changes = {}
    return plan


def test_wife_money_never_funds_husband_nisa():
    plan = _separate_plan(2)
    plan.initial_cash = 100_000_000
    plan.wallets.initial_husband_cash = 0
    plan.wallets.initial_wife_cash = 10_000_000
    plan.husband.annual_gross_income = 0
    for period in plan.income_periods:
        if period.owner == "husband":
            period.annual_gross_income = 0
    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")
    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")
    husband.monthly_contribution = 300_000
    wife.monthly_contribution = 0

    results = SimulationEngine(plan).run()

    assert all(row.husband_nisa_contributed == 0 for row in results)
    assert results[-1].wife_cash_end > plan.wallets.initial_wife_cash
    assert results[-1].husband_nisa_market_value == 0


def test_household_floor_pauses_both_nisa_accounts():
    plan = _separate_plan(1)
    plan.initial_cash = 0
    plan.wallets.minimum_household_cash = 2_000_000
    plan.wallets.target_household_cash = 3_000_000
    plan.wallets.initial_husband_cash = 10_000_000
    plan.wallets.initial_wife_cash = 10_000_000
    for account in plan.nisa_accounts:
        account.monthly_contribution = 100_000

    row = SimulationEngine(plan).run()[0]

    assert row.nisa_contributed == 0
    assert any("共同現預金を守るため" in event for event in row.events)


def test_total_cash_is_sum_of_three_wallets():
    plan = _separate_plan(2)
    plan.initial_cash = 20_000_000
    plan.wallets.initial_husband_cash = 2_000_000
    plan.wallets.initial_wife_cash = 3_000_000
    plan.wallets.husband_household_monthly = 150_000
    plan.wallets.wife_household_monthly = 100_000
    plan.wallets.husband_personal_spending_monthly = 30_000
    plan.wallets.wife_personal_spending_monthly = 50_000

    results = SimulationEngine(plan).run()

    for row in results:
        assert row.cash_end == pytest.approx(
            row.household_cash_end + row.husband_cash_end + row.wife_cash_end
        )
        assert row.net_worth == pytest.approx(
            row.cash_end
            + row.investments_market_value
            + row.property_value
            - row.mortgage_balance
        )


def test_recommendation_is_safe_and_does_not_mix_owners():
    plan = _separate_plan(3)
    plan.initial_cash = 100_000_000
    plan.wallets.initial_husband_cash = 20_000_000
    plan.wallets.initial_wife_cash = 20_000_000
    plan.wallets.minimum_personal_cash = 1_000_000
    plan.wallets.target_personal_cash = 2_000_000

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
