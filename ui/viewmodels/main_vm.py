from PySide6.QtCore import QObject, Signal, Slot
from typing import Dict, Any, List
import copy
from core.models import FamilyMember
from core.engine import SimulationEngine
from core.project import ProjectManager
from core.database import LifeCanvasDB

class MainViewModel(QObject):
    """
    アプリケーションのメインViewModel。
    状態管理、リアルタイム再計算のトリガー、データ永続化アクションを担当。
    """
    # シミュレーション結果が更新されたことをViewに通知するシグナル
    simulation_updated = Signal(list)
    project_loaded = Signal()

    def __init__(self):
        super().__init__()
        # 初期デフォルトプロジェクトデータ構造
        self._project_data: Dict[str, Any] = {
            "metadata": {
                "name": "新規ライフプラン",
                "initial_cash": 1000000.0,
                "base_living_cost": 2400000.0
            },
            "family_members": [],
            "life_events": [],
            "housing_plans": [],
            "investment_accounts": [],
            "car_plans": [],
            "insurance_plans": [],
            "education_plans": []
        }
        self.db: Optional[LifeCanvasDB] = None
        self._current_filepath: Optional[str] = None
        self._sim_results: List[Dict[str, Any]] = []

    @property
    def project_data(self) -> Dict[str, Any]:
        return self._project_data

    @property
    def sim_results(self) -> List[Dict[str, Any]]:
        return self._sim_results

    def set_project_name(self, name: str):
        self._project_data["metadata"]["name"] = name
        self.trigger_recalculation()

    def set_initial_cash(self, cash: float):
        self._project_data["metadata"]["initial_cash"] = cash
        self.trigger_recalculation()

    def set_base_living_cost(self, cost: float):
        self._project_data["metadata"]["base_living_cost"] = cost
        self.trigger_recalculation()

    @Slot()
    def trigger_recalculation(self):
        """
        最新のパラメータで再計算を実行し、Viewへ結果をシグナル通知します。
        """
        # 計算エンジンに渡すためのプロジェクトデータをディープコピー
        # （計算によるメンバ状態の不要な汚染を防ぐため）
        data_copy = copy.deepcopy(self._project_data)
        
        # 将来生まれる子供などの FamilyMember リストを補正
        # （教育プランがある場合、その子供がfamily_membersに含まれているか確認・同期）
        engine = SimulationEngine(data_copy)
        self._sim_results = engine.run()
        self.simulation_updated.emit(self._sim_results)

    # --- プロジェクトファイル操作 ---

    def new_project(self):
        """新規プロジェクトの立ち上げ"""
        self._project_data = {
            "metadata": {
                "name": "新規ライフプラン",
                "initial_cash": 1000000.0,
                "base_living_cost": 2400000.0
            },
            "family_members": [],
            "life_events": [],
            "housing_plans": [],
            "investment_accounts": [],
            "car_plans": [],
            "insurance_plans": [],
            "education_plans": []
        }
        self._current_filepath = None
        self.trigger_recalculation()
        self.project_loaded.emit()

    def load_from_json(self, filepath: str):
        """JSONプロジェクトファイルを読み込みます"""
        try:
            self._project_data = ProjectManager.load_from_json(filepath)
            self._current_filepath = filepath
            self.trigger_recalculation()
            self.project_loaded.emit()
        except Exception as e:
            print(f"JSON読み込みエラー: {e}")
            raise e

    def save_to_json(self, filepath: str):
        """JSONプロジェクトファイルとして保存します"""
        try:
            ProjectManager.save_to_json(filepath, self._project_data)
            self._current_filepath = filepath
        except Exception as e:
            print(f"JSON書き込みエラー: {e}")
            raise e

    def load_from_sqlite(self, db_path: str):
        """SQLiteデータベースからデータを読み込みます"""
        db = LifeCanvasDB(db_path)
        try:
            self._project_data = db.load_project()
            self._current_filepath = db_path
            self.trigger_recalculation()
            self.project_loaded.emit()
        finally:
            db.close()

    def save_to_sqlite(self, db_path: str):
        """SQLiteデータベースにデータを保存します"""
        db = LifeCanvasDB(db_path)
        try:
            db.save_project(self._project_data)
            self._current_filepath = db_path
        finally:
            db.close()
