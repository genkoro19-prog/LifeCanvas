from pathlib import Path

path = Path(__file__).resolve().parents[1] / "src/lifecanvas/pdf_report_v2.py"
text = path.read_text(encoding="utf-8")
needle = "def _event_rows(results: list[YearResult]) -> str:\n"
alias = '''def _chart_data_uri(results: list[YearResult], separate: bool = False) -> str:
    """Backward-compatible data URI helper used by existing chart dimension tests."""
    import base64

    raw = _chart_png_bytes(results, separate)
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


'''
if alias not in text:
    if needle not in text:
        raise RuntimeError("PDF insertion point not found")
    text = text.replace(needle, alias + needle, 1)
path.write_text(text, encoding="utf-8")
