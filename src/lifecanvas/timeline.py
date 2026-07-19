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
    owner: str | None = None


@dataclass(frozen=True)
class LifePeriod:
    start_offset: int
    end_offset: int
    category: str
    title: str
    owner: str | None = None


def build_life_events(plan: ProjectPlan) -> list[LifeEvent]:
    events: list[LifeEvent] = []

    for child in plan.children:
        milestones = [
            (0, f"{child.name}誕生", "家族が増える"),
            (6, f"{child.name} 小学校入学", "教育費の段階が変わる"),
            (12, f"{child.name} 中学校入学", "教育費と働き方を確認"),
            (15, f"{child.name} 高校入学", "進学費用を確認"),
            (18, f"{child.name} 大学入学", "教育費のピーク"),
            (22, f"{child.name} 大学卒業", "教育費終了の目安"),
        ]
        for age, title, detail in milestones:
            offset = child.birth_offset + age
            if offset < plan.simulation_years:
                events.append(LifeEvent(offset, "family", title, detail))

    husband_periods = [
        period for period in plan.income_periods if period.owner == "husband"
    ]
    if husband_periods:
        for period in husband_periods:
            offset = period.start_age - plan.husband.current_age
            if 0 <= offset < plan.simulation_years:
                events.append(
                    LifeEvent(
                        offset,
                        "work",
                        f"夫: {period.label}",
                        f"年収 {period.annual_gross_income / 10_000:,.0f}万円",
                        "husband",
                    )
                )
    else:
        events.append(
            LifeEvent(
                0,
                "work",
                "夫: 現在の勤務",
                f"年収 {plan.husband.annual_gross_income / 10_000:,.0f}万円",
                "husband",
            )
        )

    wife_periods = [
        period for period in plan.income_periods if period.owner == "wife"
    ]
    if wife_periods:
        for period in wife_periods:
            offset = period.start_age - plan.wife.current_age
            if 0 <= offset < plan.simulation_years:
                events.append(
                    LifeEvent(
                        offset,
                        "work",
                        f"妻: {period.label}",
                        f"年収 {period.annual_gross_income / 10_000:,.0f}万円",
                        "wife",
                    )
                )
    else:
        for stage in plan.wife_work_stages:
            if stage.start_offset < plan.simulation_years:
                events.append(
                    LifeEvent(
                        stage.start_offset,
                        "work",
                        f"妻: {stage.label}",
                        f"年収 {stage.annual_gross_income / 10_000:,.0f}万円",
                        "wife",
                    )
                )

    for person, label, owner in (
        (plan.husband, "夫", "husband"),
        (plan.wife, "妻", "wife"),
    ):
        retirement_offset = person.retirement_age - person.current_age
        if 0 <= retirement_offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    retirement_offset,
                    "work",
                    f"{label} 定年・退職",
                    f"{person.retirement_age}歳",
                    owner,
                )
            )
        pension_offset = person.pension_start_age - person.current_age
        if 0 <= pension_offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    pension_offset,
                    "work",
                    f"{label} 年金開始",
                    f"年 {person.annual_pension / 10_000:,.0f}万円",
                    owner,
                )
            )

    for item in plan.one_time_incomes:
        current_age = (
            plan.husband.current_age
            if item.owner == "husband"
            else plan.wife.current_age
            if item.owner == "wife"
            else 0
        )
        offset = item.age - current_age if item.owner != "household" else item.age
        if 0 <= offset < plan.simulation_years:
            events.append(
                LifeEvent(
                    offset,
                    "work",
                    item.label,
                    f"{item.amount / 10_000:,.0f}万円",
                    item.owner if item.owner != "household" else None,
                )
            )

    mortgage = plan.housing.mortgage
    events.append(
        LifeEvent(
            0,
            "housing",
            "住宅ローン開始",
            f"{mortgage.principal / 10_000:,.0f}万円・{mortgage.initial_rate_percent:.2f}%",
        )
    )
    if (
        mortgage.annual_rate_step_percent > 0
        and mortgage.max_rate_percent > mortgage.initial_rate_percent
    ):
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

    if (
        plan.housing.move_offset is not None
        and plan.housing.move_offset < plan.simulation_years
    ):
        events.append(
            LifeEvent(
                plan.housing.move_offset,
                "housing",
                "住み替え・ローン一括返済",
                f"引っ越し費用 {plan.housing.move_cost / 10_000:,.0f}万円",
            )
        )
    elif mortgage.term_years < plan.simulation_years:
        events.append(
            LifeEvent(
                mortgage.term_years,
                "housing",
                "住宅ローン完済",
                "予定どおり返済した場合",
            )
        )

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
        owner_label = "夫" if account.owner == "husband" else "妻"
        events.append(
            LifeEvent(
                0,
                "assets",
                f"{owner_label} NISA開始",
                f"月 {account.monthly_contribution / 10_000:,.1f}万円",
                account.owner,
            )
        )
        for offset, amount in sorted(account.contribution_changes.items()):
            if offset < plan.simulation_years:
                events.append(
                    LifeEvent(
                        offset,
                        "assets",
                        f"{owner_label} NISA積立変更",
                        f"月 {amount / 10_000:,.1f}万円",
                        account.owner,
                    )
                )

    return sorted(events, key=lambda event: (event.offset, event.category, event.title))


def build_life_periods(plan: ProjectPlan) -> list[LifePeriod]:
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
        if child.birth_offset < plan.simulation_years:
            periods.append(
                LifePeriod(
                    child.birth_offset,
                    min(plan.simulation_years - 1, child.birth_offset + 21),
                    "family",
                    f"{child.name} 子育て・教育期間",
                )
            )

    for income in plan.income_periods:
        person = plan.husband if income.owner == "husband" else plan.wife
        start = income.start_age - person.current_age
        end = (
            income.end_age - person.current_age - 1
            if income.end_age is not None
            else plan.simulation_years - 1
        )
        if 0 <= start < plan.simulation_years:
            periods.append(
                LifePeriod(
                    start,
                    min(plan.simulation_years - 1, end),
                    "work",
                    f"{'夫' if income.owner == 'husband' else '妻'} {income.label}",
                    income.owner,
                )
            )

    if not any(period.owner == "wife" for period in plan.income_periods):
        for stage in plan.wife_work_stages:
            end = (
                stage.end_offset - 1
                if stage.end_offset is not None
                else plan.simulation_years - 1
            )
            if stage.start_offset < plan.simulation_years:
                periods.append(
                    LifePeriod(
                        stage.start_offset,
                        min(plan.simulation_years - 1, end),
                        "work",
                        stage.label,
                        "wife",
                    )
                )

    return periods
