import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from lifecanvas.guided_ui import LifeCanvasWindow
from lifecanvas.models import ChildPlan


def _app():
    return QApplication.instance() or QApplication([])


def _close(app, window):
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, 0)
    app.processEvents()


def test_zero_or_one_child_plan_syncs_without_changing_plan():
    app = _app()
    window = LifeCanvasWindow()
    try:
        cases = [
            [],
            [ChildPlan(name="第一子", birth_offset=4)],
        ]
        for children in cases:
            window.plan.children = [child.model_copy(deep=True) for child in children]
            window._sync_inputs_from_plan()

            assert window.plan.children == children
            assert window.child_editor.table.rowCount() == len(children)
    finally:
        _close(app, window)
