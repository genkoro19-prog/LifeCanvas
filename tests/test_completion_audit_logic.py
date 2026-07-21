import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from lifecanvas.cashflow_event_editor import CashFlowEventEditor
from lifecanvas.models import PersonalDebt
from lifecanvas.personal_debt_editor import PersonalDebtEditor
from lifecanvas.policy_audit import AuditedDebtRuntime, install_policy_audit
from lifecanvas.policy_engine import SimulationEngine
from lifecanvas.sample import build_genki_family_plan


def _app():
    return QApplication.instance() or QApplication([])


def test_dynamic_cashflow_event_rows_emit_changed():
    _app()
    editor = CashFlowEventEditor(build_genki_family_plan())
    calls: list[bool] = []
    editor.changed.connect(lambda: calls.append(True))
    try:
        editor.add_row()
        assert calls
        calls.clear()
        editor.table.cellWidget(editor.table.rowCount() - 1, 4).setText("250000")
        editor.table.cellWidget(editor.table.rowCount() - 1, 4).editingFinished.emit()
        assert calls
    finally:
        editor.close()


def test_invalid_personal_debt_is_not_silently_ignored():
    _app()
    editor = PersonalDebtEditor(build_genki_family_plan())
    try:
        editor.add_debt()
        row = editor.table.rowCount() - 1
        editor.table.item(row, 2).setText("abc")
        with pytest.raises(ValueError, match="月額は数字"):
            editor.debts()
    finally:
        editor.close()


def test_unpaid_installment_does_not_consume_remaining_term():
    debt = PersonalDebt(
        debt_id="debt",
        name="借入",
        borrower="wife",
        monthly_payment=10_000,
        remaining_months=1,
        current_balance=20_000,
    )
    runtime = AuditedDebtRuntime(debt=debt, remaining_months=1, balance=20_000)
    due = runtime.due(0)
    runtime.record(0, due > 0)
    assert runtime.remaining_months == 1
    assert runtime.liability_at(0) == pytest.approx(20_000)
    assert runtime.due(1) == pytest.approx(10_000)


def test_bonus_payment_timing_is_relative_to_debt_start():
    debt = PersonalDebt(
        debt_id="bonus",
        name="ボーナス返済",
        borrower="husband",
        monthly_payment=10_000,
        remaining_months=12,
        current_balance=200_000,
        start_offset_months=2,
        bonus_payment=50_000,
    )
    runtime = AuditedDebtRuntime(debt=debt, remaining_months=12, balance=200_000)
    assert runtime.due(2) == pytest.approx(10_000)
    runtime.record(10_000, True)
    assert runtime.due(7) == pytest.approx(60_000)


def test_debt_balance_is_deducted_from_net_worth():
    install_policy_audit()
    base = build_genki_family_plan()
    base.simulation_years = 1
    base.wallets.mode = "separate"
    base.personal_debts = []
    without_debt = SimulationEngine(base.model_copy(deep=True)).run()[0]

    with_plan = base.model_copy(deep=True)
    with_plan.personal_debts = [
        PersonalDebt(
            debt_id="student",
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=96,
            current_balance=1_200_000,
        )
    ]
    with_debt = SimulationEngine(with_plan).run()[0]
    assert with_debt.net_worth < without_debt.net_worth - 1_000_000


def test_combined_mode_rejects_personal_debt_instead_of_ignoring_it():
    install_policy_audit()
    plan = build_genki_family_plan()
    plan.wallets.mode = "combined"
    plan.personal_debts = [
        PersonalDebt(
            debt_id="ignored-before",
            name="奨学金",
            borrower="wife",
            monthly_payment=15_000,
            remaining_months=12,
        )
    ]
    with pytest.raises(ValueError, match="夫婦の預金を分ける"):
        SimulationEngine(plan).run()
