from __future__ import annotations

from .models import ProjectPlan


def infer_work_reference_child(plan: ProjectPlan) -> str | None:
    """Infer the child currently driving the wife's work stages from saved offsets."""
    if not plan.children:
        return None
    stages = {stage.key: stage for stage in plan.wife_work_stages}
    nursery = stages.get("nursery")
    if nursery:
        expected_birth_offset = nursery.start_offset - 4
        match = next(
            (child for child in plan.children if child.birth_offset == expected_birth_offset),
            None,
        )
        if match:
            return match.name
    return max(plan.children, key=lambda child: child.birth_offset).name


def apply_work_stages_for_child(plan: ProjectPlan, child_name: str | None) -> None:
    """Link childcare and return-to-work stages to the selected child."""
    if not child_name:
        return
    child = next((item for item in plan.children if item.name == child_name), None)
    if child is None:
        raise ValueError("妻の働き方を連動させる子を選び直してください。")

    earliest_birth = min(item.birth_offset for item in plan.children)
    reference_birth = child.birth_offset
    retirement_offset = max(0, plan.wife.retirement_age - plan.wife.current_age)
    stages = {stage.key: stage for stage in plan.wife_work_stages}

    stages["full_time"].label = "出産前の正社員"
    stages["full_time"].end_offset = earliest_birth
    stages["childcare_leave"].label = "育児休業"
    stages["childcare_leave"].start_offset = earliest_birth
    stages["childcare_leave"].end_offset = reference_birth + 4
    stages["nursery"].label = f"短時間パート（{child.name}・保育園期）"
    stages["nursery"].start_offset = reference_birth + 4
    stages["nursery"].end_offset = reference_birth + 6
    stages["elementary"].label = f"パート（{child.name}・小学生期）"
    stages["elementary"].start_offset = reference_birth + 6
    stages["elementary"].end_offset = reference_birth + 12
    stages["junior_high"].label = f"週4〜5日パート（{child.name}・中学生以降）"
    stages["junior_high"].start_offset = reference_birth + 12
    stages["junior_high"].end_offset = retirement_offset
    stages["retired"].start_offset = retirement_offset
