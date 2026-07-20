from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .models import (
    EducationCostPlan,
    IncomePeriod,
    ProjectPlan,
    SocialInsuranceMode,
)
from .wallet_engine import SimulationEngine


@dataclass(frozen=True)
class PlanCheck:
    level: str
    title: str
    detail: str
    suggestion: str


@dataclass(frozen=True)
class ScenarioSummary:
    label: str
    retirement_net_worth: float
    minimum_cash: float
    final_net_worth: float
    warning_years: int
    note: str


@dataclass(frozen=True)
class ImpactItem:
    label: str
    improvement: float
    note: str


def _minimum_owned_cash(plan: ProjectPlan, results) -> float:
    if not results:
        return 0.0
    if plan.wallets.mode == "separate":
        return min(
            min(row.husband_cash_end, row.wife_cash_end)
            for row in results
        )
    return min(row.cash_end for row in results)


def _warning_years(results) -> int:
    return sum(bool(row.warnings) for row in results)


def _nisa_for(plan: ProjectPlan, owner: str):
    return next(
        (account for account in plan.nisa_accounts if account.owner == owner),
        None,
    )


def apply_wife_work_preset(plan: ProjectPlan, preset: str) -> None:
    """Create a practical wife-income path from a small preset selection.

    The preset deliberately stays simple. Detailed ages and amounts remain editable in
    the advanced income table after the preset has been applied.
    """

    plan.wife_work_preset = preset
    if preset == "custom":
        return

    current_age = plan.wife.current_age
    retirement_age = plan.wife.retirement_age
    current_income = max(0.0, plan.wife.annual_gross_income)
    child_offsets = sorted(child.birth_offset for child in plan.children)

    if not child_offsets:
        plan.income_periods = [
            period for period in plan.income_periods if period.owner != "wife"
        ] + [
            IncomePeriod(
                owner="wife",
                label="現在の勤務",
                start_age=current_age,
                end_age=retirement_age,
                annual_gross_income=current_income,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            )
        ]
        return

    first_birth_age = min(retirement_age, current_age + child_offsets[0])
    last_birth_age = min(retirement_age, current_age + child_offsets[-1])
    leave_end_age = min(retirement_age, last_birth_age + 1)
    youngest_school_age = min(retirement_age, last_birth_age + 6)
    youngest_junior_age = min(retirement_age, last_birth_age + 12)

    periods: list[IncomePeriod] = []

    def add_period(
        label: str,
        start_age: int,
        end_age: int,
        income: float,
        mode: SocialInsuranceMode,
        benefit: float = 0.0,
    ) -> None:
        if end_age <= start_age:
            return
        periods.append(
            IncomePeriod(
                owner="wife",
                label=label,
                start_age=start_age,
                end_age=end_age,
                annual_gross_income=max(0.0, income),
                annual_benefit=max(0.0, benefit),
                social_insurance_mode=mode,
            )
        )

    add_period(
        "出産前の勤務",
        current_age,
        first_birth_age,
        current_income,
        SocialInsuranceMode.EMPLOYEE,
    )
    add_period(
        "産休・育休",
        first_birth_age,
        leave_end_age,
        0.0,
        SocialInsuranceMode.NONE,
        current_income * 0.55,
    )

    if preset == "early":
        add_period(
            "早期復職・時短勤務",
            leave_end_age,
            youngest_school_age,
            current_income * 0.85,
            SocialInsuranceMode.EMPLOYEE,
        )
        add_period(
            "通常勤務へ復帰",
            youngest_school_age,
            retirement_age,
            current_income,
            SocialInsuranceMode.EMPLOYEE,
        )
    elif preset == "care":
        add_period(
            "育児優先の短時間勤務",
            leave_end_age,
            youngest_school_age,
            current_income * 0.50,
            SocialInsuranceMode.DEPENDENT,
        )
        add_period(
            "小学生期のパート勤務",
            youngest_school_age,
            youngest_junior_age,
            current_income * 0.65,
            SocialInsuranceMode.EMPLOYEE,
        )
        add_period(
            "中学生以降の勤務",
            youngest_junior_age,
            retirement_age,
            current_income * 0.80,
            SocialInsuranceMode.EMPLOYEE,
        )
    else:
        add_period(
            "標準復職・時短勤務",
            leave_end_age,
            youngest_school_age,
            current_income * 0.75,
            SocialInsuranceMode.EMPLOYEE,
        )
        add_period(
            "小学生期の勤務",
            youngest_school_age,
            youngest_junior_age,
            current_income * 0.90,
            SocialInsuranceMode.EMPLOYEE,
        )
        add_period(
            "通常勤務へ復帰",
            youngest_junior_age,
            retirement_age,
            current_income,
            SocialInsuranceMode.EMPLOYEE,
        )

    plan.income_periods = [
        period for period in plan.income_periods if period.owner != "wife"
    ] + periods


