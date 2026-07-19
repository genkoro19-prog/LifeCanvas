# LifeCanvas MVP Product Specification

## Purpose

LifeCanvas is not a household ledger. It is a decision-support simulator that combines income, taxes, social insurance, housing, education, vehicles, NISA, pensions, and life events into a transparent annual plan.

## UX principles

1. The user begins with a small set of important assumptions.
2. Results are visible before detailed editing.
3. Every annual number can be opened and explained.
4. Consumption, asset transfers, investment purchases, and investment sales are shown separately.
5. Missing or provisional assumptions are visible, not silently invented.
6. Scenario comparison is a primary workflow.

## Main screens

- Results: retirement net worth, minimum cash, shortage status, mortgage at relocation, asset chart, warnings.
- Easy setup: household, employment, housing, NISA, and relocation assumptions.
- Timeline and annual detail: yearly table plus calculation breakdown.
- Comparison: baseline, spouse work scenarios, interest scenario, and relocation scenario.

## Accounting rules

- Core living costs and housing costs must never be counted twice.
- When the input is a total household budget including initial housing, core living cost is derived once from the first-year recurring housing cost. Actual future housing changes are then added separately.
- Cash saving is an internal transfer and is not consumption.
- Living surplus = net income + benefits + rental income - consumption.
- Cash flow after investments = living surplus - NISA purchase + NISA sale.
- NISA purchases are reduced or stopped before NISA assets are sold.
- NISA lifetime capacity is managed by acquisition cost. Sold acquisition cost is reusable from the next year.
- A negative cash balance must produce a funding-shortage warning.

## Included sample assumptions

- Start: September 2026.
- Husband age 34, salary 6.2 million yen, retirement at 60.
- Wife age 28, salary 3.5 million yen before childbirth, retirement at 55.
- First child in 5 years and second child in 6 years.
- Wife: childcare leave, 576k nursery stage, 960k elementary stage, 2.2m part-time from second child's junior-high stage.
- House and mortgage: 31.7m yen, 40 years, 1.68%, +0.2 percentage point annually up to 3%.
- Relocation at husband's retirement, mortgage payoff, old-home net rent 750k/year, provisional new-home cost 150k/month.
- Husband NISA 60k/month then 100k/month from year 5; wife 30k/month; expected return 4%.

## Accuracy status

Tax, social insurance, pension, property value, childcare benefits, and housing tax credit are estimates. Values must be configurable and results must display that they are simulations rather than guarantees.
