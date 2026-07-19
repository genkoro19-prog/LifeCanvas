from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from .models import ProjectPlan


@dataclass(frozen=True)
class LifeEvent:
    offset: int
    category: str
    title: str
    detail: str = ""


@dataclass(frozen=True)
class LifePeriod:
    start_offset: int
    end_offset: int
    category: str
    title: str


def build_life_events(plan: ProjectPlan) -> list[LifeEvent]:
    """Build the major events shown on the visual life timeline."""
    events: list[LifeEvent] = []

    for child in plan.children:
        milestones = [
            (0, f"{child.name}誕生", "家族が増える"),
            (6, f"{child.name} 小学校入学", "教育費の段階が変わる"),
            (12, f"{child.name} 中学校入学", "教育費と妻の働き方を確認"),
            (15, f"{child.name} 高校入学", "進学費用を確認"),
            (18, f"{child.name} 大学入学", "教育費のピーク"),
            (22, f"{child.name} 大学卒業", "教育費終了の目安"),
        ]
        for age, title, detail in milestones:
            offset = child.birth_offset + age
            if offset < plan.simulation_years:
                events.append(LifeEvent(offset, "family", title, detail))

    for stage in plan.wife_work_stages:
        if stage.start_offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    stage.start_offset,
                    "work",
                    f"妻: {stage.label}",
                    f"年収 {stage.annual_gross_income / 10_000:,.0f}万円",
                )
            )

    husband_retirement = plan.husband.retirement_age - plan.husband.current_age
    if 0 <= husband_retirement < plan.simulation_years:
        events.append(LifeEvent(husband_retirement, "work", "夫 定年", f"{plan.husband.retirement_age}歳"))

    wife_retirement = plan.wife.retirement_age - plan.wife.current_age
    if 0 <= wife_retirement < plan.simulation_years:
        events.append(LifeEvent(wife_retirement, "work", "妻 退職", f"{plan.wife.retirement_age}歳"))

    for person, label in ((plan.husband, "夫"), (plan.wife, "妻")):
        pension_offset = person.pension_start_age - person.current_age
        if 0 <= pension_offset < plan.simulation_years:
            events.append(LifeEvent(pension_offset, "work", f"{label} 年金開始", f"{person.pension_start_age}歳"))

    mortgage = plan.housing.mortgage
    events.append(
        LifeEvent(
            0,
            "housing",
            "住宅ローン開始",
            f"{mortgage.principal / 10_000:,.0f}万円・{mortgage.initial_rate_percent:.2f}%",
        )
    )
    if mortgage.annual_rate_step_percent > 0 and mortgage.max_rate_percent > mortgage.initial_rate_percent:
        max_rate_offset = ceil(
            (mortgage.max_rate_percent - mortgage.initial_rate_percent)
            / mortgage.annual_rate_step_percent
        )
        if max_rate_offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    max_rate_offset,
                    "housing",
                    "住宅ローン金利が上限へ",
                    f"{mortgage.max_rate_percent:.2f}%",
                )
            )

    if plan.housing.move_offset is not None and plan.housing.move_offset < plan.simulation_years:
        events.append(
            LifeEvent(
                plan.housing.move_offset,
                "housing",
                "住み替え・ローン一括返済",
                f"引っ越し費用 {plan.housing.move_cost / 10_000:,.0f}万円",
            )
        )
    elif mortgage.term_years < plan.simulation_years:
        events.append(LifeEvent(mortgage.term_years, "housing", "住宅ローン完済", "予定どおり返済した場合"))

    car = plan.car
    if car.purchase_offset < plan.simulation_years:
        events.append(
            LifeEvent(
                car.purchase_offset,
                "car",
                "車を購入",
                f"{car.purchase_price / 10_000:,.0f}万円",
            )
        )
    if car.replacement_cycle_years:
        offset = car.purchase_offset + car.replacement_cycle_years
        while offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    offset,
                    "car",
                    "車を買い替え",
                    f"{car.replacement_price / 10_000:,.0f}万円",
                )
            )
            offset += car.replacement_cycle_years

    for account in plan.nisa_accounts:
        owner = "夫" if account.owner == "husband" else "妻"
        events.append(
            LifeEvent(
                0,
                "assets",
                f"{owner} NISA開始",
                f"月 {account.monthly_contribution / 10_000:,.1f}万円",
            )
        )
        for offset, amount in sorted(account.contribution_changes.items()):
            if offset < plan.simulation_years:
                events.append(
                    LifeEvent(
                        offset,
                        "assets",
                        f"{owner} NISA積立変更",
                        f"月 {amount / 10_000:,.1f}万円",
                    )
                )

    return sorted(events, key=lambda event: (event.offset, event.category, event.title))


def build_life_periods(plan: ProjectPlan) -> list[LifePeriod]:
    """Build long-running states that are easier to understand as horizontal bars."""
    periods: list[LifePeriod] = []

    mortgage_end = plan.housing.mortgage.term_years
    if plan.housing.move_offset is not None:
        mortgage_end = min(mortgage_end, plan.housing.move_offset)
    periods.append(
        LifePeriod(
            0,
            min(plan.simulation_years - 1, max(0, mortgage_end)),
            "housing",
            "住宅ローン返済期間",
        )
    )

    for child in plan.children:
        start = child.birth_offset
        end = min(plan.simulation_years - 1, child.birth_offset + 21)
        if start < plan.simulation_years:
            periods.append(LifePeriod(start, end, "family", f"{child.name} 子育て・教育期間"))

    for stage in plan.wife_work_stages:
        end = stage.end_offset if stage.end_offset is not None else plan.simulation_years - 1
        if stage.start_offset < plan.simulation_years:
            periods.append(
                LifePeriod(
                    stage.start_offset,
                    min(plan.simulation_years - 1, end),
                    "work",
                    stage.label,
                )
            )

    return periods
