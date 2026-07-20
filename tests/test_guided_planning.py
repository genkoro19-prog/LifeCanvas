from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from lifecanvas.guided_input import GuidedInputPage
from lifecanvas.plan_review import (
    apply_wife_work_preset,
    check_plan,
    impact_ranking,
    scenario_summaries,
)
from lifecanvas.sample import build_genki_family_plan


def _app():
    return QApplication.instance() or QApplication([])


def test_genki_sample_is_a_realistic_baseline_not_a_stress_test():
    plan = build_genki_family_plan()

    assert plan.housing.move_mode == "none"
    assert plan.housing.move_offset is None
    assert plan.wife.retirement_age == 60
    assert plan.living_cost.includes_personal_spending is True
    assert plan.wallets.husband_personal_spending_monthly == 0
    assert plan.wallets.wife_personal_spending_monthly == 0
    husband_nisa = next(a for a in plan.nisa_accounts if a.owner == "husband")
    assert husband_nisa.monthly_contribution == 60_000
    assert husband_nisa.contribution_changes[5] == 60_000


def test_plan_check_detects_double_counted_personal_spending():
    plan = build_genki_family_plan()
    plan.wallets.husband_personal_spending_monthly = 50_000

    checks = check_plan(plan)

    assert any("重複" in check.title for check in checks)


def test_standard_wife_preset_builds_leave_and_gradual_return():
    plan = build_genki_family_plan()
    plan.income_periods = [
        period for period in plan.income_periods if period.owner != "wife"
    ]

    apply_wife_work_preset(plan, "standard")

    wife_periods = sorted(
        [period for period in plan.income_periods if period.owner == "wife"],
        key=lambda item: item.start_age,
    )
    assert wife_periods[0].annual_gross_income == plan.wife.annual_gross_income
    assert any(period.annual_benefit > 0 for period in wife_periods)
    assert wife_periods[-1].annual_gross_income == plan.wife.annual_gross_income
    assert plan.wife_work_preset == "standard"


def test_guided_input_removes_double_counting_and_hidden_nisa_change():
    app = _app()
    plan = build_genki_family_plan()
    page = GuidedInputPage(plan)
    page.includes_personal.setChecked(True)
    page.husband_personal.set_value(80_000)
    page.wife_personal.set_value(90_000)
    page.child_count.setCurrentIndex(page.child_count.findData(1))
    page.first_child_offset.set_value(4)
    page.husband_nisa.set_value(50_000)
    page.include_move.setChecked(False)

    page.apply_to(plan)

    assert plan.wallets.mode == "separate"
    assert plan.wallets.husband_personal_spending_monthly == 0
    assert plan.wallets.wife_personal_spending_monthly == 0
    assert len(plan.children) == 1
    assert plan.children[0].birth_offset == 4
    assert plan.housing.move_mode == "none"
    husband_nisa = next(a for a in plan.nisa_accounts if a.owner == "husband")
    assert husband_nisa.monthly_contribution == 50_000
    assert husband_nisa.contribution_changes == {}

    page.close()
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


def test_scenario_comparison_uses_baseline_cautious_and_optimistic():
    summaries = scenario_summaries(build_genki_family_plan())

    assert [item.label for item in summaries] == [
        "基準プラン",
        "慎重プラン",
        "楽観プラン",
    ]
    assert summaries[1].final_net_worth <= summaries[2].final_net_worth


def test_impact_ranking_explains_large_optional_costs():
    impacts = impact_ranking(build_genki_family_plan())
    labels = {item.label for item in impacts}

    assert "車の購入・維持" in labels
    assert "教育費" in labels
