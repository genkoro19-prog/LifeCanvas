from __future__ import annotations

from pathlib import Path

from .models import ProjectPlan


def save_plan(plan: ProjectPlan, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return target


def migrate_plan(plan: ProjectPlan) -> ProjectPlan:
    """Apply narrow, backward-compatible migrations to previously saved plans."""
    if plan.name == "大原家ライフプラン":
        for period in plan.income_periods:
            if (
                period.owner == "husband"
                and "定年後の継続雇用" in period.label
                and period.annual_gross_income == 0
            ):
                period.annual_gross_income = 2_200_000
                period.end_age = plan.husband.pension_start_age
    return plan


def load_plan(path: str | Path) -> ProjectPlan:
    plan = ProjectPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))
    return migrate_plan(plan)
