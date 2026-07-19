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


def test_previous_personal_plan_gets_220_man_retirement_income(tmp_path):
    plan = build_genki_family_plan()
    period = next(item for item in plan.income_periods if "継続雇用" in item.label)
    period.annual_gross_income = 0
    path = save_plan(plan, tmp_path / "old-plan.json")

    loaded = load_plan(path)
    migrated = next(item for item in loaded.income_periods if "継続雇用" in item.label)

    assert migrated.annual_gross_income == 2_200_000
    assert migrated.end_age == loaded.husband.pension_start_age
