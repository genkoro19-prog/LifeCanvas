from pathlib import Path

path = Path(__file__).resolve().parents[1] / "src/lifecanvas/policy_engine.py"
text = path.read_text(encoding="utf-8")
old = '''    else:\n        floor = plan.wallets.wife_target_cash\n        values = [row.wife_cash_end for row in results]\n'''
new = '''    else:\n        # Wife target cash is the threshold for optional extra investment, not a hard minimum.\n        floor = 0.0\n        values = [row.wife_cash_end for row in results]\n'''
if old not in text:
    raise RuntimeError("wife recommendation floor block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
