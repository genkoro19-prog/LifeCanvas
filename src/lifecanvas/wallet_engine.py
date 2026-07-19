from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .engine import NisaState
from .models import IncomePeriod, ProjectPlan, SocialInsuranceMode, WifeWorkStage, YearResult
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


def _social_insurance_mode(
    plan: ProjectPlan,
    owner: str,
    age: int,
    offset: int,
) -> SocialInsuranceMode:
    period = _income_period(plan, owner, age)
    if period:
        return period.social_insurance_mode
    if owner == "husband":
        if age >= plan.husband.retirement_age:
            return SocialInsuranceMode.NONE
        return plan.husband.social_insurance_mode
    stage = _wife_stage(plan, offset)
    if age >= plan.wife.retirement_age or stage is None:
        return SocialInsuranceMode.NONE
    return stage.social_insurance_mode


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
    """Split the core engine's exact take-home while retaining the housing-credit effect."""

    husband = estimate_net_salary(row.husband_gross, husband_mode, plan.rules).net
    wife = estimate_net_salary(row.wife_gross, wife_mode, plan.rules).net
    estimated = husband + wife
    difference = row.salary_net - estimated
    if difference >= 0:
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


def _ratio(plan: ProjectPlan) -> tuple[float, float]:
    wallets = plan.wallets
    husband = wallets.household_shortfall_husband_percent / 100.0
    wife = wallets.household_shortfall_wife_percent / 100.0
    return husband, wife


