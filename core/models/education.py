from dataclasses import dataclass, field
from typing import Dict

@dataclass
class EducationPlan:
    """
    教育費プランモデル
    子供ごとの年齢ステージに応じた年間教育費用を管理します。
    """
    child_name: str
    birth_year_offset: int          # シミュレーション開始から何年後に誕生するか (0は開始時点で生まれている)
    
    # 区分ごとの年間学習費用のデフォルトテンプレート (日本FP協会等の統計に基づく目安)
    # nursery: 保育園, kindergarten: 幼稚園, elementary: 小学校,
    # junior_high: 中学校, high_school: 高校, university: 大学
    stage_costs: Dict[str, float] = field(default_factory=lambda: {
        "nursery": 150000.0,
        "kindergarten": 200000.0,
        "elementary": 350000.0,
        "junior_high": 550000.0,
        "high_school": 550000.0,
        "university": 1500000.0
    })

    def get_annual_cost(self, elapsed_years: int) -> float:
        """
        指定されたシミュレーション経過年における教育費用を算出します。
        """
        # まだ生まれていない場合
        if elapsed_years < self.birth_year_offset:
            return 0.0

        child_age = elapsed_years - self.birth_year_offset
        
        # 年齢に応じた就学ステージ判定 (一般的な日本の学制ベース)
        # 0歳〜2歳: 保育園等 (nursery)
        if 0 <= child_age < 3:
            return self.stage_costs.get("nursery", 0.0)
        # 3歳〜5歳: 幼稚園等 (kindergarten)
        elif 3 <= child_age < 6:
            return self.stage_costs.get("kindergarten", 0.0)
        # 6歳〜11歳: 小学校 (elementary)
        elif 6 <= child_age < 12:
            return self.stage_costs.get("elementary", 0.0)
        # 12歳〜14歳: 中学校 (junior_high)
        elif 12 <= child_age < 15:
            return self.stage_costs.get("junior_high", 0.0)
        # 15歳〜17歳: 高校 (high_school)
        elif 15 <= child_age < 18:
            return self.stage_costs.get("high_school", 0.0)
        # 18歳〜21歳: 大学 (university) - 浪人や留年は考慮しない基本モデル
        elif 18 <= child_age < 22:
            return self.stage_costs.get("university", 0.0)
        
        # 22歳以降は社会人となり、一般的には教育費は発生しない
        return 0.0