def check_plan(plan: ProjectPlan) -> list[PlanCheck]:
    checks: list[PlanCheck] = []
    wallet = plan.wallets

    if wallet.mode == "separate":
        personal_total = (
            wallet.husband_personal_spending_monthly
            + wallet.wife_personal_spending_monthly
        )
        if plan.living_cost.includes_personal_spending and personal_total > 0:
            checks.append(
                PlanCheck(
                    "warning",
                    "生活費と個人支出が重複しています",
                    "基本生活費に夫婦のお小遣い等を含める設定ですが、個人支出にも金額があります。",
                    "かんたん入力では個人支出を0円にするか、生活費に含めない設定へ変更してください。",
                )
            )

        owned_cash = wallet.initial_husband_cash + wallet.initial_wife_cash
        required_cash = wallet.minimum_personal_cash * 2
        if owned_cash + 1 < required_cash:
            checks.append(
                PlanCheck(
                    "warning",
                    "現在預金が最低手元現金を下回っています",
                    f"夫婦の現在預金は合計{owned_cash/10_000:,.0f}万円ですが、各自{wallet.minimum_personal_cash/10_000:,.0f}万円を残すには合計{required_cash/10_000:,.0f}万円必要です。",
                    "最低額に達するまではNISAを抑える前提で確認してください。",
                )
            )

    child_offsets = sorted(child.birth_offset for child in plan.children)
    husband_nisa = _nisa_for(plan, "husband")
    if child_offsets and husband_nisa:
        previous = husband_nisa.monthly_contribution
        for start in sorted(husband_nisa.contribution_changes):
            amount = husband_nisa.contribution_changes[start]
            if any(abs(start - birth) <= 1 for birth in child_offsets) and amount > previous:
                checks.append(
                    PlanCheck(
                        "warning",
                        "出産時期に夫NISAが増額されています",
                        f"子どもの誕生前後に、夫NISAが月{previous/10_000:,.1f}万円から月{amount/10_000:,.1f}万円へ増えます。",
                        "育休・教育費が始まる時期は、増額せず現金を優先する設定が安全です。",
                    )
                )
            previous = amount

    if plan.housing.move_mode != "none" and plan.housing.move_offset is not None:
        if plan.housing.move_offset < plan.housing.mortgage.term_years:
            annual_gap = max(
                0.0,
                plan.housing.new_home_monthly_cost * 12
                - plan.housing.old_home_net_rent_annual,
            )
            checks.append(
                PlanCheck(
                    "notice",
                    "住宅ローン返済中の住み替えが基準プランに入っています",
                    f"住み替え後の新居費と家賃収入の差は年約{annual_gap/10_000:,.0f}万円です。旧居ローンも残る可能性があります。",
                    "まだ未定なら、基準プランでは『住み替えなし』にして比較シナリオで確認してください。",
                )
            )

    for period in plan.income_periods:
        if period.owner != "wife" or period.annual_benefit <= 0:
            continue
        end_age = period.end_age or plan.wife.retirement_age
        if end_age - period.start_age > 2:
            checks.append(
                PlanCheck(
                    "notice",
                    "妻の給付期間が長く設定されています",
                    f"『{period.label}』で給付を{end_age-period.start_age}年間受け取る設定です。",
                    "給付期間と復職時期が実際の予定に近いか確認してください。",
                )
            )
            break

    if plan.wife.retirement_age < 60:
        checks.append(
            PlanCheck(
                "notice",
                "妻の退職年齢が早めです",
                f"妻は{plan.wife.retirement_age}歳で退職する設定です。",
                "確定していない場合は60歳前後を基準にし、早期退職を慎重シナリオで確認してください。",
            )
        )

    return checks


