from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class LifeEvent:
    """
    統一ライフイベントモデル
    一時的な収支から、状態の上書き（転職、NISA変更など）まで
    すべてのシミュレーション操作をこのクラスで表現します。
    """
    event_id: str
    name: str
    elapsed_year: int
    category: str = "other"  # job, investment, housing, family, other
    
    # 【旧仕様との互換＆一時的な収支】
    one_time_cost: float = 0.0
    one_time_income: float = 0.0
    
    # 【新仕様・状態変更のためのパラメータ】
    # dict形式で変更対象のキーと値を保持します
    # 例: {"target": "wife", "action": "update_salary", "value": 576000}
    # 例: {"target": "nisa_husband", "action": "update_deposit", "value": 100000}
    details: Dict[str, Any] = field(default_factory=dict)
    
    target_member_name: Optional[str] = None

    def apply_to_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        （将来用）イベント発火時にシミュレーションのStateを書き換えるロジックを実装します。
        現在のPhase 1.5では、辞書ベースの設定変更で対応します。
        """
        # 単純なキャッシュの増減だけの場合
        if self.one_time_income > 0:
            state["cash_balance"] = state.get("cash_balance", 0) + self.one_time_income
        if self.one_time_cost > 0:
            state["cash_balance"] = state.get("cash_balance", 0) - self.one_time_cost

        # 状態の上書き(details に定義された "action" による)
        if "action" in self.details:
            action = self.details["action"]
            target = self.details.get("target")
            val = self.details.get("value")
            
            if action == "update_salary" and target:
                if "salary_overrides" not in state:
                    state["salary_overrides"] = {}
                state["salary_overrides"][target] = val

            elif action == "update_benefits" and target:
                if "benefit_overrides" not in state:
                    state["benefit_overrides"] = {}
                # 例: value=1500000 なら対象者の非課税収入として加える
                state["benefit_overrides"][target] = val

            elif action == "update_nisa_deposit" and target:
                if "investment_overrides" not in state:
                    state["investment_overrides"] = {}
                state["investment_overrides"][target] = val
                
            elif action == "trigger_house_sale" and target is not None:
                if "housing_commands" not in state:
                    state["housing_commands"] = {}
                state["housing_commands"][target] = "sell_and_rent"

        return state
        
    def process_event(self, simulation_year: int) -> Dict[str, Any]:
        """
        旧来のエンジン（core/engine.py）から呼ばれる互換用メソッド。
        シミュレーションエンジンに渡す一時的収支命令命令データを生成します。
        """
        if simulation_year == self.elapsed_year:
            return {
                "name": self.name,
                "category": self.category,
                "cost": self.one_time_cost,
                "income": self.one_time_income,
                "details": self.details,
                "target_member": self.target_member_name
            }
        return {}
