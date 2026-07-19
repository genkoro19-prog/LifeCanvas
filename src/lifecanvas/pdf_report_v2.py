from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path

from matplotlib.figure import Figure
from PySide6.QtCore import QSizeF
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument

from .insights import analyze_plan, dominant_expense
from .models import ProjectPlan, YearResult
from .plotting import configure_japanese_matplotlib
from .rent_engine import is_rental_move


def _man(value: float) -> str:
    return f"{value / 10_000:,.0f}万円"


def _chart_data_uri(results: list[YearResult]) -> str:
    configure_japanese_matplotlib()
    figure = Figure(figsize=(9.3, 4.2), dpi=120)
    axis = figure.add_subplot(111)
    years = [row.calendar_year for row in results]
    axis.plot(years, [row.net_worth / 10_000 for row in results], label="純資産", linewidth=2.2)
    axis.plot(years, [row.cash_end / 10_000 for row in results], label="現預金", linewidth=1.8)
    axis.plot(
        years,
        [row.investments_market_value / 10_000 for row in results],
        label="投資資産",
        linewidth=1.8,
    )
    axis.plot(
        years,
        [-row.mortgage_balance / 10_000 for row in results],
        label="住宅ローン",
        linestyle="--",
        linewidth=1.5,
    )
    axis.axhline(0, linewidth=0.8, alpha=0.45)
    axis.set_title("資産・負債の推移")
    axis.set_xlabel("年")
    axis.set_ylabel("万円")
    axis.grid(True, alpha=0.22)
    axis.legend(ncol=2, loc="upper left", frameon=False)
    figure.subplots_adjust(left=0.08, right=0.98, bottom=0.14, top=0.88)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _event_rows(results: list[YearResult]) -> str:
    rows: list[str] = []
    for result in results:
        if not result.events and not result.warnings:
            continue
        text = " / ".join([*result.events, *result.warnings])
        rows.append(
            f"<tr><td>{result.calendar_year}</td><td>{result.husband_age}/{result.wife_age}歳</td>"
            f"<td>{escape(text)}</td><td>{_man(result.cash_end)}</td></tr>"
        )
    return "".join(rows[:28])


