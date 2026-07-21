from __future__ import annotations

from .models import ChildPlan


def install_legacy_sync_guard() -> None:
    """Protect hidden legacy child fields while syncing modern plans.

    The current UI supports zero or one child, but an older base page still
    expects two child entries when it refreshes its hidden compatibility fields.
    Temporarily provide placeholders only for that legacy refresh and restore the
    real plan immediately afterwards.
    """

    from . import complete_ui

    window_class = complete_ui.LifeCanvasWindow
    if getattr(window_class, "_legacy_child_sync_guard_installed", False):
        return

    original_sync = window_class._sync_inputs_from_plan

    def safe_sync(window) -> None:
        real_children = list(window.plan.children)
        if len(real_children) >= 2:
            original_sync(window)
            return

        base_offset = real_children[0].birth_offset if real_children else 0
        placeholders = [
            ChildPlan(
                name=f"__legacy_child_placeholder_{index + 1}",
                birth_offset=base_offset + 2 * (index + 1),
            )
            for index in range(2 - len(real_children))
        ]
        window.plan.children = [*real_children, *placeholders]
        try:
            original_sync(window)
        finally:
            window.plan.children = real_children

    window_class._sync_inputs_from_plan = safe_sync
    window_class._legacy_child_sync_guard_installed = True
