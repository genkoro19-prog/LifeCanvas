from __future__ import annotations

from types import MethodType

from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton, QWidget


def _safe_disconnect(signal, slot=None) -> None:
    try:
        if slot is None:
            signal.disconnect()
        else:
            signal.disconnect(slot)
    except (RuntimeError, TypeError):
        pass


class CompletionAuditController:
    """Stabilize recalculation, export, and cross-page synchronization."""

    def __init__(self, window):
        self.window = window
        self.original_schedule_refresh = window._schedule_refresh
        self.original_recalculate = window.recalculate
        self.original_export_report = window.export_report
        self.original_apply_guided = window._apply_guided_input
        self._syncing = False
        self._guided_applying = False

        window._schedule_refresh = MethodType(self._schedule_refresh, window)
        window.recalculate = MethodType(self._recalculate, window)
        window.export_report = MethodType(self._export_report, window)
        window._apply_guided_input = MethodType(self._apply_guided_input, window)

        self._rewire_inputs()
        self._rewire_actions()

    def _rewire_inputs(self) -> None:
        window = self.window
        old_schedule = self.original_schedule_refresh
        new_schedule = window._schedule_refresh
        guided = getattr(window, "guided_input", None)

        def inside(widget: QWidget, parent: QWidget | None) -> bool:
            current: QWidget | None = widget
            while current is not None:
                if current is parent:
                    return True
                current = current.parentWidget()
            return False

        for edit in window.findChildren(QLineEdit):
            if guided is not None and inside(edit, guided):
                continue
            _safe_disconnect(edit.editingFinished, old_schedule)
            edit.editingFinished.connect(new_schedule)
        for combo in window.findChildren(QComboBox):
            if guided is not None and inside(combo, guided):
                continue
            if combo.objectName() == "sampleSelector":
                _safe_disconnect(combo.currentIndexChanged, old_schedule)
                continue
            _safe_disconnect(combo.currentIndexChanged, old_schedule)
            combo.currentIndexChanged.connect(new_schedule)

        editors = (
            getattr(window, "child_editor", None),
            getattr(window, "housing_editor", None),
            getattr(window, "car_editor", None),
            getattr(window, "cashflow_event_editor", None),
            getattr(window, "husband_age_income", None),
            getattr(window, "wife_age_income", None),
            getattr(window, "wallet_editor", None),
            getattr(window, "personal_debt_editor", None),
        )
        for editor in editors:
            changed = getattr(editor, "changed", None)
            if changed is None:
                continue
            _safe_disconnect(changed, old_schedule)
            _safe_disconnect(changed, new_schedule)
            changed.connect(new_schedule)

        timer = getattr(window, "_auto_timer", None)
        if timer is not None:
            _safe_disconnect(timer.timeout)
            timer.timeout.connect(window.recalculate)

    def _rewire_actions(self) -> None:
        window = self.window
        guided = getattr(window, "guided_input", None)
        if guided is not None:
            _safe_disconnect(guided.applyRequested)
            guided.applyRequested.connect(window._apply_guided_input)

        for button in window.findChildren(QPushButton):
            if button.objectName() == "pdfButton" or button.text() == "PDFレポート":
                _safe_disconnect(button.clicked)
                button.clicked.connect(lambda _checked=False, w=window: w.export_report())

    def _schedule_refresh(self, window, *_args) -> None:
        if self._syncing or self._guided_applying:
            return
        if getattr(window, "_loading_file", False):
            return
        self.original_schedule_refresh()

    def _sync_guided_from_plan(self) -> None:
        window = self.window
        guided = getattr(window, "guided_input", None)
        quick = getattr(window, "quick_policy", None)
        self._syncing = True
        try:
            if guided is not None:
                guided.load(window.plan)
            if quick is not None:
                quick.load(window.plan)
        finally:
            self._syncing = False

    def _apply_current_guided_values(self) -> None:
        window = self.window
        guided = getattr(window, "guided_input", None)
        if guided is None:
            return
        guided.apply_to(window.plan)
        quick = getattr(window, "quick_policy", None)
        if quick is not None:
            quick.apply_to(window.plan)
        window._sync_inputs_from_plan()
        if hasattr(window, "h_nisa_after") and hasattr(window, "h_nisa_before"):
            window.h_nisa_after.set_value(window.h_nisa_before.value())

    def _recalculate(self, window, *_args) -> bool:
        timer = getattr(window, "_auto_timer", None)
        if timer is not None and timer.isActive():
            timer.stop()

        try:
            guided = getattr(window, "guided_input", None)
            tabs = getattr(window, "tabs", None)
            on_guided_page = guided is not None and tabs is not None and tabs.currentWidget() is guided
            if on_guided_page and not self._guided_applying:
                self._guided_applying = True
                try:
                    self._apply_current_guided_values()
                finally:
                    self._guided_applying = False
        except (TypeError, ValueError) as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(window, "入力内容を確認してください", str(exc))
            detailed = getattr(window, "detailed_settings", None)
            if detailed is not None:
                detailed.status.setText("入力エラー")
            return False

        before = getattr(window, "results", None)
        self.original_recalculate()
        after = getattr(window, "results", None)
        success = after is not before and bool(after)
        detailed = getattr(window, "detailed_settings", None)
        if not success:
            if detailed is not None:
                detailed.status.setText("入力エラー")
            return False

        self._sync_guided_from_plan()
        if detailed is not None:
            detailed.status.setText("反映済み")
        return True

    def _export_report(self, window) -> None:
        if not window.recalculate():
            return
        self.original_export_report()

    def _apply_guided_input(self, window) -> None:
        if getattr(window, "guided_input", None) is None:
            return
        self._guided_applying = True
        try:
            self._apply_current_guided_values()
        except (TypeError, ValueError) as exc:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(window, "入力内容を確認してください", str(exc))
            return
        finally:
            self._guided_applying = False
        if window.recalculate():
            window.tabs.setCurrentIndex(0)


def install_completion_audit(window) -> CompletionAuditController:
    existing = getattr(window, "_completion_audit_controller", None)
    if isinstance(existing, CompletionAuditController):
        return existing
    controller = CompletionAuditController(window)
    window._completion_audit_controller = controller
    return controller
