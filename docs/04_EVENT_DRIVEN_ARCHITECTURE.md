# イベントドリブン・アーキテクチャ設計書 (Event-Driven Architecture)

## 1. 概要
LifeCanvasは、従来の「項目一覧ベース（スプレッドシート型）」の設計から、特定の時系列で発生する様々なライフイベントを起点としてシミュレーション状態を変化させる**「イベントドリブン・アーキテクチャ」**へと進化します。

「何年に何が起きるか」というイベントをタイムライン上に配置するだけで、収入・支出・投資・住宅・教育などの複雑なシミュレーションが自動的に追従・連動する拡張性の高い設計です。

## 2. コアコンセプト
シミュレーションの対象期間（例: 40年間）において、各年（Year）ごとに**イベントキュー**を評価します。

1. **State（状態）の保持**: 家族の年齢、資金残高、現在の給与、保有住宅、継続中のローンなどの状態を変数として持ちます。
2. **Event（イベント）の発火**: 特定の年に達した瞬間に、該当するイベントが発火し、State（状態）を書き換えます。
3. **Calculate（計算）**: 変更された最新のStateを用いて、その年のキャッシュフローと純資産を計算します。

## 3. 主要なイベントの種類 (Event Types)

すべてのアクションを以下のサブイベントとして定義します。ユーザーはUIからこれらのイベントを任意の年に追加するだけです。

### 3.1 家族・キャリア (Career & Family Events)
* `BirthEvent`: 家族の追加（教育費発生フラグON、児童手当計算ON）
* `JobChangeEvent`: 転職、退職、パート化、産休・育休開始/復帰（年収の変更）
* `RetirementEvent`: 定年退職（年金受給フラグON、給与OFF）

### 3.2 投資・資金 (Investment & Finance Events)
* `DepositChangeEvent`: 月額積立金や利回り（NISA・現金）の変更
* `FundWithdrawalEvent`: 資金の引き出し（教育費ピーク時等の意図的な切り崩し）

### 3.3 住宅・不動産 (Housing Events)
* `HousePurchaseEvent`: 住宅の購入（ローン開始、維持費開始）
* `LoanPrepaymentEvent`: ローンの繰り上げ一括返済・一部返済
* `HouseSaleEvent`: 住宅売却（売却益の現金注入、ローン残債の償還）
* `HouseRentOutEvent`: 住宅の賃貸化（家賃収入の追加、固定資産税の継続）

### 3.4 支出・その他 (Expense Events)
* `CarPurchaseEvent`: 車の購入（買替サイクルの開始）
* `OneTimeExpenseEvent`: 一時的な支出（旅行、結婚式支援、負債返済など）
* `OneTimeIncomeEvent`: 一時的な収入（相続、宝くじなど）

## 4. エンジンの処理フロー

```python
# 擬似コード
def run_simulation(timeline_events):
    state = InitialState()
    
    for year in range(40):
        # 1. その年の一時イベントや状態変更イベントを発火
        current_events = timeline_events.get(year, [])
        for event in current_events:
            event.apply(state) # stateを上書き/変更
            
        # 2. 最新のstateに基づいて年間収支を計算
        income = state.calculate_total_income()
        expense = state.calculate_total_expense()
        
        # 3. キャッシュフロー精算と資産残高の更新
        state.cash_balance += (income - expense)
        state.update_investments()
        
        # 4. レポート記録
        record_year_result(year, state)
```

## 5. 分析・AI連動
この設計により、「もし〇〇年に〇〇のイベントを起こしたらどうなるか？」というシナリオ分岐が容易になります。
AIエンジンは、純資産がマイナスになる年を特定し、そこに**「投資積立変更イベント」**や**「支出削減イベント」**を自動的に挿入・提案するだけで、家計改善シミュレーションを提示できるようになります。
