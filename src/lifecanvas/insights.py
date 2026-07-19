from __future__ import annotations

from dataclasses import dataclass

from .models import ProjectPlan, YearResult


@dataclass(frozen=True)
class PlanInsights:
    status: str
    status_note: str
    retirement_year: int
    retirement_min_cash: float
    final_net_worth: float
    difficult_years: tuple[YearResult, ...]


def analyze_plan(plan: ProjectPlan, results: list[YearResult]) -> PlanInsights:
    if not results:
        raise ValueError("results must not be empty")

    retirement_start_age = min(
        plan.husband.pension_start_age,
        plan.wife.pension_start_age,
    )
    retirement_rows = [
        row for row in results if row.husband_age >= retirement_start_age
    ] or [results[-1]]
    retirement_min_cash = min(row.cash_end for row in retirement_rows)
    shortages = [
        row
        for row in results
        if any("資金ショート" in warning for warning in row.warnings)
    ]

    if shortages:
        status = "要見直し"
        status_note = f"{shortages[0].calendar_year}年に資金ショート"
    elif retirement_min_cash < plan.rules.minimum_cash_reserve:
        status = "注意"
        status_note = "老後の現預金が目標額を下回ります"
    elif results[-1].net_worth < 0:
        status = "注意"
        status_note = "最終年の純資産がマイナスです"
    else:
        status = "概ね安定"
        status_note = "現在の前提では重大な資金ショートなし"

    difficult_years = tuple(
        sorted(results, key=lambda row: (row.living_surplus, row.cash_end))[:3]
    )
    return PlanInsights(
        status=status,
        status_note=status_note,
        retirement_year=retirement_rows[0].calendar_year,
        retirement_min_cash=retirement_min_cash,
        final_net_worth=results[-1].net_worth,
        difficult_years=difficult_years,
    )


def dominant_expense(row: YearResult) -> str:
    expenses = {
        "生活費": row.core_living_cost,
        "住宅": row.housing_cost,
        "教育": row.education_cost,
        "車": row.car_cost,
        "臨時イベント": row.life_event_expense,
    }
    return max(expenses, key=expenses.get)
