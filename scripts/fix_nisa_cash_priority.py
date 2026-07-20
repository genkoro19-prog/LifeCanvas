from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Automatic extra investment must be opt-in. Older plans without the field
# therefore keep cash instead of unexpectedly sweeping it into NISA.
replace_once(
    "src/lifecanvas/models.py",
    '    auto_invest_enabled: bool = True\n',
    '    auto_invest_enabled: bool = False\n',
)

# Wife surplus belongs to her cash after her base NISA and household contribution.
# Automatic investment only applies to the husband cash above his target. A wife
# NISA addition funded by the husband is handled separately by the transfer rule.
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                if wallets.auto_invest_enabled:\n                    wife_extra_available = max(0.0, wife_flow_remaining)\n                    wife_extra_desired = min(wallets.auto_extra_monthly_cap, wife_extra_available)\n                    wife_cash, wife_extra = _buy_from_cash(wife_cash, wife_state, wife_extra_desired)\n                    year.wife_extra_nisa += wife_extra\n                    year.planned_nisa += wife_extra_desired\n\n                    husband_extra_desired = min(\n''',
    '''                if wallets.auto_invest_enabled:\n                    # Wife surplus remains in the wife's cash account. Only her configured\n                    # base NISA is paid from her own income; husband-funded additions are\n                    # processed by the explicit spouse-transfer rule below.\n                    husband_extra_desired = min(\n''',
)

replace_once(
    "src/lifecanvas/wallet_editor.py",
    '        self.auto_invest = QCheckBox("目標預金を超えた余剰をNISAへ自動追加する")\n',
    '        self.auto_invest = QCheckBox("夫の目標預金を超えた余剰を夫NISAへ自動追加する")\n',
)

# Regression test: enabling husband auto-invest must never sweep wife surplus.
replace_once(
    "tests/test_household_policy_phases.py",
    '''def test_spousal_nisa_transfer_is_capped_at_annual_management_limit(monkeypatch):\n''',
    '''def test_auto_invest_does_not_sweep_wife_surplus(monkeypatch):\n    plan, rows = _plan(wife_income=3_600_000, household=0)\n    plan.wallets.auto_invest_enabled = True\n    plan.wallets.husband_target_cash = 100_000_000\n    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")\n    wife.monthly_contribution = 0\n    row = _run(plan, rows, monkeypatch)\n    assert row.wife_additional_nisa_contributed == 0\n    assert row.wife_nisa_contributed == 0\n    assert row.wife_cash_end == pytest.approx(row.wife_personal_income)\n\n\ndef test_spousal_nisa_transfer_is_capped_at_annual_management_limit(monkeypatch):\n''',
)

print("Applied NISA cash-priority fixes.")
