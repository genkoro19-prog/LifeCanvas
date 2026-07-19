from __future__ import annotations

from copy import deepcopy

from .engine import SimulationEngine as BaseSimulationEngine
from .models import CashFlowEvent, ProjectPlan, YearResult


_RENT_EVENT_PREFIX = "__lifecanvas_future_rent__"


def is_rental_move(plan: ProjectPlan) -> bool:
    """Return True when the existing sell fields encode a move from ownership to rent."""

    house = plan.housing
    return (
        house.move_mode == "sell"
        and house.move_offset is not None
        and house.new_home_purchase_price == 0
        and house.new_mortgage_principal == 0
        and house.new_home_monthly_cost > 0
    )


class SimulationEngine:
    """Run the core engine while treating a sell-and-rent plan as recurring housing cost.

    The persisted data remains backward compatible: rental moves reuse the existing sell
    fields with a zero-priced replacement home and `new_home_monthly_cost` as rent.
    """

    def __init__(self, plan: ProjectPlan):
        self.plan = plan

    def run(self) -> list[YearResult]:
        if not is_rental_move(self.plan):
            return BaseSimulationEngine(self.plan).run()

        adjusted = deepcopy(self.plan)
        house = adjusted.housing
        move_offset = house.move_offset or 0
        annual_rent = house.new_home_monthly_cost * 12

        for offset in range(move_offset, adjusted.simulation_years):
            amount = annual_rent
            if offset == 0:
                amount *= (13 - adjusted.start_month) / 12.0
            adjusted.cashflow_events.append(
                CashFlowEvent(
                    label=f"{_RENT_EVENT_PREFIX}{offset}",
                    offset=offset,
                    flow_type="expense",
                    amount=amount,
                    category="housing",
                )
            )

        results = BaseSimulationEngine(adjusted).run()
        for row in results:
            if row.offset < move_offset:
                continue
            rent = annual_rent * (row.months / 12.0 if row.offset == 0 else 1.0)
            row.life_event_expense = max(0.0, row.life_event_expense - rent)
            row.housing_cost += rent
            row.events = [
                event
                for event in row.events
                if _RENT_EVENT_PREFIX not in event
                and not (
                    row.offset == move_offset
                    and event.startswith("今の家を")
                    and "新居へ住み替え" in event
                )
            ]
            if row.offset == move_offset:
                row.events.append(
                    f"今の家を売却し、月{house.new_home_monthly_cost / 10_000:,.1f}万円の賃貸へ住み替え"
                )
        return results
