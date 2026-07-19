from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QScrollArea

from lifecanvas.ito_sample import build_ito_family_plan
from lifecanvas.pdf_report_v2 import export_pdf
from lifecanvas.rent_engine import SimulationEngine, is_rental_move
from lifecanvas.revision_ui import LifeCanvasWindow
from lifecanvas.timeline import build_life_events


def _app():
    return QApplication.instance() or QApplication([])


def _close(app, window):
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


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

    assert after_move.housing_cost >= 2_160_000 * 0.99
    assert after_move.property_value == pytest.approx(0)
    assert after_move.mortgage_balance == pytest.approx(0)
    assert not any("__lifecanvas_future_rent__" in event for event in after_move.events)


def test_result_page_scrolls_and_places_judgement_below_graph():
    app = _app()
    window = LifeCanvasWindow()

    result_page = window.tabs.widget(0)
    assert isinstance(result_page, QScrollArea)
    assert window.canvas.minimumHeight() >= 430
    content_layout = result_page.widget().layout()
    assert content_layout.indexOf(window.canvas) < content_layout.indexOf(window.dashboard_summary)
    assert content_layout.indexOf(window.dashboard_summary) < content_layout.indexOf(window.dashboard_warnings)
    assert window.sample_combo.count() == 2
    assert window.housing_editor.mode.findData("rent") >= 0
    assert window.figure.axes[0].get_title() == "資産・負債の推移"

    _close(app, window)


def test_deleting_children_updates_plan_results_and_timeline():
    app = _app()
    window = LifeCanvasWindow()

    while window.child_editor.table.rowCount():
        window.child_editor.table.selectRow(0)
        window.child_editor.remove_selected()
    window.recalculate()

    assert window.plan.children == []
    assert all(result.children_ages == {} for result in window.results)
    assert all(result.education_cost == pytest.approx(0) for result in window.results)
    assert not any(event.category == "family" for event in build_life_events(window.plan))

    _close(app, window)


def test_both_spouses_can_set_income_from_specific_ages():
    app = _app()
    window = LifeCanvasWindow()

    husband = window.husband_age_income
    husband.table.setRowCount(0)
    husband.add_row()
    husband.add_row()
    husband.table.cellWidget(0, 0).setText("現在の勤務")
    husband.table.cellWidget(0, 1).setText("34")
    husband.table.cellWidget(0, 2).setText("6000000")
    husband.table.cellWidget(1, 0).setText("働き方変更")
    husband.table.cellWidget(1, 1).setText("50")
    husband.table.cellWidget(1, 2).setText("4000000")

    wife = window.wife_age_income
    wife.table.setRowCount(0)
    wife.add_row()
    wife.add_row()
    wife.table.cellWidget(0, 0).setText("現在の勤務")
    wife.table.cellWidget(0, 1).setText("29")
    wife.table.cellWidget(0, 2).setText("4500000")
    wife.table.cellWidget(1, 0).setText("働き方変更")
    wife.table.cellWidget(1, 1).setText("40")
    wife.table.cellWidget(1, 2).setText("3000000")

    window.recalculate()

    husband_50 = next(result for result in window.results if result.husband_age == 50)
    wife_40 = next(result for result in window.results if result.wife_age == 40)
    assert husband_50.husband_gross == pytest.approx(4_000_000)
    assert wife_40.wife_gross == pytest.approx(3_000_000)
    assert any(period.owner == "wife" for period in window.plan.income_periods)

    _close(app, window)


def test_revised_pdf_can_export_ito_plan(tmp_path: Path):
    plan = build_ito_family_plan()
    results = SimulationEngine(plan).run()
    target = export_pdf(plan, results, tmp_path / "ito.pdf")

    assert target.exists()
    assert target.stat().st_size > 10_000
