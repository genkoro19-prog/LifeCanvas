from __future__ import annotations

from dataclasses import dataclass
from math import pow

from .models import IncomePeriod, NisaPlan, ProjectPlan, SocialInsuranceMode, WifeWorkStage, YearResult
from .tax import estimate_net_salary


@dataclass
class MortgageState:
    balance: float
    remaining_months: int
    initial_rate_percent: float
    annual_rate_step_percent: float
    max_rate_percent: float
    start_offset: int = 0


@dataclass
class NisaState:
    plan: NisaPlan
    market_value: float = 0.0
    book_value: float = 0.0
    used_lifetime_limit: float = 0.0
    pending_restore: float = 0.0
    annual_purchased: float = 0.0

    def begin_year(self) -> None:
        self.used_lifetime_limit = max(0.0, self.used_lifetime_limit - self.pending_restore)
        self.pending_restore = 0.0
        self.annual_purchased = 0.0

    def buy(self, desired: float) -> float:
        annual_room = max(0.0, self.plan.annual_limit - self.annual_purchased)
        lifetime_room = max(0.0, self.plan.lifetime_limit - self.used_lifetime_limit)
        actual = min(max(0.0, desired), annual_room, lifetime_room)
        self.market_value += actual
        self.book_value += actual
        self.used_lifetime_limit += actual
        self.annual_purchased += actual
        return actual

    def grow(self, contribution: float) -> float:
        rate = self.plan.annual_return_percent / 100.0
        growth = max(
            -self.market_value,
            (self.market_value - contribution) * rate + contribution * rate * 0.5,
        )
        self.market_value += growth
        return growth

    def sell(self, amount: float) -> tuple[float, float]:
        actual = min(max(0.0, amount), self.market_value)
        if actual <= 0:
            return 0.0, 0.0
        ratio = 0.0 if self.market_value <= 0 else self.book_value / self.market_value
        sold_book = min(self.book_value, actual * ratio)
        self.market_value -= actual
        self.book_value -= sold_book
        self.pending_restore += sold_book
        return actual, sold_book


