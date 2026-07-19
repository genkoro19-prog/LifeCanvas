from __future__ import annotations

import base64
import struct

from lifecanvas.engine import NisaState
from lifecanvas.models import NisaPlan
from lifecanvas.pdf_report_v2 import _chart_data_uri, export_pdf
from lifecanvas.rent_engine import SimulationEngine
from lifecanvas.sample import build_genki_family_plan


def test_combined_nisa_limit_and_legacy_migration():
    plan = NisaPlan(
        owner="husband",
        monthly_contribution=0,
        annual_limit=1_200_000,
        lifetime_limit=18_000_000,
    )

    assert plan.annual_limit == 3_600_000
    state = NisaState(plan)
    for _ in range(5):
        state.begin_year()
        assert state.buy(10_000_000) == 3_600_000
    state.begin_year()
    assert state.buy(10_000_000) == 0
    assert state.used_lifetime_limit == 18_000_000


def test_pdf_chart_has_safe_fixed_aspect_ratio(tmp_path):
    plan = build_genki_family_plan()
    results = SimulationEngine(plan).run()
    uri = _chart_data_uri(results)
    raw = base64.b64decode(uri.split(",", 1)[1])

    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    assert width >= 900
    assert height >= 450
    assert 1.7 <= width / height <= 2.2

    target = export_pdf(plan, results, tmp_path / "report.pdf")
    assert target.read_bytes().startswith(b"%PDF")
    assert target.stat().st_size > 10_000
