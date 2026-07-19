from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FamilyMember:
    """家族の個人データモデル"""
    name: str                           # 名前（例: '夫', '妻', '長男'）
    relation: str                       # 続柄（'husband', 'wife', 'child', 'other'）
    age: int                            # 開始時点の年齢
    annual_income: float = 0.0          # 基本年収（現在の額面）
    bonus: float = 0.0                  # ボーナス
    retirement_age: int = 65            # 定年年齢
    pension_start_age: int = 65         # 年金受給開始年齢
    birth_year_offset: int = 0          # シミュレーション開始から何年後に生まれるか（子供などの将来の誕生用）
    current_occupation: str = "会社員"  # 就業状況（'会社員', 'パート', '専業主婦', '無職' など）
    salary_growth_rate: float = 0.0     # 昇給率（% / 年）

    # 妻の就業ワークフローなどの動的年収変動用
    income_modifiers: dict = field(default_factory=dict)
    # 例: { 'before_birth': 3500000, 'childcare_leave_continuous': True, 'nursery': 576000, ... }

    def get_income_for_simulation_year(self, elapsed_years: int, current_family_state: dict) -> float:
        """
        指定された経過年数および家族全体の状況（子供の進学ステージなど）を考慮し、
        その年の年収を計算して返します。
        """
        # 将来生まれる子供で、まだ生まれていない場合
        if self.relation == "child" and elapsed_years < self.birth_year_offset:
            return 0.0

        current_age = self.age + elapsed_years

        # 定年退職後の場合
        if current_age >= self.retirement_age:
            # シミュレーションエンジンが年金を補完する
            return 0.0

        # 動的な年収モディファイア（年齢ベースなど）
        # 例: 60代前半再雇用ルール "age_60_64": 2200000
        if 60 <= current_age < 65 and "age_60_64" in self.income_modifiers:
            return float(self.income_modifiers["age_60_64"])

        # サンプル要件: 妻の就業ワークフロー
        if self.relation == "wife":
            # 妻の60歳定年退職（強制的に年収0円）
            if current_age >= 60:
                return 0.0
                
        if self.relation == "wife" and self.income_modifiers:
            # 家族内に子供がいるか、それぞれの年齢・就学ステージを判定
            children = current_family_state.get("children", [])
            
            # 子供たちの修学状況に基づく年収変更
            if children:
                # 簡易判定：一番下の子供の年齢や状態を基準にするなどのロジック
                # ここでは子供たちの就学状況からモディファイアを決定
                youngest_child_age = -1
                for child in children:
                    child_age = child.age + elapsed_years - child.birth_year_offset
                    if child_age >= 0:
                        if youngest_child_age == -1 or child_age < youngest_child_age:
                            youngest_child_age = child_age

                # 子供の年齢に基づく年収評価
                # wife_workflow:
                #   before_birth: 3500000
                #   childcare_leave: continuous (育休)
                #   nursery (保育園): 576000
                #   elementary (小学校): 960000
                #   junior_high (中学校): 1152000
                
                # まだ誰も生まれていない、あるいは出生前
                all_unborn = all(elapsed_years < c.birth_year_offset for c in children)
                
                if all_unborn:
                    return self.income_modifiers.get("before_birth", self.annual_income)
                
                # 育児休業期間 (0歳時など。サンプルでは continuous)
                # 一番直近の子供が生後0歳（誕生年）の場合
                has_bebe = any(elapsed_years == c.birth_year_offset for c in children)
                if has_bebe:
                    # 育休中（年収は0、手当金は別途給付金として計算される）
                    return 0.0
                
                # 就学段階に応じた年収
                # 保育園/幼稚園 (1歳〜5歳)
                if 1 <= youngest_child_age <= 5:
                    return self.income_modifiers.get("nursery", 600000.0)
                # 小学校 (6歳〜11歳)
                elif 6 <= youngest_child_age <= 11:
                    return self.income_modifiers.get("elementary", 1200000.0)
                # 中学校 (12歳〜14歳)
                elif 12 <= youngest_child_age <= 14:
                    return self.income_modifiers.get("junior_high", 2200000.0)
                # 高校生以降 (15歳〜)
                else:
                    return self.income_modifiers.get("high_school", 2200000.0)

        # 基本的な昇給率込みの年収計算
        # 年収 = (基本年収 + ボーナス) * (1 + 昇給率)^経過年数
        base = self.annual_income + self.bonus
        growth = (1.0 + self.salary_growth_rate / 100.0) ** elapsed_years
        return base * growth


@dataclass
class Family:
    """世帯データモデル"""
    members: List[FamilyMember] = field(default_factory=list)

    @property
    def husband(self) -> Optional[FamilyMember]:
        for m in self.members:
            if m.relation == "husband":
                return m
        return None

    @property
    def wife(self) -> Optional[FamilyMember]:
        for m in self.members:
            if m.relation == "wife":
                return m
        return None

    @property
    def children(self) -> List[FamilyMember]:
        return [m for m in self.members if m.relation == "child"]

    def add_member(self, member: FamilyMember):
        self.members.append(member)
