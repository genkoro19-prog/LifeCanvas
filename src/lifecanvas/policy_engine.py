from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .engine import NisaState
from .models import (
    IncomePeriod,
    PersonalDebt,
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


@dataclass
class DebtRuntime:
    debt: PersonalDebt
    remaining_months: int
    balance: float

    def due(self, absolute_month: int) -> float:
        if absolute_month < self.debt.start_offset_months or self.remaining_months <= 0:
            return 0.0
        if self.balance > 0:
            self.balance += self.balance * (self.debt.annual_interest_rate / 100.0 / 12.0)
        amount = self.debt.monthly_payment
        if self.debt.bonus_payment and absolute_month % 6 == 5:
            amount += self.debt.bonus_payment
        if self.balance > 0:
            amount = min(amount, self.balance)
        return max(0.0, amount)

    def record(self, actual: float, was_due: bool) -> None:
        if not was_due:
            return
        if self.balance > 0:
            self.balance = max(0.0, self.balance - actual)
        self.remaining_months = max(0, self.remaining_months - 1)


@dataclass
class YearAllocation:
    husband_household_paid: float = 0.0
    wife_household_paid: float = 0.0
    household_unmet: float = 0.0
    husband_spending: float = 0.0
    wife_spending: float = 0.0
    husband_debt: float = 0.0
    wife_debt: float = 0.0
    household_debt: float = 0.0
    husband_unmet: float = 0.0
    wife_unmet: float = 0.0
    husband_base_nisa: float = 0.0
    wife_base_nisa: float = 0.0
    husband_extra_nisa: float = 0.0
    wife_extra_nisa: float = 0.0
    spouse_transfer: float = 0.0
    planned_nisa: float = 0.0


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
    ignored = ("NISA", "手元資金を守るため", "資金確保のため", "資金ショート", "現預金が目標額")
    return [message for message in messages if not any(token in message for token in ignored)]


def _pay_from_cash(cash: float, desired: float) -> tuple[float, float, float]:
    desired = max(0.0, desired)
    actual = min(max(0.0, cash), desired)
    return cash - actual, actual, desired - actual


def _nisa_room(state: NisaState | None) -> float:
    if state is None:
        return 0.0
    annual = max(0.0, state.plan.annual_limit - state.annual_purchased)
    lifetime = max(0.0, state.plan.lifetime_limit - state.used_lifetime_limit)
    return min(annual, lifetime)


def _buy_from_cash(
    cash: float,
    state: NisaState | None,
    desired: float,
    reserve: float = 0.0,
) -> tuple[float, float]:
    if state is None:
        return cash, 0.0
    available = max(0.0, cash - max(0.0, reserve))
    actual = state.buy(min(max(0.0, desired), available))
    return cash - actual, actual


class SimulationEngine:
    """Run the pooled model or the monthly husband/wife allocation policy."""

    def __init__(self, plan: ProjectPlan):
        self.plan = plan

    def run(self) -> list[YearResult]:
        if self.plan.wallets.mode != "separate":
            results = HousingSimulationEngine(self.plan).run()
            for row in results:
                row.household_cash_end = row.cash_end
                row.recommended_husband_monthly = next(
                    (account.monthly_for_offset(row.offset) for account in self.plan.nisa_accounts if account.owner == "husband"),
                    0.0,
                )
                row.recommended_wife_monthly = next(
                    (account.monthly_for_offset(row.offset) for account in self.plan.nisa_accounts if account.owner == "wife"),
                    0.0,
                )
            return results
        return self._run_separate()

    def _run_separate(self) -> list[YearResult]:
        plan = self.plan
        wallets = plan.wallets
        physical_plan = deepcopy(plan)
        for account in physical_plan.nisa_accounts:
            account.monthly_contribution = 0
            account.contribution_changes = {}
        physical_plan.rules.minimum_cash_reserve = 0
        raw_results = HousingSimulationEngine(physical_plan).run()

        husband_cash = wallets.initial_husband_cash + plan.initial_cash
        wife_cash = wallets.initial_wife_cash
        states = {account.owner: NisaState(deepcopy(account)) for account in plan.nisa_accounts}
        debt_states = {
            debt.debt_id: DebtRuntime(
                debt=deepcopy(debt),
                remaining_months=debt.remaining_months,
                balance=debt.current_balance or debt.principal,
            )
            for debt in plan.personal_debts
        }
        results: list[YearResult] = []
        absolute_month = 0

        for raw in raw_results:
            months = max(1, raw.months)
            ratio = months / 12.0
            husband_opening = husband_cash
            wife_opening = wife_cash
            husband_mode = _social_insurance_mode(plan, "husband", raw.husband_age, raw.offset)
            wife_mode = _social_insurance_mode(plan, "wife", raw.wife_age, raw.offset)
            husband_net, wife_net = _split_salary_net(plan, raw, husband_mode, wife_mode)
            husband_pension = plan.husband.annual_pension * ratio if raw.husband_age >= plan.husband.pension_start_age else 0.0
            wife_pension = plan.wife.annual_pension * ratio if raw.wife_age >= plan.wife.pension_start_age else 0.0
            husband_personal_income = husband_net + husband_pension + _owner_one_time(plan, "husband", raw.husband_age)
            wife_personal_income = wife_net + wife_pension + _owner_one_time(plan, "wife", raw.wife_age) + raw.benefits
            household_offsets = raw.rental_income + _household_one_time(plan, raw.offset) + raw.life_event_income
            household_cost_net = max(0.0, raw.consumption_total - household_offsets)
            household_surplus = max(0.0, household_offsets - raw.consumption_total)
            husband_monthly_income = husband_personal_income / months
            wife_monthly_income = wife_personal_income / months
            household_monthly_cost = household_cost_net / months
            household_monthly_surplus = household_surplus / months

            husband_state = states.get("husband")
            wife_state = states.get("wife")
            for state in states.values():
                state.begin_year()
            year = YearAllocation()
            annual_transfer_used = 0.0

            for _month in range(months):
                husband_cash += husband_monthly_income + household_monthly_surplus
                wife_cash += wife_monthly_income
                wife_flow_remaining = wife_monthly_income

                for runtime in debt_states.values():
                    due = runtime.due(absolute_month)
                    if due <= 0:
                        continue
                    debt = runtime.debt
                    if debt.borrower == "wife":
                        if debt.payment_source == "spouse":
                            husband_cash, paid, unmet = _pay_from_cash(husband_cash, due)
                            year.husband_debt += paid
                            year.husband_unmet += unmet
                        else:
                            wife_cash, paid, unmet = _pay_from_cash(wife_cash, due)
                            year.wife_debt += paid
                            year.wife_unmet += unmet
                            wife_flow_remaining = max(0.0, wife_flow_remaining - paid)
                    elif debt.borrower == "husband":
                        if debt.payment_source == "spouse":
                            wife_cash, paid, unmet = _pay_from_cash(wife_cash, due)
                            year.wife_debt += paid
                            year.wife_unmet += unmet
                        else:
                            husband_cash, paid, unmet = _pay_from_cash(husband_cash, due)
                            year.husband_debt += paid
                            year.husband_unmet += unmet
                    else:
                        husband_cash, paid, unmet = _pay_from_cash(husband_cash, due)
                        year.household_debt += paid
                        year.husband_unmet += unmet
                    runtime.record(paid, True)

                husband_cash, paid, unmet = _pay_from_cash(husband_cash, wallets.husband_personal_spending_monthly)
                year.husband_spending += paid
                year.husband_unmet += unmet
                wife_cash, wife_spent, unmet = _pay_from_cash(wife_cash, wallets.wife_personal_spending_monthly)
                year.wife_spending += wife_spent
                year.wife_unmet += unmet
                wife_flow_remaining = max(0.0, wife_flow_remaining - wife_spent)

                wife_base_desired = wife_state.plan.monthly_for_offset(raw.offset) if wife_state else 0.0
                year.planned_nisa += wife_base_desired
                wife_cash, wife_base = _buy_from_cash(wife_cash, wife_state, wife_base_desired)
                year.wife_base_nisa += wife_base
                wife_flow_remaining = max(0.0, wife_flow_remaining - wife_base)

                active_children = sum(1 for age in raw.children_ages.values() if 0 <= age <= 21)
                wife_cap = wallets.wife_household_monthly + wallets.wife_child_household_increment_monthly * active_children
                wife_candidate = (
                    wife_flow_remaining
                    if wife_flow_remaining > wallets.wife_contribution_threshold_monthly
                    else 0.0
                )
                if wallets.wife_use_existing_cash_for_household:
                    wife_candidate = max(wife_candidate, max(0.0, wife_cash - wallets.wife_contribution_threshold_monthly))
                wife_household = min(household_monthly_cost, wife_cap, wife_candidate)
                wife_cash -= wife_household
                year.wife_household_paid += wife_household
                wife_flow_remaining = max(0.0, wife_flow_remaining - wife_household)

                remaining_household = max(0.0, household_monthly_cost - wife_household)
                husband_cash, husband_household, household_unmet = _pay_from_cash(husband_cash, remaining_household)
                year.husband_household_paid += husband_household
                year.household_unmet += household_unmet

                saving_reserve = 0.0
                if husband_cash < wallets.husband_target_cash:
                    saving_reserve = min(wallets.husband_monthly_saving_until_target, wallets.husband_target_cash - husband_cash)
                husband_base_desired = husband_state.plan.monthly_for_offset(raw.offset) if husband_state else 0.0
                year.planned_nisa += husband_base_desired
                husband_cash, husband_base = _buy_from_cash(
                    husband_cash,
                    husband_state,
                    husband_base_desired,
                    reserve=wallets.husband_minimum_cash + saving_reserve,
                )
                year.husband_base_nisa += husband_base

                if wallets.auto_invest_enabled:
                    # Wife surplus remains in the wife's cash account. Only her configured
                    # base NISA is paid from her own income; husband-funded additions are
                    # processed by the explicit spouse-transfer rule below.
                    husband_extra_desired = min(
                        wallets.auto_extra_monthly_cap,
                        max(0.0, husband_cash - wallets.husband_target_cash),
                    )
                    husband_cash, husband_extra = _buy_from_cash(
                        husband_cash,
                        husband_state,
                        husband_extra_desired,
                        reserve=wallets.husband_target_cash,
                    )
                    year.husband_extra_nisa += husband_extra
                    year.planned_nisa += husband_extra_desired

                    transfer_limit_left = max(
                        0.0,
                        wallets.spouse_nisa_annual_management_limit
                        - wallets.spouse_nisa_other_transfers_this_year
                        - annual_transfer_used,
                    )
                    if (
                        wallets.spouse_nisa_transfer_enabled
                        and _nisa_room(husband_state) <= 1
                        and transfer_limit_left > 0
                        and _nisa_room(wife_state) > 0
                    ):
                        transfer_desired = min(
                            max(0.0, husband_cash - wallets.husband_target_cash),
                            transfer_limit_left,
                            _nisa_room(wife_state),
                        )
                        actual_transfer = wife_state.buy(transfer_desired) if wife_state else 0.0
                        husband_cash -= actual_transfer
                        annual_transfer_used += actual_transfer
                        year.spouse_transfer += actual_transfer
                        year.wife_extra_nisa += actual_transfer
                        year.planned_nisa += transfer_desired
                absolute_month += 1

            husband_contributed = year.husband_base_nisa + year.husband_extra_nisa
            wife_contributed = year.wife_base_nisa + year.wife_extra_nisa
            if husband_state:
                husband_state.grow(husband_contributed)
            if wife_state:
                wife_state.grow(wife_contributed)

            events = _clean_finance_messages(list(raw.events))
            warnings = _clean_finance_messages(list(raw.warnings))
            if year.wife_household_paid + 1 < wallets.wife_household_monthly * months:
                events.append(f"妻の収入状況により家計拠出は年間{year.wife_household_paid/10_000:,.0f}万円")
            if year.husband_household_paid > 0:
                events.append(f"家計残額{year.husband_household_paid/10_000:,.0f}万円を夫が負担")
            if year.spouse_transfer > 0:
                events.append(f"夫NISA枠消化後、妻NISAへ{year.spouse_transfer/10_000:,.0f}万円を資金移転")
            total_debt = year.husband_debt + year.wife_debt + year.household_debt
            if total_debt > 0:
                events.append(f"個人借入等を年間{total_debt/10_000:,.0f}万円返済")
            if husband_cash < wallets.husband_minimum_cash:
                warnings.append(
                    f"夫の預金が最低維持預金を{(wallets.husband_minimum_cash-husband_cash)/10_000:,.0f}万円下回る"
                )
            if year.household_unmet > 1:
                warnings.append(f"家計支出を満たせず未充足額{year.household_unmet/10_000:,.0f}万円")
            if year.husband_unmet + year.wife_unmet > 1:
                warnings.append(
                    f"個人支出・返済の未充足額{(year.husband_unmet+year.wife_unmet)/10_000:,.0f}万円"
                )

            husband_market = husband_state.market_value if husband_state else 0.0
            wife_market = wife_state.market_value if wife_state else 0.0
            investments_market = husband_market + wife_market
            investments_book = sum(state.book_value for state in states.values())
            total_cash = max(0.0, husband_cash) + max(0.0, wife_cash)
            unmet_amount = year.household_unmet + year.husband_unmet + year.wife_unmet
            net_worth = total_cash + investments_market + raw.property_value - raw.mortgage_balance - unmet_amount
            family_personal_spending = year.husband_spending + year.wife_spending

            row = raw.model_copy(deep=True)
            row.living_surplus = raw.total_income - raw.consumption_total - family_personal_spending
            row.nisa_planned = year.planned_nisa
            row.nisa_contributed = husband_contributed + wife_contributed
            row.nisa_sold = 0.0
            row.cash_end = total_cash
            row.household_cash_end = 0.0
            row.husband_cash_end = max(0.0, husband_cash)
            row.wife_cash_end = max(0.0, wife_cash)
            row.husband_nisa_contributed = husband_contributed
            row.wife_nisa_contributed = wife_contributed
            row.husband_base_nisa_contributed = year.husband_base_nisa
            row.wife_base_nisa_contributed = year.wife_base_nisa
            row.husband_additional_nisa_contributed = year.husband_extra_nisa
            row.wife_additional_nisa_contributed = year.wife_extra_nisa
            row.spouse_nisa_transfer = year.spouse_transfer
            row.husband_nisa_market_value = husband_market
            row.wife_nisa_market_value = wife_market
            row.recommended_husband_monthly = husband_contributed / months
            row.recommended_wife_monthly = wife_contributed / months
            row.investments_market_value = investments_market
            row.investments_book_value = investments_book
            row.net_worth = net_worth
            row.household_cost_net = household_cost_net
            row.household_shortfall = year.husband_household_paid + year.household_unmet
            row.household_unmet = year.household_unmet
            row.husband_household_paid = year.husband_household_paid
            row.wife_household_paid = year.wife_household_paid
            row.husband_personal_spending = year.husband_spending
            row.wife_personal_spending = year.wife_spending
            row.husband_personal_income = husband_personal_income
            row.wife_personal_income = wife_personal_income
            row.husband_debt_payment = year.husband_debt
            row.wife_debt_payment = year.wife_debt
            row.household_debt_payment = year.household_debt
            row.husband_savings_change = row.husband_cash_end - husband_opening
            row.wife_savings_change = row.wife_cash_end - wife_opening
            row.husband_unmet = year.husband_unmet
            row.wife_unmet = year.wife_unmet
            row.unmet_amount = unmet_amount
            row.events = events
            row.warnings = warnings
            results.append(row)
        return results


def _is_safe(plan: ProjectPlan, owner: str) -> bool:
    results = SimulationEngine(plan).run()
    if owner == "husband":
        floor = plan.wallets.husband_minimum_cash
        values = [row.husband_cash_end for row in results]
    else:
        floor = 0.0
        values = [row.wife_cash_end for row in results]
    return min(values) >= floor and not any(row.unmet_amount > 1 for row in results)


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
            f"妻は個人支出・本人NISA・月{plan.wallets.wife_contribution_threshold_monthly/10_000:,.1f}万円の"
            "余裕資金を確保してから家計へ拠出し、残額は夫が負担します。"
            f"夫の預金を全期間{plan.wallets.husband_minimum_cash/10_000:,.0f}万円以上残す範囲です。"
        ),
    )
