from __future__ import annotations

from pathlib import Path

from .models import ProjectPlan


def save_plan(plan: ProjectPlan, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_plan(path: str | Path) -> ProjectPlan:
    return ProjectPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))
