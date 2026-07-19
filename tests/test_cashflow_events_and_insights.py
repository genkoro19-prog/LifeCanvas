import pytest

from lifecanvas.engine import SimulationEngine
from lifecanvas.insights import analyze_plan
from lifecanvas.models import CashFlowEvent
from lifecanvas.persistence import load_plan, save_plan
from lifecanvas.sample import build_genki_family_plan


def test_expense_event_reduces_cash_flow():
    plan = build_genki_family_plan()
    baseline = SimulationEngine(plan).run()[3]
    plan.cashflow_events = [
        CashFlowEvent(
            label="リフォーム",
            offset=3,
            flow_type="expense",
            amount=2_000_000,
            category="housing",
        )
    ]

    changed = SimulationEngine(plan).run()[3]

    assert changed.life_event_expense == pytest.approx(2_000_000)
    assert changed.consumption_total - baseline.consumption_total == pytest.approx(2_000_000)
    assert changed.living_surplus - baseline.living_surplus == pytest.approx(-2_000_000)
    assert any("リフォーム" in event for event in changed.events)


def test_income_event_increases_total_income():
    plan = build_genki_family_plan()
    baseline = SimulationEngine(plan).run()[4]
    plan.cashflow_events = [
        CashFlowEvent(
            label="親からの援助",
            offset=4,
            flow_type="income",
            amount=1_500_000,
            category="family",
        )
    ]

    changed = SimulationEngine(plan).run()[4]

    assert changed.life_event_income == pytest.approx(1_500_000)
    assert changed.total_income - baseline.total_income == pytest.approx(1_500_000)


def test_cashflow_events_are_saved(tmp_path):
    plan = build_genki_family_plan()
    plan.cashflow_events = [
        CashFlowEvent(
            label="海外旅行",
            offset=8,
            flow_type="expense",
            amount=800_000,
            category="travel",
        )
    ]
    path = save_plan(plan, tmp_path / "plan.json")

    loaded = load_plan(path)

    assert loaded.cashflow_events == plan.cashflow_events


def test_local_insights_detect_shortage():
    plan = build_genki_family_plan()
    plan.initial_cash = 0
    plan.rules.minimum_cash_reserve = 0
    plan.cashflow_events = [
        CashFlowEvent(
            label="大きな臨時支出",
            offset=1,
            flow_type="expense",
            amount=100_000_000,
            category="other",
        )
    ]
    results = SimulationEngine(plan).run()

    insight = analyze_plan(plan, results)

    assert insight.status == "要見直し"
    assert "資金ショート" in insight.status_note
    assert len(insight.difficult_years) == 3
