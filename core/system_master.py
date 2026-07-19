import json
import os
from typing import Dict, Any

class SystemMaster:
    """
    税制・社会保障・投資制度などの「国・年代のルール（制度）」を一元管理するマスタ。
    これにより、将来の法改正（NISA枠の拡大など）に単なる設定変更で対応できるようにする。
    """
    _instance = None
    
    # 2026年時点のデフォルト制度設定
    _DEFAULT_CONFIG = {
        "nisa": {
            "lifetime_limit": 18000000,
            "annual_limit": 3600000,
            "growth_limit": 12000000
        },
        "ideco": {
            "annual_limit_employee": 276000,
            "annual_limit_freelance": 816000
        },
        "child_allowance": {
            # 児童手当 (月額) - 第3子倍増などの複雑化もあるがベースライン
            "under_3": 15000,
            "under_primary": 10000,
            "junior_and_high": 10000
        },
        "housing_loan_deduction": {
            "rate": 0.007,
            "max_balance_new": 20000000, # 新築等(一般住宅などで2000万, 認定住宅ならもっと高いが基本2000万とする)
            "max_balance_used": 20000000 # 中古等
        },
        "tax": {
            "consumption_tax_rate": 0.10,
            # 将来的な所得税・社会保険料率の基準値などを追加予定
        }
    }

    def __init__(self):
        self.config: Dict[str, Any] = self._DEFAULT_CONFIG.copy()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SystemMaster()
        return cls._instance

    def load_custom_config(self, filepath: str):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                custom_conf = json.load(f)
                # 単純マージ (本来は深いマージが望ましい)
                self.config.update(custom_conf)

    def get_nisa_limit(self) -> float:
        return self.config["nisa"]["lifetime_limit"]

    def get_child_allowance_monthly(self, age: int, is_third_child_or_more: bool = False) -> float:
        # ごく簡易的な児童手当算出（将来的により詳細化）
        if age < 3:
            return self.config["child_allowance"]["under_3"]
        elif 3 <= age <= 12:
            return self.config["child_allowance"]["under_primary"]
        elif 13 <= age <= 18:
            return self.config["child_allowance"]["junior_and_high"]
        return 0.0

    def get_housing_loan_deduction_limit(self, house_type: str = "new") -> float:
        """指定された住宅タイプの最大控除額(年額)を算出する"""
        rate = self.config["housing_loan_deduction"]["rate"]
        balance = self.config["housing_loan_deduction"]["max_balance_new"] if house_type == "new" else self.config["housing_loan_deduction"]["max_balance_used"]
        return balance * rate
