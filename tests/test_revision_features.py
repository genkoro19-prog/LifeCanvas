from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lifecanvas.ito_sample import build_ito_family_plan
from lifecanvas.pdf_report_v2 import export_pdf
from lifecanvas.rent_engine import SimulationEngine, is_rental_move
from lifecanvas.revision_ui import LifeCanvasWindow


def test_ito_sample_uses_cautious_unsettled_assumptions():
    plan = build_ito_family_plan()

    assert plan.husband.current_age == 34
    assert plan.husband.annual_gross_income == 6_000_000
    assert plan.wife.current_age == 29
    assert plan.wife.annual_gross_income == 4_500_000
    assert plan.initial_cash == 1_500_000
    assert plan.living_cost.monthly_amount == 250_000
    assert plan.living_cost.scope == "excludes_housing"
    assert plan.housing.mortgage.principal == 60_000_000
    assert plan.housing.mortgage.term_years == 40
    assert plan.cars[0].purchase_price == 3_500_000
    assert plan.cars[0].replacement_cycle_years == 8
    assert plan.cars[0].annual_running_cost == 400_000
    assert len(plan.children) == 1
    assert plan.children[0].birth_offset == 5
    assert all(account.monthly_contribution == 0 for account in plan.nisa_accounts)


def test_rental_move_becomes_recurring_housing_cost():
    plan = build_ito_family_plan()
    house = plan.housing
    house.move_mode = "sell"
    house.move_offset = 10
    house.sale_price = 50_000_000
    house.new_home_purchase_price = 0
    house.new_mortgage_principal = 0
    house.new_home_monthly_cost = 180_000

    assert is_rental_move(plan)
    results = SimulationEngine(plan).run()
    after_move = results[11]

    assert after_move.housing_cost >= pytest.approx(2_160_000, rel=0.01)
    assert after_move.property_value == pytest.approx(0)
    assert after_move.mortgage_balance == pytest.approx(0)
    assert not any("__lifecanvas_future_rent__" in event for event in after_move.events)


def test_revised_dashboard_reserves_graph_height(qtbot):
    window = LifeCanvasWindow()
    qtbot.addWidget(window)

    assert window.canvas.minimumHeight() >= 360
    assert window.sample_combo.count() == 2
    assert window.housing_editor.mode.findData("rent") >= 0
    assert window.figure.axes[0].get_title() == "資産・負債の推移"


def test_revised_pdf_can_export_ito_plan(tmp_path: Path):
    plan = build_ito_family_plan()
    results = SimulationEngine(plan).run()
    target = export_pdf(plan, results, tmp_path / "ito.pdf")

    assert target.exists()
    assert target.stat().st_size > 10_000
