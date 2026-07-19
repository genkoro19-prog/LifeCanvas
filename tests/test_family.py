from lifecanvas.family import apply_work_stages_for_child, infer_work_reference_child
from lifecanvas.models import ChildPlan
from lifecanvas.sample import build_genki_family_plan


def test_reference_child_can_be_selected_freely():
    plan = build_genki_family_plan()
    plan.children.append(ChildPlan(name="第三子", birth_offset=9))

    apply_work_stages_for_child(plan, "第三子")
    stages = {stage.key: stage for stage in plan.wife_work_stages}

    assert stages["nursery"].start_offset == 13
    assert stages["elementary"].start_offset == 15
    assert stages["junior_high"].start_offset == 21
    assert "第三子" in stages["nursery"].label
    assert infer_work_reference_child(plan) == "第三子"


def test_children_can_be_removed_or_replaced_without_fixed_indexes():
    plan = build_genki_family_plan()
    plan.children = [ChildPlan(name="子どもA", birth_offset=4)]

    apply_work_stages_for_child(plan, "子どもA")
    stages = {stage.key: stage for stage in plan.wife_work_stages}

    assert stages["full_time"].end_offset == 4
    assert stages["childcare_leave"].start_offset == 4
    assert stages["nursery"].start_offset == 8


def test_no_children_keeps_existing_work_schedule():
    plan = build_genki_family_plan()
    nursery_start = next(stage for stage in plan.wife_work_stages if stage.key == "nursery").start_offset
    plan.children = []

    apply_work_stages_for_child(plan, None)

    assert next(stage for stage in plan.wife_work_stages if stage.key == "nursery").start_offset == nursery_start
    assert infer_work_reference_child(plan) is None
