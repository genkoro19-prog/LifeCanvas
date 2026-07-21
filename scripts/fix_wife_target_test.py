from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests/test_household_policy_phases.py"
text = path.read_text(encoding="utf-8")
old = '''    assert row.wife_cash_end == pytest.approx(3_000_000)\n    assert row.wife_additional_nisa_contributed == pytest.approx(1_100_000)\n'''
new = '''    assert row.wife_cash_end == pytest.approx(plan.wallets.wife_target_cash)\n    expected_extra = (\n        plan.wallets.initial_wife_cash\n        + row.wife_personal_income\n        - row.wife_personal_spending\n        - plan.wallets.wife_target_cash\n    )\n    assert row.wife_additional_nisa_contributed == pytest.approx(expected_extra)\n'''
if old not in text:
    raise RuntimeError("wife target test block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