class SimulationEngine:
    def __init__(self, plan: ProjectPlan):
        self.plan = plan

    @staticmethod
    def _monthly_payment(balance: float, annual_rate_percent: float, months: int) -> float:
        if balance <= 0 or months <= 0:
            return 0.0
        monthly_rate = annual_rate_percent / 100.0 / 12.0
        if monthly_rate == 0:
            return balance / months
        factor = pow(1.0 + monthly_rate, months)
        return balance * monthly_rate * factor / (factor - 1.0)

    @staticmethod
    def _rate_for_state(mortgage: MortgageState, offset: int) -> float:
        elapsed = max(0, offset - mortgage.start_offset)
        return min(
            mortgage.max_rate_percent,
            mortgage.initial_rate_percent + mortgage.annual_rate_step_percent * elapsed,
        )

    def _initial_core_living_annual(self) -> float:
        living = self.plan.living_cost
        if living.scope == "excludes_housing":
            return living.monthly_amount * 12
        mortgage = self.plan.housing.mortgage
        first_payment = self._monthly_payment(
            mortgage.principal,
            mortgage.initial_rate_percent,
            mortgage.term_years * 12,
        ) * 12
        recurring_housing = (
            first_payment
            + mortgage.property_tax_annual
            + mortgage.insurance_annual
            + mortgage.maintenance_annual
        )
        return max(0.0, living.monthly_amount * 12 - recurring_housing)

    def _wife_stage(self, offset: int) -> WifeWorkStage:
        active = [stage for stage in self.plan.wife_work_stages if stage.active(offset)]
        if not active:
            return WifeWorkStage(
                key="none",
                label="収入なし",
                start_offset=0,
                annual_gross_income=0,
                social_insurance_mode=SocialInsuranceMode.NONE,
            )
        return max(active, key=lambda stage: stage.start_offset)

    def _income_period(self, owner: str, age: int) -> IncomePeriod | None:
        active = [
            period
            for period in self.plan.income_periods
            if period.owner == owner and period.active(age)
        ]
        return max(active, key=lambda period: period.start_age) if active else None

    def _property_value(self, purchase_price: float, property_age: int) -> float:
        if purchase_price <= 0:
            return 0.0
        house = self.plan.housing
        land = purchase_price * house.land_ratio
        building_initial = purchase_price * (1.0 - house.land_ratio)
        decline = min(1.0, max(0.0, property_age / house.building_depreciation_years))
        building_factor = 1.0 - decline * (1.0 - house.building_floor_ratio)
        return land + building_initial * building_factor

    def _pay_mortgage(
        self,
        mortgage: MortgageState,
        offset: int,
        months: int,
    ) -> tuple[float, float, float]:
        payment = 0.0
        interest_total = 0.0
        principal_total = 0.0
        if mortgage.balance <= 0 or mortgage.remaining_months <= 0:
            return payment, interest_total, principal_total
        rate = self._rate_for_state(mortgage, offset)
        monthly_payment = self._monthly_payment(
            mortgage.balance,
            rate,
            mortgage.remaining_months,
        )
        for _ in range(min(months, mortgage.remaining_months)):
            interest = mortgage.balance * (rate / 100.0 / 12.0)
            principal = min(mortgage.balance, max(0.0, monthly_payment - interest))
            mortgage.balance -= principal
            mortgage.remaining_months -= 1
            payment += principal + interest
            interest_total += interest
            principal_total += principal
        return payment, interest_total, principal_total

    def run(self) -> list[YearResult]:
        plan = self.plan
        results: list[YearResult] = []
        cash = plan.initial_cash
        mortgage_rules = plan.housing.mortgage
        mortgage = MortgageState(
            balance=mortgage_rules.principal,
            remaining_months=mortgage_rules.term_years * 12,
            initial_rate_percent=mortgage_rules.initial_rate_percent,
            annual_rate_step_percent=mortgage_rules.annual_rate_step_percent,
            max_rate_percent=mortgage_rules.max_rate_percent,
        )
        property_purchase_price = plan.housing.purchase_price
        property_start_offset = 0
        owns_property = property_purchase_price > 0
        nisa_states = [NisaState(account) for account in plan.nisa_accounts]
        core_living_annual = self._initial_core_living_annual()
        moved = False

        for offset in range(plan.simulation_years):
            months = 13 - plan.start_month if offset == 0 else 12
            ratio = months / 12.0
            events: list[str] = []
            warnings: list[str] = []
            for state in nisa_states:
                state.begin_year()

            husband_age = plan.husband.current_age + offset
            wife_age = plan.wife.current_age + offset
            child_ages = {
                child.name: offset - child.birth_offset
                for child in plan.children
                if offset >= child.birth_offset
            }

            husband_period = self._income_period("husband", husband_age)
            if husband_period:
                husband_gross_annual = husband_period.annual_gross_income
                husband_mode = husband_period.social_insurance_mode
                husband_benefit = husband_period.annual_benefit * ratio
                if husband_age == husband_period.start_age:
                    events.append(
                        f"夫の働き方: {husband_period.label}（年収{husband_period.annual_gross_income/10_000:.0f}万円）"
                    )
            else:
                husband_gross_annual = (
                    plan.husband.annual_gross_income
                    if husband_age < plan.husband.retirement_age
                    else 0.0
                )
                husband_mode = (
                    plan.husband.social_insurance_mode
                    if husband_gross_annual > 0
                    else SocialInsuranceMode.NONE
                )
                husband_benefit = 0.0
            if husband_age == plan.husband.retirement_age:
                events.append(f"夫が{plan.husband.retirement_age}歳で定年")
            husband_gross = husband_gross_annual * ratio

            wife_period = self._income_period("wife", wife_age)
            if wife_period:
                wife_gross_annual = wife_period.annual_gross_income
                wife_mode = wife_period.social_insurance_mode
                wife_benefit = wife_period.annual_benefit * ratio
                if wife_age == wife_period.start_age:
                    events.append(
                        f"妻の働き方: {wife_period.label}（年収{wife_period.annual_gross_income/10_000:.0f}万円）"
                    )
            else:
                wife_stage = self._wife_stage(offset)
                wife_gross_annual = (
                    0.0 if wife_age >= plan.wife.retirement_age else wife_stage.annual_gross_income
                )
                wife_mode = (
                    SocialInsuranceMode.NONE
                    if wife_age >= plan.wife.retirement_age
                    else wife_stage.social_insurance_mode
                )
                wife_benefit = wife_stage.annual_benefit * ratio
                if offset == wife_stage.start_offset:
                    events.append(
                        f"妻の働き方: {wife_stage.label}（年収{wife_stage.annual_gross_income/10_000:.0f}万円）"
                    )
            if wife_age == plan.wife.retirement_age:
                events.append(f"妻が{plan.wife.retirement_age}歳で退職")
            wife_gross = wife_gross_annual * ratio

            housing_credit = (
                min(210_000.0, mortgage.balance * 0.007)
                if offset < 13 and mortgage.balance > 0
                else 0.0
            )
            husband_net = estimate_net_salary(
                husband_gross,
                husband_mode,
                plan.rules,
                housing_credit,
            )
            wife_net = estimate_net_salary(wife_gross, wife_mode, plan.rules)

            pension = 0.0
            if husband_age >= plan.husband.pension_start_age:
                pension += plan.husband.annual_pension * ratio
            if wife_age >= plan.wife.pension_start_age:
                pension += plan.wife.annual_pension * ratio

            benefits = husband_benefit + wife_benefit
            for child in plan.children:
                age = offset - child.birth_offset
                if age == 0:
                    events.append(f"{child.name}誕生")
                if 0 <= age <= 2:
                    benefits += plan.rules.child_allowance_age_0_2_monthly * months
                elif 3 <= age <= 18:
                    benefits += plan.rules.child_allowance_age_3_18_monthly * months

            one_time_income = 0.0
            for item in plan.one_time_incomes:
                item_age = (
                    husband_age
                    if item.owner == "husband"
                    else wife_age
                    if item.owner == "wife"
                    else None
                )
                applies = (
                    item_age == item.age
                    if item_age is not None
                    else item.owner == "household" and offset == item.age
                )
                if item.amount > 0 and applies:
                    one_time_income += item.amount
                    events.append(f"{item.label} {item.amount/10_000:.0f}万円")

            life_event_income = 0.0
            life_event_expense = 0.0
            for item in plan.cashflow_events:
                if item.offset != offset:
                    continue
                if item.flow_type == "income":
                    life_event_income += item.amount
                    sign = "+"
                else:
                    life_event_expense += item.amount
                    sign = "-"
                events.append(f"{item.label} {sign}{item.amount/10_000:,.0f}万円")

            mortgage_payment = 0.0
            mortgage_interest = 0.0
            mortgage_principal = 0.0
            housing_cost = 0.0
            rental_income = 0.0
            move_this_year = (
                plan.housing.move_mode != "none"
                and plan.housing.move_offset is not None
                and offset == plan.housing.move_offset
            )
            if move_this_year and not moved:
                if plan.housing.move_mode == "sell":
                    payoff = mortgage.balance
                    down_payment = max(
                        0.0,
                        plan.housing.new_home_purchase_price
                        - plan.housing.new_mortgage_principal,
                    )
                    housing_cost += (
                        payoff
                        + plan.housing.move_cost
                        + down_payment
                        - plan.housing.sale_price
                    )
                    mortgage_principal += payoff
                    mortgage = MortgageState(
                        balance=plan.housing.new_mortgage_principal,
                        remaining_months=plan.housing.new_mortgage_term_years * 12,
                        initial_rate_percent=plan.housing.new_mortgage_rate_percent,
                        annual_rate_step_percent=0.0,
                        max_rate_percent=plan.housing.new_mortgage_rate_percent,
                        start_offset=offset,
                    )
                    property_purchase_price = plan.housing.new_home_purchase_price
                    property_start_offset = offset
                    owns_property = property_purchase_price > 0
                    events.append(
                        f"今の家を{plan.housing.sale_price/10_000:,.0f}万円で売却し、新居へ住み替え"
                    )
                else:
                    housing_cost += plan.housing.move_cost
                    events.append("今の家を残して住み替え")
                moved = True

            payment, interest, principal = self._pay_mortgage(mortgage, offset, months)
            mortgage_payment += payment
            mortgage_interest += interest
            mortgage_principal += principal
            housing_cost += payment

            if owns_property:
                housing_cost += (
                    mortgage_rules.property_tax_annual
                    + mortgage_rules.insurance_annual
                    + mortgage_rules.maintenance_annual
                ) * ratio
            if moved and plan.housing.move_mode == "keep":
                housing_cost += plan.housing.new_home_monthly_cost * months
                rental_income += plan.housing.old_home_net_rent_annual * ratio

            education_cost = sum(
                plan.education.annual_cost(offset - child.birth_offset)
                for child in plan.children
            ) * ratio

            car_cost = 0.0
            for car in plan.cars:
                if not car.enabled:
                    continue
                if offset >= car.purchase_offset:
                    car_cost += car.annual_running_cost * ratio
                if offset == car.purchase_offset:
                    car_cost += car.purchase_price
                    events.append(f"{car.name}を購入")
                elif (
                    car.replacement_cycle_years
                    and offset > car.purchase_offset
                    and (offset - car.purchase_offset) % car.replacement_cycle_years == 0
                ):
                    car_cost += car.replacement_price
                    events.append(f"{car.name}を買い替え")

            children_count = len([age for age in child_ages.values() if age <= 21])
            core_living = (
                core_living_annual
                + children_count * plan.living_cost.annual_child_increment
            ) * ratio
            consumption = (
                core_living
                + housing_cost
                + education_cost
                + car_cost
                + life_event_expense
            )
            salary_net = husband_net.net + wife_net.net
            total_income = (
                salary_net
                + pension
                + benefits
                + rental_income
                + one_time_income
                + life_event_income
            )
            living_surplus = total_income - consumption
            cash += living_surplus

            planned = 0.0
            desired_by_state: list[tuple[NisaState, float]] = []
            for state in nisa_states:
                desired = state.plan.monthly_for_offset(offset) * months
                planned += desired
                desired_by_state.append((state, desired))

            contribution_budget = max(0.0, cash - plan.rules.minimum_cash_reserve)
            contributed = 0.0
            for state, desired in desired_by_state:
                allocation = min(desired, contribution_budget)
                actual = state.buy(allocation)
                cash -= actual
                contribution_budget -= actual
                contributed += actual
                state.grow(actual)
            if contributed + 1 < planned:
                events.append(
                    f"手元資金を守るためNISA積立を{(planned-contributed)/10_000:.0f}万円減額"
                )

            sold_total = 0.0
            cash_need = max(0.0, plan.rules.minimum_cash_reserve - cash)
            for state in sorted(
                nisa_states,
                key=lambda value: value.market_value,
                reverse=True,
            ):
                if cash_need <= 0:
                    break
                sold, _ = state.sell(cash_need)
                cash += sold
                sold_total += sold
                cash_need -= sold
            if sold_total > 0:
                events.append(f"資金確保のためNISAを{sold_total/10_000:.0f}万円売却")
            if cash < 0:
                warnings.append(f"資金ショート {-cash/10_000:.0f}万円")
            elif cash < plan.rules.minimum_cash_reserve:
                warnings.append(
                    f"現預金が目標額を{(plan.rules.minimum_cash_reserve-cash)/10_000:.0f}万円下回る"
                )

            investments_market = sum(state.market_value for state in nisa_states)
            investments_book = sum(state.book_value for state in nisa_states)
            property_value = (
                self._property_value(
                    property_purchase_price,
                    max(0, offset - property_start_offset),
                )
                if owns_property
                else 0.0
            )
            net_worth = cash + investments_market + property_value - mortgage.balance

            results.append(
                YearResult(
                    offset=offset,
                    calendar_year=plan.start_year + offset,
                    months=months,
                    husband_age=husband_age,
                    wife_age=wife_age,
                    children_ages=child_ages,
                    husband_gross=husband_gross,
                    wife_gross=wife_gross,
                    salary_net=salary_net,
                    pension_income=pension,
                    one_time_income=one_time_income,
                    life_event_income=life_event_income,
                    life_event_expense=life_event_expense,
                    benefits=benefits,
                    rental_income=rental_income,
                    total_income=total_income,
                    core_living_cost=core_living,
                    housing_cost=housing_cost,
                    mortgage_payment=mortgage_payment,
                    mortgage_interest=mortgage_interest,
                    mortgage_principal=mortgage_principal,
                    education_cost=education_cost,
                    car_cost=car_cost,
                    consumption_total=consumption,
                    living_surplus=living_surplus,
                    nisa_planned=planned,
                    nisa_contributed=contributed,
                    nisa_sold=sold_total,
                    cash_end=cash,
                    investments_market_value=investments_market,
                    investments_book_value=investments_book,
                    property_value=property_value,
                    mortgage_balance=mortgage.balance,
                    net_worth=net_worth,
                    events=events,
                    warnings=warnings,
                )
            )
        return results