def _annual_rows(results: list[YearResult]) -> str:
    rows: list[str] = []
    for result in results:
        rows.append(
            "<tr>"
            f"<td>{result.calendar_year}</td>"
            f"<td>{_man(result.total_income)}</td>"
            f"<td>{_man(result.consumption_total)}</td>"
            f"<td>{_man(result.living_surplus)}</td>"
            f"<td>{_man(result.cash_end)}</td>"
            f"<td>{_man(result.investments_market_value)}</td>"
            f"<td>{_man(result.net_worth)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _housing_label(plan: ProjectPlan) -> str:
    if is_rental_move(plan):
        year = plan.start_year + (plan.housing.move_offset or 0)
        return f"{year}年に今の家を売り、月{plan.housing.new_home_monthly_cost / 10_000:,.1f}万円の賃貸へ移る"
    labels = {
        "none": "現在の家に住み続ける",
        "sell": "今の家を売って新しい家を買う",
        "keep": "今の家を残して別の住まいへ移る",
    }
    return labels.get(plan.housing.move_mode, plan.housing.move_mode)


def export_pdf(plan: ProjectPlan, results: list[YearResult], path: str | Path) -> Path:
    """Create a compact, printable PDF without external services or APIs."""

    if not results:
        raise ValueError("PDFを作成する前に計算を実行してください。")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    insight = analyze_plan(plan, results)
    minimum_cash = min(results, key=lambda row: row.cash_end)
    retirement = next(
        (row for row in results if row.husband_age == plan.husband.retirement_age),
        results[-1],
    )
    difficult = "".join(
        f"<li>{row.calendar_year}年：収支 {_man(row.living_surplus)}（主な支出：{escape(dominant_expense(row))}）</li>"
        for row in insight.difficult_years
    )
    children = "、".join(child.name for child in plan.children) or "なし"
    cars = "、".join(car.name for car in plan.cars if car.enabled) or "なし"
    chart = _chart_data_uri(results)

    html = f"""
    <html><head><meta charset='utf-8'><style>
    @page {{ size: A4; margin: 16mm; }}
    body {{ font-family: 'Yu Gothic', 'Meiryo', 'Noto Sans CJK JP', sans-serif; color:#172033; font-size:10pt; }}
    h1 {{ color:#183153; font-size:24pt; margin-bottom:2px; }}
    h2 {{ color:#24476f; border-bottom:2px solid #dbe7f4; padding-bottom:5px; margin-top:20px; }}
    .muted {{ color:#6b778c; }}
    .cards {{ width:100%; border-collapse:separate; border-spacing:7px; }}
    .card {{ background:#f3f7fc; border:1px solid #dce6f2; padding:10px; vertical-align:top; }}
    .value {{ font-size:16pt; font-weight:bold; color:#163a67; }}
    table.data {{ width:100%; border-collapse:collapse; font-size:8.5pt; }}
    table.data th {{ background:#eaf1f8; color:#344b68; padding:5px; border:1px solid #d8e1ec; }}
    table.data td {{ padding:4px; border:1px solid #e1e7ef; }}
    .pagebreak {{ page-break-before: always; }}
    .chart {{ width:100%; }}
    .judge {{ background:#eef8f4; border-left:5px solid #2f8b70; padding:12px; }}
    </style></head><body>
    <h1>LifeCanvas</h1>
    <div class='muted'>{escape(plan.name)}　将来設計レポート</div>
    <p class='muted'>開始年：{plan.start_year}年　シミュレーション期間：{plan.simulation_years}年</p>

    <table class='cards'><tr>
      <td class='card'><div>将来判定</div><div class='value'>{escape(insight.status)}</div><div>{escape(insight.status_note)}</div></td>
      <td class='card'><div>最低現預金</div><div class='value'>{_man(minimum_cash.cash_end)}</div><div>{minimum_cash.calendar_year}年</div></td>
      <td class='card'><div>夫の定年時純資産</div><div class='value'>{_man(retirement.net_worth)}</div><div>{retirement.calendar_year}年</div></td>
    </tr></table>

    <h2>計画の概要</h2>
    <table class='data'>
      <tr><th>家族</th><td>夫 {plan.husband.current_age}歳／妻 {plan.wife.current_age}歳／子ども：{escape(children)}</td></tr>
      <tr><th>現在の現預金</th><td>{_man(plan.initial_cash)}</td></tr>
      <tr><th>住宅</th><td>{escape(_housing_label(plan))}</td></tr>
      <tr><th>車</th><td>{escape(cars)}</td></tr>
      <tr><th>年金</th><td>夫 {_man(plan.husband.annual_pension)}／妻 {_man(plan.wife.annual_pension)}</td></tr>
    </table>

    <h2>資産推移</h2>
    <img class='chart' src='{chart}' />

    <h2>確認しておきたい年</h2>
    <div class='judge'><ul>{difficult or '<li>大きな資金悪化は見つかりませんでした。</li>'}</ul></div>

    <div class='pagebreak'></div>
    <h2>主なライフイベント</h2>
    <table class='data'><tr><th>年</th><th>夫/妻</th><th>イベント・注意</th><th>年末現預金</th></tr>
    {_event_rows(results)}</table>

    <div class='pagebreak'></div>
    <h2>年次キャッシュフロー</h2>
    <table class='data'><tr><th>年</th><th>収入</th><th>支出</th><th>収支</th><th>現預金</th><th>投資</th><th>純資産</th></tr>
    {_annual_rows(results)}</table>
    <p class='muted'>本レポートは入力された前提に基づく試算です。税・社会保険・運用結果などを保証するものではありません。</p>
    </body></html>
    """

    writer = QPdfWriter(str(target))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setResolution(120)
    writer.setTitle(f"LifeCanvas - {plan.name}")
    document = QTextDocument()
    document.setPageSize(QSizeF(writer.width(), writer.height()))
    document.setHtml(html)
    document.print_(writer)
    return target