class SimulationEngine:
    """Run either the legacy pooled model or two separately owned bank accounts."""

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
        husband_ratio, wife_ratio = _ratio(plan)

        physical_plan = deepcopy(plan)
        for account in physical_plan.nisa_accounts:
            account.monthly_contribution = 0
            account.contribution_changes = {}
        physical_plan.rules.minimum_cash_reserve = 0
        raw_results = HousingSimulationEngine(physical_plan).run()

        # The old single "current cash" field is migrated into the two owned accounts.
        husband_cash = wallets.initial_husband_cash + plan.initial_cash * husband_ratio
        wife_cash = wallets.initial_wife_cash + plan.initial_cash * wife_ratio
        states = {account.owner: NisaState(deepcopy(account)) for account in plan.nisa_accounts}
        results: list[YearResult] = []

        for raw in raw_results:
            ratio = raw.months / 12.0
            husband_opening = husband_cash
            wife_opening = wife_cash
            husband_mode = _social_insurance_mode(plan, "husband", raw.husband_age, raw.offset)
            wife_mode = _social_insurance_mode(plan, "wife", raw.wife_age, raw.offset)
            husband_net, wife_net = _split_salary_net(plan, raw, husband_mode, wife_mode)

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

            husband_personal_income = husband_net + husband_pension + husband_one_time
            # All benefits, including childcare allowance and leave benefits, enter the wife's account.
            wife_personal_income = wife_net + wife_pension + wife_one_time + raw.benefits
            husband_cash += husband_personal_income
            wife_cash += wife_personal_income

            household_offsets = raw.rental_income + household_one_time + raw.life_event_income
            household_cost_net = max(0.0, raw.consumption_total - household_offsets)
            household_surplus = max(0.0, household_offsets - raw.consumption_total)
            if household_surplus:
                husband_cash += household_surplus * husband_ratio
                wife_cash += household_surplus * wife_ratio

            active_children = sum(
                1 for age in raw.children_ages.values() if 0 <= age <= 21
            )
            requested_husband = (
                wallets.husband_household_monthly
                + wallets.husband_child_household_increment_monthly * active_children
            ) * raw.months
            requested_wife = (
                wallets.wife_household_monthly
                + wallets.wife_child_household_increment_monthly * active_children
            ) * raw.months
            requested_total = requested_husband + requested_wife

            normal_paid = min(household_cost_net, requested_total)
            if requested_total > 0:
                husband_normal = normal_paid * requested_husband / requested_total
                wife_normal = normal_paid - husband_normal
            else:
                husband_normal = 0.0
                wife_normal = 0.0

            household_shortfall = max(0.0, household_cost_net - normal_paid)
            husband_extra = household_shortfall * husband_ratio
            wife_extra = household_shortfall - husband_extra
            husband_household_paid = husband_normal + husband_extra
            wife_household_paid = wife_normal + wife_extra
            husband_cash -= husband_household_paid
            wife_cash -= wife_household_paid

            husband_personal_spending = wallets.husband_personal_spending_monthly * raw.months
            wife_personal_spending = wallets.wife_personal_spending_monthly * raw.months
            husband_cash -= husband_personal_spending
            wife_cash -= wife_personal_spending

            events = _clean_finance_messages(list(raw.events))
            warnings = _clean_finance_messages(list(raw.warnings))
            if household_shortfall > 1:
                events.append(
                    "家計不足 "
                    f"{household_shortfall/10_000:,.0f}万円を"
                    f"夫{wallets.household_shortfall_husband_percent:g}%・"
                    f"妻{wallets.household_shortfall_wife_percent:g}%で預金から補填"
                )
            if any(age == 0 for age in raw.children_ages.values()):
                increase = wallets.husband_child_household_increment_monthly
                if increase > 0:
                    events.append(
                        f"子ども誕生により夫の家計負担上限を月{increase/10_000:,.1f}万円増額"
                    )
            if raw.benefits > 0:
                events.append(f"給付金{raw.benefits/10_000:,.0f}万円を妻口座へ入金")

            husband_contributed = 0.0
            wife_contributed = 0.0
            planned_total = 0.0

            for owner in ("husband", "wife"):
                state = states.get(owner)
                if state is None:
                    continue
                state.begin_year()
                personal_cash = husband_cash if owner == "husband" else wife_cash
                scheduled = state.plan.monthly_for_offset(raw.offset) * raw.months
                desired = scheduled
                if wallets.auto_invest_enabled and personal_cash > wallets.target_personal_cash:
                    extra = personal_cash - wallets.target_personal_cash
                    annual_cap = wallets.auto_extra_monthly_cap * raw.months
                    desired = max(scheduled, min(annual_cap, scheduled + extra))

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
                    elif available + 1 < scheduled:
                        events.append(
                            f"{owner_label}の手元現金100万円を守るためNISA積立を減額・停止"
                        )
                    else:
                        events.append(f"{owner_label}NISAの制度上限により積立を調整")

                if owner == "husband":
                    husband_cash = personal_cash
                    husband_contributed = actual
                else:
                    wife_cash = personal_cash
                    wife_contributed = actual

            if husband_cash < 0:
                warnings.append(f"夫の預金が不足 {-husband_cash/10_000:,.0f}万円")
            elif husband_cash < wallets.minimum_personal_cash:
                warnings.append(
                    f"夫の預金が最低手元現金を"
                    f"{(wallets.minimum_personal_cash-husband_cash)/10_000:,.0f}万円下回る"
                )
            if wife_cash < 0:
                warnings.append(f"妻の預金が不足 {-wife_cash/10_000:,.0f}万円")
            elif wife_cash < wallets.minimum_personal_cash:
                warnings.append(
                    f"妻の預金が最低手元現金を"
                    f"{(wallets.minimum_personal_cash-wife_cash)/10_000:,.0f}万円下回る"
                )

            husband_state = states.get("husband")
            wife_state = states.get("wife")
            husband_market = husband_state.market_value if husband_state else 0.0
            wife_market = wife_state.market_value if wife_state else 0.0
            investments_market = husband_market + wife_market
            investments_book = sum(state.book_value for state in states.values())
            total_cash = husband_cash + wife_cash
            net_worth = total_cash + investments_market + raw.property_value - raw.mortgage_balance
            family_personal_spending = husband_personal_spending + wife_personal_spending

            row = raw.model_copy(deep=True)
            row.living_surplus = raw.total_income - raw.consumption_total - family_personal_spending
            row.nisa_planned = planned_total
            row.nisa_contributed = husband_contributed + wife_contributed
            row.nisa_sold = 0.0
            row.cash_end = total_cash
            row.household_cash_end = 0.0
            row.husband_cash_end = husband_cash
            row.wife_cash_end = wife_cash
            row.husband_nisa_contributed = husband_contributed
            row.wife_nisa_contributed = wife_contributed
            row.husband_nisa_market_value = husband_market
            row.wife_nisa_market_value = wife_market
            row.recommended_husband_monthly = husband_contributed / raw.months if raw.months else 0.0
            row.recommended_wife_monthly = wife_contributed / raw.months if raw.months else 0.0
            row.investments_market_value = investments_market
            row.investments_book_value = investments_book
            row.net_worth = net_worth
            row.household_cost_net = household_cost_net
            row.household_shortfall = household_shortfall
            row.husband_household_paid = husband_household_paid
            row.wife_household_paid = wife_household_paid
            row.husband_personal_spending = husband_personal_spending
            row.wife_personal_spending = wife_personal_spending
            row.husband_personal_income = husband_personal_income
            row.wife_personal_income = wife_personal_income
            row.husband_savings_change = husband_cash - husband_opening
            row.wife_savings_change = wife_cash - wife_opening
            row.events = events
            row.warnings = warnings
            results.append(row)

        return results


def _is_safe(plan: ProjectPlan, owner: str) -> bool:
    results = SimulationEngine(plan).run()
    floor = plan.wallets.minimum_personal_cash
    personal_values = (
        [row.husband_cash_end for row in results]
        if owner == "husband"
        else [row.wife_cash_end for row in results]
    )
    return min(personal_values) >= floor


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
    """Find constant monthly contributions that keep each owner's cash above the floor."""

    if plan.wallets.mode != "separate":
        return InvestmentRecommendation(
            husband_monthly=0,
            wife_monthly=0,
            note="おすすめ投資額は家計モードを「夫婦の預金を分ける」にすると試算できます。",
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
            f"家計不足の負担を夫{plan.wallets.household_shortfall_husband_percent:g}%・"
            f"妻{plan.wallets.household_shortfall_wife_percent:g}%で織り込み、"
            f"各自の預金を全期間{plan.wallets.minimum_personal_cash/10_000:,.0f}万円以上"
            "残せる範囲です。夫婦間のNISA資金移動は行いません。"
        ),
    )
