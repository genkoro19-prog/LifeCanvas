from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .engine import NisaState
from .models import (
    IncomePeriod,
    ProjectPlan,
    SocialInsuranceMode,
    WifeWorkStage,
    YearResult,
)
from .rent_engine import SimulationEngine as HousingSimulationEngine
from .tax import estimate_net_salary


@dataclass(frozen=True)
class InvestmentRecommendation:
    husband_monthly: float
    wife_monthly: float
    note: str


def _income_period(plan: ProjectPlan, owner: str, age: int) -> IncomePeriod | None:
    periods = [
        period
        for period in plan.income_periods
        if period.owner == owner and period.active(age)
    ]
    return max(periods, key=lambda item: item.start_age) if periods else None


def _wife_stage(plan: ProjectPlan, offset: int) -> WifeWorkStage | None:
    stages = [stage for stage in plan.wife_work_stages if stage.active(offset)]
    return max(stages, key=lambda item: item.start_offset) if stages else None


def _mode_and_benefit(
    plan: ProjectPlan,
    owner: str,
    age: int,
    offset: int,
    ratio: float,
) -> tuple[SocialInsuranceMode, float]:
    period = _income_period(plan, owner, age)
    if period:
        return period.social_insurance_mode, period.annual_benefit * ratio
    if owner == "husband":
        if age >= plan.husband.retirement_age:
            return SocialInsuranceMode.NONE, 0.0
        return plan.husband.social_insurance_mode, 0.0
    stage = _wife_stage(plan, offset)
    if age >= plan.wife.retirement_age or stage is None:
        return SocialInsuranceMode.NONE, 0.0
    return stage.social_insurance_mode, stage.annual_benefit * ratio


def _owner_one_time(plan: ProjectPlan, owner: str, age: int) -> float:
    return sum(
        item.amount
        for item in plan.one_time_incomes
        if item.owner == owner and item.age == age
    )


def _household_one_time(plan: ProjectPlan, offset: int) -> float:
    return sum(
        item.amount
        for item in plan.one_time_incomes
        if item.owner == "household" and item.age == offset
    )


def _split_salary_net(
    plan: ProjectPlan,
    row: YearResult,
    husband_mode: SocialInsuranceMode,
    wife_mode: SocialInsuranceMode,
) -> tuple[float, float]:
    """Split the core engine's exact family take-home while keeping housing-credit effects."""

    husband = estimate_net_salary(row.husband_gross, husband_mode, plan.rules).net
    wife = estimate_net_salary(row.wife_gross, wife_mode, plan.rules).net
    estimated = husband + wife
    difference = row.salary_net - estimated
    if difference >= 0:
        # The core engine applies the housing-loan tax credit to the husband.
        husband += difference
    elif estimated > 0:
        scale = max(0.0, row.salary_net / estimated)
        husband *= scale
        wife *= scale
    return max(0.0, husband), max(0.0, wife)


def _clean_finance_messages(messages: list[str]) -> list[str]:
    ignored = (
        "NISA",
        "手元資金を守るため",
        "資金確保のため",
        "資金ショート",
        "現預金が目標額",
    )
    return [message for message in messages if not any(token in message for token in ignored)]


