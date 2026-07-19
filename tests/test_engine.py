import pytest

from lifecanvas.engine import SimulationEngine
from lifecanvas.sample import build_genki_family_plan


def results():
    return SimulationEngine(build_genki_family_plan()).run()


def test_first_year_is_september_to_december():
    first = results()[0]
    assert first.months == 4
    assert first.husband_gross == pytest.approx(6_200_000 * 4 / 12)
    assert first.wife_gross == pytest.approx(3_500_000 * 4 / 12)


def test_husband_works_for_220_man_until_pension():
    rows = results()
    age_60 = next(row for row in rows if row.husband_age == 60)
    age_64 = next(row for row in rows if row.husband_age == 64)
    age_65 = next(row for row in rows if row.husband_age == 65)
    assert age_60.husband_gross == pytest.approx(2_200_000)
    assert age_64.husband_gross == pytest.approx(2_200_000)
    assert age_65.husband_gross == 0
    assert age_65.pension_income >= 1_800_000
    assert any("定年" in event for event in age_60.events)


def test_wife_income_follows_reference_child_stages():
    rows = results()
    assert rows[10].wife_gross == pytest.approx(576_000)
    assert rows[12].wife_gross == pytest.approx(960_000)
    assert rows[18].wife_gross == pytest.approx(2_200_000)
    assert rows[27].wife_gross == 0


def test_twelve_years_later_is_elementary_stage_not_nursery():
    row = results()[12]
    assert row.wife_age == 40
    assert row.children_ages["第二子"] == 6
    assert row.wife_gross == pytest.approx(960_000)


def test_living_and_initial_housing_are_not_double_counted():
    plan = build_genki_family_plan()
    first = SimulationEngine(plan).run()[0]
    recurring_annualized = (first.core_living_cost + first.housing_cost) / (first.months / 12)
    assert recurring_annualized == pytest.approx(3_000_000, rel=0.02)


def test_cash_saving_goal_is_not_a_consumption_expense():
    first = results()[0]
    assert first.consumption_total == pytest.approx(
        first.core_living_cost + first.housing_cost + first.education_cost + first.car_cost
    )


def test_nisa_contribution_reduces_before_sale():
    plan = build_genki_family_plan()
    plan.initial_cash = 0
    plan.rules.minimum_cash_reserve = 0
    row = SimulationEngine(plan).run()[0]
    assert row.nisa_contributed <= row.nisa_planned
    if row.living_surplus < 0:
        assert row.nisa_contributed == 0


def test_nisa_lifetime_limit_is_respected():
    plan = build_genki_family_plan()
    plan.initial_cash = 100_000_000
    plan.rules.minimum_cash_reserve = 0
    plan.nisa_accounts[0].monthly_contribution = 300_000
    plan.nisa_accounts[0].contribution_changes = {}
    plan.nisa_accounts[0].annual_limit = 3_600_000
    rows = SimulationEngine(plan).run()
    assert all(row.investments_book_value <= 36_000_000 + 1 for row in rows)


def test_move_pays_off_mortgage():
    plan = build_genki_family_plan()
    row = SimulationEngine(plan).run()[plan.housing.move_offset]
    assert row.mortgage_balance == pytest.approx(0)
    assert any("一括返済" in event for event in row.events)
