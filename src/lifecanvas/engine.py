from __future__ import annotations

from dataclasses import dataclass
from math import pow

from .models import NisaPlan, ProjectPlan, SocialInsuranceMode, WifeWorkStage, YearResult
from .tax import estimate_net_salary


@dataclass
class MortgageState:
    balance: float
    remaining_months: int


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
        growth = max(-self.market_value, (self.market_value - contribution) * rate + contribution * rate * 0.5)
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

    def _rate_for_offset(self, offset: int) -> float:
        loan = self.plan.housing.mortgage
        return min(loan.max_rate_percent, loan.initial_rate_percent + loan.annual_rate_step_percent * offset)

    def _initial_core_living_annual(self) -> float:
        living = self.plan.living_cost
        if living.scope == "excludes_housing":
            return living.monthly_amount * 12
        mortgage = self.plan.housing.mortgage
        first_payment = self._monthly_payment(mortgage.principal, mortgage.initial_rate_percent, mortgage.term_years * 12) * 12
        recurring_housing = first_payment + mortgage.property_tax_annual + mortgage.insurance_annual + mortgage.maintenance_annual
        return max(0.0, living.monthly_amount * 12 - recurring_housing)

    def _wife_stage(self, offset: int) -> WifeWorkStage:
        active = [stage for stage in self.plan.wife_work_stages if stage.active(offset)]
        if not active:
            return WifeWorkStage(
                key="none", label="収入なし", start_offset=0, annual_gross_income=0,
                social_insurance_mode=SocialInsuranceMode.NONE,
            )
        return max(active, key=lambda s: s.start_offset)

    def _property_value(self, property_age: int) -> float:
        house = self.plan.housing
        land = house.purchase_price * house.land_ratio
        building_initial = house.purchase_price * (1.0 - house.land_ratio)
        decline = min(1.0, max(0.0, property_age / house.building_depreciation_years))
        building_factor = 1.0 - decline * (1.0 - house.building_floor_ratio)
        return land + building_initial * building_factor

    def run(self) -> list[YearResult]:
        plan = self.plan
        results: list[YearResult] = []
        cash = plan.initial_cash
        mortgage = MortgageState(plan.housing.mortgage.principal, plan.housing.mortgage.term_years * 12)
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
            child_ages = {c.name: offset - c.birth_offset for c in plan.children if offset >= c.birth_offset}

            husband_gross_annual = plan.husband.annual_gross_income if husband_age < plan.husband.retirement_age else 0.0
            if husband_age == plan.husband.retirement_age:
                events.append(f"夫が{plan.husband.retirement_age}歳で定年")
            husband_gross = husband_gross_annual * ratio

            wife_stage = self._wife_stage(offset)
            wife_gross_annual = 0.0 if wife_age >= plan.wife.retirement_age else wife_stage.annual_gross_income
            wife_mode = SocialInsuranceMode.NONE if wife_age >= plan.wife.retirement_age else wife_stage.social_insurance_mode
            wife_gross = wife_gross_annual * ratio
            if offset == wife_stage.start_offset:
                events.append(f"妻の働き方: {wife_stage.label}（年収{wife_stage.annual_gross_income/10_000:.0f}万円）")
            if wife_age == plan.wife.retirement_age:
                events.append(f"妻が{plan.wife.retirement_age}歳で退職")

            housing_credit = min(210_000.0, mortgage.balance * 0.007) if offset < 13 and mortgage.balance > 0 else 0.0
            h_net = estimate_net_salary(husband_gross, plan.husband.social_insurance_mode, plan.rules, housing_credit)
            w_net = estimate_net_salary(wife_gross, wife_mode, plan.rules)

            pension = 0.0
            if husband_age >= plan.husband.pension_start_age:
                pension += plan.husband.annual_pension * ratio
            if wife_age >= plan.wife.pension_start_age:
                pension += plan.wife.annual_pension * ratio

            benefits = wife_stage.annual_benefit * ratio
            for child in plan.children:
                age = offset - child.birth_offset
                if age == 0:
                    events.append(f"{child.name}誕生")
                if 0 <= age <= 2:
                    benefits += plan.rules.child_allowance_age_0_2_monthly * months
                elif 3 <= age <= 18:
                    benefits += plan.rules.child_allowance_age_3_18_monthly * months

            mortgage_payment = mortgage_interest = mortgage_principal = 0.0
            housing_cost = 0.0
            rental_income = 0.0
            move_this_year = plan.housing.move_offset is not None and offset == plan.housing.move_offset
            if move_this_year and not moved:
                payoff = mortgage.balance
                if payoff > 0:
                    housing_cost += payoff
                    mortgage_principal += payoff
                    mortgage.balance = 0.0
                    mortgage.remaining_months = 0
                housing_cost += plan.housing.move_cost
                moved = True
                events.append(f"住み替え・住宅ローン一括返済（{payoff/10_000:.0f}万円）")

            if mortgage.balance > 0 and mortgage.remaining_months > 0:
                rate = self._rate_for_offset(offset)
                monthly_payment = self._monthly_payment(mortgage.balance, rate, mortgage.remaining_months)
                for _ in range(min(months, mortgage.remaining_months)):
                    interest = mortgage.balance * (rate / 100.0 / 12.0)
                    principal = min(mortgage.balance, max(0.0, monthly_payment - interest))
                    mortgage.balance -= principal
                    mortgage.remaining_months -= 1
                    mortgage_payment += principal + interest
                    mortgage_interest += interest
                    mortgage_principal += principal
                housing_cost += mortgage_payment

            mortgage_rules = plan.housing.mortgage
            housing_cost += (mortgage_rules.property_tax_annual + mortgage_rules.insurance_annual + mortgage_rules.maintenance_annual) * ratio
            if moved:
                housing_cost += plan.housing.new_home_monthly_cost * months
                rental_income += plan.housing.old_home_net_rent_annual * ratio

            education_cost = sum(plan.education.annual_cost(offset - c.birth_offset) for c in plan.children) * ratio

            car_cost = 0.0
            if offset >= plan.car.purchase_offset:
                car_cost += plan.car.annual_running_cost * ratio
            if offset == plan.car.purchase_offset:
                car_cost += plan.car.purchase_price
                events.append("軽自動車を購入")
            elif (
                plan.car.replacement_cycle_years
                and offset > plan.car.purchase_offset
                and (offset - plan.car.purchase_offset) % plan.car.replacement_cycle_years == 0
            ):
                car_cost += plan.car.replacement_price
                events.append("軽自動車を買い替え")

            children_count = len([age for age in child_ages.values() if age <= 21])
            core_living = (core_living_annual + children_count * plan.living_cost.annual_child_increment) * ratio
            consumption = core_living + housing_cost + education_cost + car_cost
            salary_net = h_net.net + w_net.net + pension
            total_income = salary_net + benefits + rental_income
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
                events.append(f"手元資金を守るためNISA積立を{(planned-contributed)/10_000:.0f}万円減額")

            sold_total = 0.0
            cash_need = max(0.0, plan.rules.minimum_cash_reserve - cash)
            for state in sorted(nisa_states, key=lambda s: s.market_value, reverse=True):
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
                warnings.append(f"現預金が目標額を{(plan.rules.minimum_cash_reserve-cash)/10_000:.0f}万円下回る")

            investments_market = sum(s.market_value for s in nisa_states)
            investments_book = sum(s.book_value for s in nisa_states)
            property_value = self._property_value(offset)
            net_worth = cash + investments_market + property_value - mortgage.balance

            results.append(YearResult(
                offset=offset,
                calendar_year=plan.start_year + offset,
                months=months,
                husband_age=husband_age,
                wife_age=wife_age,
                children_ages=child_ages,
                husband_gross=husband_gross,
                wife_gross=wife_gross,
                salary_net=salary_net,
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
            ))
        return results