class SimulationEngine:
    """Run LifeCanvas with either the legacy pooled wallet or three owned wallets."""

    def __init__(self, plan: ProjectPlan):
        self.plan = plan

    def run(self) -> list[YearResult]:
        if self.plan.wallets.mode != "separate":
            results = HousingSimulationEngine(self.plan).run()
            for row in results:
                row.household_cash_end = row.cash_end
                row.recommended_husband_monthly = next(
                    (
                        account.monthly_for_offset(row.offset)
                        for account in self.plan.nisa_accounts
                        if account.owner == "husband"
                    ),
                    0.0,
                )
                row.recommended_wife_monthly = next(
                    (
                        account.monthly_for_offset(row.offset)
                        for account in self.plan.nisa_accounts
                        if account.owner == "wife"
                    ),
                    0.0,
                )
            return results

        return self._run_separate()

    def _run_separate(self) -> list[YearResult]:
        plan = self.plan
        wallets = plan.wallets

        # The established engine remains the source of truth for tax, mortgage, housing,
        # education, cars and events. NISA is disabled in this pass and rebuilt per owner.
        physical_plan = deepcopy(plan)
        for account in physical_plan.nisa_accounts:
            account.monthly_contribution = 0
            account.contribution_changes = {}
        physical_plan.rules.minimum_cash_reserve = 0
        raw_results = HousingSimulationEngine(physical_plan).run()

        household_cash = plan.initial_cash
        husband_cash = wallets.initial_husband_cash
        wife_cash = wallets.initial_wife_cash
        states = {account.owner: NisaState(deepcopy(account)) for account in plan.nisa_accounts}
        results: list[YearResult] = []

        for raw in raw_results:
            ratio = raw.months / 12.0
            husband_mode, husband_benefit = _mode_and_benefit(
                plan, "husband", raw.husband_age, raw.offset, ratio
            )
            wife_mode, wife_benefit = _mode_and_benefit(
                plan, "wife", raw.wife_age, raw.offset, ratio
            )
            husband_net, wife_net = _split_salary_net(
                plan, raw, husband_mode, wife_mode
            )

            husband_pension = (
                plan.husband.annual_pension * ratio
                if raw.husband_age >= plan.husband.pension_start_age
                else 0.0
            )
            wife_pension = (
                plan.wife.annual_pension * ratio
                if raw.wife_age >= plan.wife.pension_start_age
                else 0.0
            )
            husband_one_time = _owner_one_time(plan, "husband", raw.husband_age)
            wife_one_time = _owner_one_time(plan, "wife", raw.wife_age)
            household_one_time = _household_one_time(plan, raw.offset)
            child_and_household_benefits = max(
                0.0, raw.benefits - husband_benefit - wife_benefit
            )

            husband_cash += husband_net + husband_pension + husband_benefit + husband_one_time
            wife_cash += wife_net + wife_pension + wife_benefit + wife_one_time

            requested_husband_transfer = wallets.husband_household_monthly * raw.months
            requested_wife_transfer = wallets.wife_household_monthly * raw.months
            husband_transfer = min(max(0.0, husband_cash), requested_husband_transfer)
            wife_transfer = min(max(0.0, wife_cash), requested_wife_transfer)
            husband_cash -= husband_transfer
            wife_cash -= wife_transfer

            husband_personal_spending = wallets.husband_personal_spending_monthly * raw.months
            wife_personal_spending = wallets.wife_personal_spending_monthly * raw.months
            husband_cash -= husband_personal_spending
            wife_cash -= wife_personal_spending

            household_income = (
                husband_transfer
                + wife_transfer
                + child_and_household_benefits
                + raw.rental_income
                + household_one_time
                + raw.life_event_income
            )
            household_cash += household_income - raw.consumption_total

            events = _clean_finance_messages(list(raw.events))
            warnings = _clean_finance_messages(list(raw.warnings))
            if husband_transfer + 1 < requested_husband_transfer:
                warnings.append("夫の個人資金が不足し、共同家計への入金を満額できません")
            if wife_transfer + 1 < requested_wife_transfer:
                warnings.append("妻の個人資金が不足し、共同家計への入金を満額できません")

            husband_contributed = 0.0
            wife_contributed = 0.0
            planned_total = 0.0
            sold_total = 0.0

            for owner in ("husband", "wife"):
                state = states.get(owner)
                if state is None:
                    continue
                state.begin_year()
                personal_cash = husband_cash if owner == "husband" else wife_cash
                scheduled = state.plan.monthly_for_offset(raw.offset) * raw.months
                desired = scheduled

                if household_cash < wallets.minimum_household_cash:
                    desired = 0.0
                elif wallets.auto_invest_enabled:
                    if (
                        household_cash >= wallets.target_household_cash
                        and personal_cash > wallets.target_personal_cash
                    ):
                        extra = personal_cash - wallets.target_personal_cash
                        annual_cap = wallets.auto_extra_monthly_cap * raw.months
                        desired = max(desired, min(annual_cap, desired + extra))

                available = max(0.0, personal_cash - wallets.minimum_personal_cash)
                allocation = min(desired, available)
                planned_total += desired
                actual = state.buy(allocation)
                state.grow(actual)
                personal_cash -= actual

                owner_label = "夫" if owner == "husband" else "妻"
                if actual + 1 < scheduled:
                    if state.used_lifetime_limit >= state.plan.lifetime_limit - 1:
                        events.append(f"{owner_label}NISAは生涯枠1,800万円へ到達")
                    elif household_cash < wallets.minimum_household_cash:
                        events.append(
                            f"共同現預金を守るため{owner_label}NISA積立を一時停止"
                        )
                    elif available + 1 < scheduled:
                        events.append(
                            f"{owner_label}の個人現預金を守るためNISA積立を減額"
                        )
                    else:
                        events.append(f"{owner_label}NISAの制度上限により積立を調整")

                if owner == "husband":
                    husband_cash = personal_cash
                    husband_contributed = actual
                else:
                    wife_cash = personal_cash
                    wife_contributed = actual

            # Each owner's NISA may only restore that owner's personal reserve.
            for owner in ("husband", "wife"):
                state = states.get(owner)
                if state is None:
                    continue
                personal_cash = husband_cash if owner == "husband" else wife_cash
                need = max(0.0, wallets.minimum_personal_cash - personal_cash)
                if need > 0:
                    sold, _ = state.sell(need)
                    personal_cash += sold
                    sold_total += sold
                    if sold > 0:
                        label = "夫" if owner == "husband" else "妻"
                        events.append(f"{label}の個人資金確保のためNISAを{sold/10_000:.0f}万円売却")
                if owner == "husband":
                    husband_cash = personal_cash
                else:
                    wife_cash = personal_cash

            if household_cash < 0:
                warnings.append(f"共同家計が資金ショート {-household_cash/10_000:.0f}万円")
            elif household_cash < wallets.minimum_household_cash:
                warnings.append(
                    "共同現預金が最低額を"
                    f"{(wallets.minimum_household_cash-household_cash)/10_000:.0f}万円下回る"
                )
            if husband_cash < 0:
                warnings.append(f"夫の個人資金が不足 {-husband_cash/10_000:.0f}万円")
            if wife_cash < 0:
                warnings.append(f"妻の個人資金が不足 {-wife_cash/10_000:.0f}万円")

            husband_state = states.get("husband")
            wife_state = states.get("wife")
            husband_market = husband_state.market_value if husband_state else 0.0
            wife_market = wife_state.market_value if wife_state else 0.0
            investments_market = husband_market + wife_market
            investments_book = sum(state.book_value for state in states.values())
            total_cash = household_cash + husband_cash + wife_cash
            net_worth = (
                total_cash
                + investments_market
                + raw.property_value
                - raw.mortgage_balance
            )
            family_personal_spending = husband_personal_spending + wife_personal_spending

            row = raw.model_copy(deep=True)
            row.living_surplus = raw.total_income - raw.consumption_total - family_personal_spending
            row.nisa_planned = planned_total
            row.nisa_contributed = husband_contributed + wife_contributed
            row.nisa_sold = sold_total
            row.cash_end = total_cash
            row.household_cash_end = household_cash
            row.husband_cash_end = husband_cash
            row.wife_cash_end = wife_cash
            row.husband_nisa_contributed = husband_contributed
            row.wife_nisa_contributed = wife_contributed
            row.husband_nisa_market_value = husband_market
            row.wife_nisa_market_value = wife_market
            row.recommended_husband_monthly = (
                husband_contributed / raw.months if raw.months else 0.0
            )
            row.recommended_wife_monthly = (
                wife_contributed / raw.months if raw.months else 0.0
            )
            row.investments_market_value = investments_market
            row.investments_book_value = investments_book
            row.net_worth = net_worth
            row.events = events
            row.warnings = warnings
            results.append(row)

        return results


