from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from lifecanvas.engine import SimulationEngine
from lifecanvas.models import CarPlan, ProjectPlan
from lifecanvas.pdf_report import export_pdf
from lifecanvas.plotting import configure_japanese_matplotlib
from lifecanvas.sample import build_genki_family_plan


def test_legacy_single_car_is_migrated_to_car_list():
    original = build_genki_family_plan()
    payload = original.model_dump()
    payload.pop("cars", None)

    loaded = ProjectPlan.model_validate(payload)

    assert len(loaded.cars) == 1
    assert loaded.cars[0].purchase_price == loaded.car.purchase_price


def test_multiple_cars_are_added_to_their_purchase_years():
    plan = build_genki_family_plan()
    plan.cars = [
        CarPlan(
            name="軽自動車",
            purchase_offset=1,
            purchase_price=1_500_000,
            annual_running_cost=300_000,
            replacement_cycle_years=None,
            replacement_price=0,
        ),
        CarPlan(
            name="普通車",
            purchase_offset=3,
            purchase_price=3_000_000,
            annual_running_cost=450_000,
            replacement_cycle_years=None,
            replacement_price=0,
        ),
    ]
    rows = SimulationEngine(plan).run()

    assert rows[1].car_cost >= 1_500_000
    assert rows[3].car_cost >= 3_000_000 + 300_000 + 450_000
    assert any("普通車を購入" in event for event in rows[3].events)


def test_no_move_mode_removes_move_event():
    plan = build_genki_family_plan()
    plan.housing.move_mode = "none"
    plan.housing.move_offset = None

    rows = SimulationEngine(plan).run()

    assert not any("住み替え" in event for row in rows for event in row.events)


def test_font_configuration_does_not_scan_fonts(monkeypatch):
    import matplotlib.font_manager as font_manager

    monkeypatch.setattr(
        font_manager,
        "findfont",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("font scan called")),
    )
    selected = configure_japanese_matplotlib()
    assert selected in {"Yu Gothic", "Noto Sans CJK JP"}


def test_pdf_report_is_created(tmp_path):
    app = QApplication.instance() or QApplication([])
    plan = build_genki_family_plan()
    rows = SimulationEngine(plan).run()
    target = export_pdf(plan, rows, tmp_path / "report.pdf")

    assert target.exists()
    assert target.stat().st_size > 10_000
    if QApplication.instance() is app:
        app.processEvents()
