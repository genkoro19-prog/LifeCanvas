import pytest

from lifecanvas.engine import SimulationEngine
from lifecanvas.sample import build_genki_family_plan
from lifecanvas.timeline import build_life_events, build_life_periods


def test_husband_continued_employment_is_editable():
    plan = build_genki_family_plan()
    period = next(
        item
        for item in plan.income_periods
        if item.owner == "husband" and item.start_age == 60
    )
    period.annual_gross_income = 2_400_000

    result = next(
        row
        for row in SimulationEngine(plan).run()
        if row.husband_age == 60
    )

    assert result.husband_gross == pytest.approx(2_400_000)


def test_retirement_lump_sum_is_counted_once():
    plan = build_genki_family_plan()
    retirement_pay = next(
        item
        for item in plan.one_time_incomes
        if item.owner == "husband"
    )
    retirement_pay.amount = 10_000_000

    rows = SimulationEngine(plan).run()
    retirement_year = next(row for row in rows if row.husband_age == 60)

    assert retirement_year.one_time_income == 10_000_000
    assert sum(row.one_time_income for row in rows) == 10_000_000


def test_pension_is_separate_from_salary_income():
    plan = build_genki_family_plan()
    result = next(
        row
        for row in SimulationEngine(plan).run()
        if row.husband_age == 65
    )

    assert result.pension_income >= plan.husband.annual_pension
    assert result.total_income >= result.salary_net + result.pension_income


def test_timeline_contains_husband_income_periods():
    plan = build_genki_family_plan()
    event_titles = {event.title for event in build_life_events(plan)}
    period_titles = {period.title for period in build_life_periods(plan)}

    assert "夫: 現在の勤務" in event_titles
    assert "夫: 定年後の継続雇用" in event_titles
    assert "夫 現在の勤務" in period_titles