def _is_safe(plan: ProjectPlan, owner: str) -> bool:
    results = SimulationEngine(plan).run()
    wallets = plan.wallets
    if min(row.household_cash_end for row in results) < wallets.minimum_household_cash:
        return False
    personal_values = (
        [row.husband_cash_end for row in results]
        if owner == "husband"
        else [row.wife_cash_end for row in results]
    )
    return min(personal_values) >= wallets.minimum_personal_cash


def _search_owner(plan: ProjectPlan, owner: str) -> float:
    low = 0.0
    high = 300_000.0
    for _ in range(14):
        midpoint = (low + high) / 2.0
        trial = deepcopy(plan)
        account = next(item for item in trial.nisa_accounts if item.owner == owner)
        account.monthly_contribution = midpoint
        account.contribution_changes = {}
        if _is_safe(trial, owner):
            low = midpoint
        else:
            high = midpoint
    return round(low / 1_000) * 1_000


def recommend_monthly_contributions(plan: ProjectPlan) -> InvestmentRecommendation:
    """Find sustainable constant contributions without mixing spouse-owned money."""

    if plan.wallets.mode != "separate":
        return InvestmentRecommendation(
            husband_monthly=0,
            wife_monthly=0,
            note="おすすめ投資額は家計モードを「夫婦別」にすると試算できます。",
        )

    trial = deepcopy(plan)
    trial.wallets.auto_invest_enabled = False
    for account in trial.nisa_accounts:
        account.monthly_contribution = 0
        account.contribution_changes = {}

    husband = _search_owner(trial, "husband")
    next_trial = deepcopy(trial)
    next(item for item in next_trial.nisa_accounts if item.owner == "husband").monthly_contribution = husband
    wife = _search_owner(next_trial, "wife")
    return InvestmentRecommendation(
        husband_monthly=husband,
        wife_monthly=wife,
        note=(
            "共同家計と本人の最低現預金を全期間で維持できる範囲です。"
            "夫婦間の資金移動は行わず、各本人の財布だけで判定しています。"
        ),
    )
