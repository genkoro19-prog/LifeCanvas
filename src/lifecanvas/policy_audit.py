from __future__ import annotations

from dataclasses import dataclass, field

from .models import PersonalDebt


_RUNTIME_COLLECTOR: list["AuditedDebtRuntime"] | None = None


@dataclass
class AuditedDebtRuntime:
    """Fixed-payment debt runtime that never erases an unpaid balance."""

    debt: PersonalDebt
    remaining_months: int
    balance: float
    initial_balance: float = field(init=False)
    history: dict[int, float] = field(default_factory=dict, init=False)
    _last_due: float = field(default=0.0, init=False)
    _last_month: int = field(default=-1, init=False)

    def __post_init__(self) -> None:
        if self.balance <= 0:
            bonus_count = (max(0, self.remaining_months) + 5) // 6
            self.balance = (
                self.debt.monthly_payment * max(0, self.remaining_months)
                + self.debt.bonus_payment * bonus_count
            )
        self.initial_balance = max(0.0, self.balance)
        if _RUNTIME_COLLECTOR is not None:
            _RUNTIME_COLLECTOR.append(self)

    def due(self, absolute_month: int) -> float:
        self._last_month = absolute_month
        self._last_due = 0.0
        if absolute_month < self.debt.start_offset_months or self.balance <= 0:
            return 0.0
        if self.debt.annual_interest_rate > 0:
            self.balance += self.balance * (self.debt.annual_interest_rate / 100.0 / 12.0)
        relative_month = absolute_month - self.debt.start_offset_months
        amount = self.debt.monthly_payment
        if self.debt.bonus_payment and relative_month % 6 == 5:
            amount += self.debt.bonus_payment
        self._last_due = min(max(0.0, amount), self.balance)
        return self._last_due

    def record(self, actual: float, was_due: bool) -> None:
        if not was_due or self._last_month < 0:
            return
        actual = min(max(0.0, actual), self.balance)
        self.balance = max(0.0, self.balance - actual)
        # A missed or partial installment extends the term instead of silently
        # consuming one of the remaining months.
        if self._last_due > 0 and actual + 1 >= self._last_due:
            self.remaining_months = max(0, self.remaining_months - 1)
        self.history[self._last_month] = self.balance

    def liability_at(self, absolute_month: int) -> float:
        values = [month for month in self.history if month <= absolute_month]
        if not values:
            return self.initial_balance
        return max(0.0, self.history[max(values)])


def _validate_supported_debts(plan) -> None:
    if not plan.personal_debts:
        return
    if plan.wallets.mode != "separate":
        raise ValueError(
            "個人借入・奨学金は『夫婦の預金を分ける』家計モードで設定してください。"
        )
    for debt in plan.personal_debts:
        if debt.repayment_method != "fixed":
            raise ValueError(f"{debt.name}の返済方式は現在『月額固定』のみ対応しています。")
        if debt.payment_source not in ("borrower", "spouse"):
            raise ValueError(f"{debt.name}の支払元は本人または配偶者を選択してください。")
        if debt.borrower == "husband" and debt.payment_source == "spouse":
            raise ValueError(
                f"{debt.name}は夫の借入を妻口座から払う設定です。"
                "現在は借入者本人の口座から支払う設定にしてください。"
            )


def install_policy_audit() -> None:
    """Patch the active policy engine once with audited debt behavior."""

    from . import policy_engine

    if getattr(policy_engine, "_completion_policy_audit_installed", False):
        return

    original_run = policy_engine.SimulationEngine.run
    policy_engine.DebtRuntime = AuditedDebtRuntime

    def audited_run(engine):
        global _RUNTIME_COLLECTOR
        _validate_supported_debts(engine.plan)
        collector: list[AuditedDebtRuntime] = []
        _RUNTIME_COLLECTOR = collector
        try:
            results = original_run(engine)
        finally:
            _RUNTIME_COLLECTOR = None

        if not collector or not results:
            return results

        elapsed_months = 0
        last_liability = 0.0
        for row in results:
            elapsed_months += max(1, row.months)
            last_liability = sum(
                runtime.liability_at(elapsed_months - 1) for runtime in collector
            )
            row.net_worth -= last_liability

        if last_liability > 1:
            results[-1].warnings.append(
                f"最終年の個人借入残高 {last_liability/10_000:,.0f}万円を純資産から控除"
            )
        return results

    policy_engine.SimulationEngine.run = audited_run
    policy_engine._completion_policy_audit_installed = True
