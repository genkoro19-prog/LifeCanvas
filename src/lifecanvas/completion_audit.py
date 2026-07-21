from __future__ import annotations

from types import MethodType

from PySide6.QtWidgets import QMessageBox, QPushButton


class CompletionAuditController:
    """Keep explicit actions, PDF export, and both input pages synchronized."""

    def __init__(self, window):
        self.window = window
        self.original_recalculate = window.recalculate
        self.original_export_report = window.export_report
        self._applying_guided = False
        self._syncing = False

        window.recalculate = MethodType(self._recalculate, window)
        window.export_report = MethodType(self._export_report, window)

        timer = getattr(window, "_auto_timer", None)
        if timer is not None:
            try:
                timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                pass
            timer.timeout.connect(window.recalculate)

        guided = getattr(window, "guided_input", None)
        if guided is not None:
            try:
                guided.applyRequested.disconnect()
            except (RuntimeError, TypeError):
                pass
            guided.applyRequested.connect(self._apply_guided_input)

        recalc_button = getattr(window, "recalc_button", None)
        if isinstance(recalc_button, QPushButton):
            try:
                recalc_button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            recalc_button.clicked.connect(lambda _checked=False: window.recalculate())

        for button in window.findChildren(QPushButton):
            if button.objectName() == "pdfButton" or button.text() == "PDFレポート":
                try:
                    button.clicked.disconnect()
                except (RuntimeError, TypeError):
                    pass
                button.clicked.connect(lambda _checked=False: window.export_report())

    def _apply_guided_values(self) -> None:
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

    def _sync_guided_from_plan(self) -> None:
        if self._syncing:
            return
        window = self.window
        self._syncing = True
        try:
            guided = getattr(window, "guided_input", None)
            if guided is not None:
                guided.load(window.plan)
            quick = getattr(window, "quick_policy", None)
            if quick is not None:
                quick.load(window.plan)
        finally:
            self._syncing = False

    def _recalculate(self, window, *_args) -> bool:
        timer = getattr(window, "_auto_timer", None)
        if timer is not None and timer.isActive():
            timer.stop()

        guided = getattr(window, "guided_input", None)
        tabs = getattr(window, "tabs", None)
        on_guided_page = guided is not None and tabs is not None and tabs.currentWidget() is guided
        if on_guided_page and not self._applying_guided:
            try:
                self._applying_guided = True
                self._apply_guided_values()
            except (TypeError, ValueError) as exc:
                QMessageBox.warning(window, "入力内容を確認してください", str(exc))
                return False
            finally:
                self._applying_guided = False

        before = getattr(window, "results", None)
        self.original_recalculate()
        after = getattr(window, "results", None)
        success = bool(after) and after is not before
        detailed = getattr(window, "detailed_settings", None)
        if not success:
            if detailed is not None:
                detailed.status.setText("入力エラー")
            return False

        self._sync_guided_from_plan()
        if detailed is not None:
            detailed.status.setText("反映済み")
        return True

    def _apply_guided_input(self) -> None:
        window = self.window
        try:
            self._applying_guided = True
            self._apply_guided_values()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(window, "入力内容を確認してください", str(exc))
            return
        finally:
            self._applying_guided = False
        if window.recalculate():
            window.tabs.setCurrentIndex(0)

    def _export_report(self, window) -> None:
        # Export must never use stale results that predate the latest controls.
        if not window.recalculate():
            return
        self.original_export_report()


def install_completion_audit(window) -> CompletionAuditController:
    existing = getattr(window, "_completion_audit_controller", None)
    if isinstance(existing, CompletionAuditController):
        return existing
    controller = CompletionAuditController(window)
    window._completion_audit_controller = controller
    return controller
