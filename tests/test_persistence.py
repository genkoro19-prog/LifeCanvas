from lifecanvas.persistence import load_plan, save_plan
from lifecanvas.sample import build_genki_family_plan


def test_plan_roundtrip(tmp_path):
    plan = build_genki_family_plan()
    plan.name = "保存テスト"
    path = save_plan(plan, tmp_path / "plan.json")

    loaded = load_plan(path)

    assert loaded.name == "保存テスト"
    assert loaded.income_periods == plan.income_periods
    assert loaded.one_time_incomes == plan.one_time_incomes