def scenario_summaries(plan: ProjectPlan) -> list[ScenarioSummary]:
    variants: list[tuple[str, ProjectPlan, str]] = []

    base = deepcopy(plan)
    variants.append(("基準プラン", base, "現在入力している、最も可能性が高い計画"))

    cautious = deepcopy(plan)
    for account in cautious.nisa_accounts:
        account.annual_return_percent = min(account.annual_return_percent, 2.0)
    cautious.housing.mortgage.max_rate_percent = min(
        5.0,
        max(
            cautious.housing.mortgage.max_rate_percent,
            cautious.housing.mortgage.initial_rate_percent + 1.0,
        ),
    )
    first_child_age = (
        cautious.wife.current_age + min(child.birth_offset for child in cautious.children)
        if cautious.children
        else cautious.wife.current_age
    )
    for period in cautious.income_periods:
        if period.owner == "wife" and period.start_age >= first_child_age:
            period.annual_gross_income *= 0.8
            period.annual_benefit *= 0.9
    variants.append(("慎重プラン", cautious, "運用2%・金利上昇・妻の復職収入20%減"))

    optimistic = deepcopy(plan)
    for account in optimistic.nisa_accounts:
        account.annual_return_percent = max(account.annual_return_percent, 5.0)
    optimistic.housing.mortgage.max_rate_percent = max(
        optimistic.housing.mortgage.initial_rate_percent,
        min(optimistic.housing.mortgage.max_rate_percent, 2.0),
    )
    for period in optimistic.income_periods:
        if period.owner == "wife" and period.start_age >= first_child_age:
            period.annual_gross_income *= 1.1
    variants.append(("楽観プラン", optimistic, "運用5%・金利上昇を抑制・妻の復職収入10%増"))

    summaries: list[ScenarioSummary] = []
    for label, variant, note in variants:
        results = SimulationEngine(variant).run()
        retirement = next(
            (
                row
                for row in results
                if row.husband_age == variant.husband.retirement_age
            ),
            results[-1],
        )
        summaries.append(
            ScenarioSummary(
                label=label,
                retirement_net_worth=retirement.net_worth,
                minimum_cash=_minimum_owned_cash(variant, results),
                final_net_worth=results[-1].net_worth,
                warning_years=_warning_years(results),
                note=note,
            )
        )
    return summaries


def impact_ranking(plan: ProjectPlan, baseline_results=None) -> list[ImpactItem]:
    baseline = baseline_results or SimulationEngine(plan).run()
    if not baseline:
        return []
    baseline_final = baseline[-1].net_worth
    variants: list[tuple[str, ProjectPlan, str]] = []

    if plan.housing.move_mode != "none":
        no_move = deepcopy(plan)
        no_move.housing.move_mode = "none"
        no_move.housing.move_offset = None
        variants.append(("住み替え計画", no_move, "住み替えを基準プランから外した場合"))

    if (
        plan.wallets.husband_personal_spending_monthly
        + plan.wallets.wife_personal_spending_monthly
        > 0
    ):
        no_personal = deepcopy(plan)
        no_personal.wallets.husband_personal_spending_monthly = 0
        no_personal.wallets.wife_personal_spending_monthly = 0
        variants.append(("夫婦の個人支出", no_personal, "個人支出を生活費に含めた場合"))

    if any(car.enabled for car in plan.cars):
        no_cars = deepcopy(plan)
        for car in no_cars.cars:
            car.enabled = False
        no_cars.car.enabled = False
        variants.append(("車の購入・維持", no_cars, "車関連費を除いた場合"))

    if plan.children:
        no_education = deepcopy(plan)
        no_education.education = EducationCostPlan(
            age_0_2=0,
            age_3_5=0,
            elementary=0,
            junior_high=0,
            high_school=0,
            university=0,
        )
        variants.append(("教育費", no_education, "教育費を除いた場合"))

    future_wife_periods = [
        period
        for period in plan.income_periods
        if period.owner == "wife"
        and period.start_age > plan.wife.current_age
        and period.annual_gross_income < plan.wife.annual_gross_income
    ]
    if future_wife_periods:
        full_income = deepcopy(plan)
        for period in full_income.income_periods:
            if period.owner == "wife" and period.start_age >= full_income.wife.current_age:
                period.annual_gross_income = full_income.wife.annual_gross_income
                period.annual_benefit = 0
                period.social_insurance_mode = SocialInsuranceMode.EMPLOYEE
        variants.append(("妻の収入減少", full_income, "妻が現在年収を維持した場合との差"))

    impacts: list[ImpactItem] = []
    for label, variant, note in variants:
        results = SimulationEngine(variant).run()
        improvement = results[-1].net_worth - baseline_final
        if improvement > 1:
            impacts.append(ImpactItem(label, improvement, note))

    impacts.sort(key=lambda item: item.improvement, reverse=True)
    return impacts[:5]
