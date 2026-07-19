# AI実装用プロンプト集

AIコーディングアシスタントにLifeCanvasの各コンポーネントを実装させるためのプロンプト集。

各プロンプトは独立して使用可能。依存関係がある場合は順番に実行する。

---

## Prompt 1: プロジェクト基盤

```
Python + PySide6 のWindowsデスクトップアプリ「LifeCanvas」を作成してください。

技術スタック:
- Python 3.12+
- PySide6（UI）
- Pydantic（データモデル）
- SQLAlchemy + SQLite（永続化）
- matplotlib（グラフ）
- MVVM アーキテクチャ

ディレクトリ構成:
- core/models/ → Pydantic モデル
- core/calculator/ → 計算ロジック（純Python、UI依存なし）
- core/engine.py → シミュレーションエンジン
- core/database.py → SQLAlchemy ORM定義
- ui/views/ → PySide6 View
- ui/viewmodels/ → ViewModel（Signal/Slot）
- ui/styles.py → QSSテーマ
- tests/ → pytest

requirements.txt を作成し、仮想環境でセットアップしてください。
```

---

## Prompt 2: データモデル

```
以下のPydanticモデルを core/models/ に作成してください。

1. FamilyMember
   - name, relation(husband/wife/child/other), birth_date, annual_income
   - bonus, salary_growth_rate, retirement_age, pension_start_age
   - occupation, income_modifiers(dict)
   - get_income_for_year(elapsed_years, family_state) メソッド

2. LifeEvent
   - event_id, name, category, elapsed_year
   - one_time_cost, one_time_income, details(dict)

3. HousePlan + LoanPlan
   - 購入価格、ローン（固定/変動/金利推移/繰上返済）
   - 売却、賃貸運用、修繕費、固定資産税、火災保険
   - 住宅ローン控除（残高×0.7%、上限21万、13年）

4. InvestmentAccount
   - account_type(nisa/ideco/taxable/cash)
   - monthly_deposit, annual_return_rate, changes_schedule
   - simulate_year() で月次複利計算

5. CarPlan
   - 購入価格、買替サイクル、維持費、車検、保険、ローン

6. InsurancePlan
   - 保険タイプ(life/medical/fire/car)、保険料、期間、満期返戻金

7. EducationPlan
   - 子供ごとの教育費テンプレート（保育園〜大学）
   - get_annual_cost(elapsed_years) で年齢に応じた費用算出

すべてPydanticのBaseModelを使用。JSON変換はmodel_dump() / model_validate()で対応。
```

---

## Prompt 3: 計算ロジック

```
以下の計算モジュールを core/calculator/ に作成してください。

1. TaxCalculator (tax.py)
   - 給与所得控除の計算
   - 課税所得の算出
   - 所得税（累進税率・速算表）
   - 住民税（課税所得×10% + 均等割5,000円）
   - 社会保険料（額面×15%概算）
   - 住宅ローン控除の相殺（所得税→住民税の順）
   - iDeCo所得控除
   - get_net_income(annual_income, is_employee, housing_deduction, ideco_deduction)

2. LoanCalculator (loan.py)
   - 元利均等返済の年次スケジュール
   - 元金均等返済の年次スケジュール
   - 変動金利対応（interest_adjustments辞書による年次金利変更）
   - calculate_amortization_schedule() → List[dict]
```

---

## Prompt 4: シミュレーションエンジン

```
core/engine.py にシミュレーションエンジンを実装してください。

40年間の年次ループで以下を順番に計算:

1. 家族の年齢更新・誕生判定
2. 収入（年収・昇給・定年後0円）
3. 年金（65歳以降。会社員: 180万/年、自営業: 78万/年）
4. 税金・社会保険（TaxCalculator使用）
5. 住宅ローン控除
6. ライフイベント処理（一時収支）
7. 住宅費用（ローン返済・固定資産税・修繕・賃貸化トリガー）
8. 教育費（EducationPlan.get_annual_cost()）
9. 車費用
10. 保険料
11. 給付金（児童手当・育休給付金）
12. 生活費（基本240万 + 子供1人30万）
13. 投資積立（月次複利）
14. キャッシュフロー集計
15. 現金不足時の投資取崩し
16. 純資産算出（現金 + 投資 + 不動産評価 - ローン残高）

戻り値: List[Dict] で年次データ配列。
```

---

## Prompt 5: UI

```
PySide6でNotion風UIを実装してください。

1. MainWindow
   - 左: Sidebar（200px固定、メニューボタン8個）
   - 右: QStackedWidget（各画面）
   - メニューバー: ファイル管理（新規/保存/読込/JSON入出力）

2. Dashboard
   - サマリーカード4枚（資産寿命・赤字有無・NISA到達額・FIRE判定）
   - matplotlib グラフ（キャッシュフロー棒グラフ + 資産折れ線）
   - リアルタイム調整スライダー（年収・利回り）

3. InputPanels（QTabWidget）
   - 家族構成タブ: テーブル + メンバー追加/削除
   - 住宅タブ: フォーム入力
   - 投資タブ: テーブル + 口座追加
   - 車タブ: フォーム入力
   - 保険タブ: テーブル + 追加

4. ComparisonView: シナリオ比較グラフ
5. ReportView: PDF/Excelエクスポートボタン

QSSスタイル:
- 背景: #f7f6f3（サイドバー）、#ffffff（コンテンツ）
- アクセント: #2383e2
- フォント: Segoe UI / Meiryo
- ボタン: 角丸4px、ホバーエフェクト

すべてのView → ViewModel → Engine の単方向データフローを維持。
パラメータ変更時にtrigger_recalculation()で即時再計算。
```

---

## Prompt 6: レポート出力

```
core/report_generator.py にPDF・Excel出力を実装してください。

PDF（ReportLab）:
- A4縦、日本語フォント（C:\Windows\Fonts\msgothic.ttc）
- タイトル + プラン名
- キャッシュフローテーブル（5年おき）
- AI診断コメント
- テーブルスタイル: ヘッダー#2383e2、交互行色

Excel（openpyxl）:
- シート「キャッシュフロー推移」
- 全年度の収支データ（万円単位）
- ヘッダー装飾・列幅自動調整
- MergedCell対策済み（get_column_letterを使用）
```

---

## Prompt 7: サンプルデータ投入

```
main.py のsetup_sample_project()で以下のデータを投入してください。

docs/02_SAMPLE_PROJECT.md の内容に準拠。

- 夫34歳/妻28歳/子供2人（5・6年後誕生）
- 住宅3170万/40年ローン/変動1.68%
- 26年後に繰上完済→賃貸運用（年75万）
- NISA: 夫月6万（5年後→10万）、妻月3万、年利4%
- 現金積立: 夫月4万
- 車: 1年後購入、年間35万維持
- 教育費: テンプレート適用

起動直後にダッシュボードにグラフが表示される状態にしてください。
```
