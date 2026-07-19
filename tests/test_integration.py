import os
import pytest
from ui.viewmodels.main_vm import MainViewModel
from main import setup_sample_project
from core.report_generator import ReportGenerator

def test_integration_sample_scenario():
    # ViewModelの初期化とサンプルデータの読み込み
    vm = MainViewModel()
    setup_sample_project(vm)
    
    # データの注入確認
    assert len(vm.project_data["family_members"]) == 4
    assert len(vm.project_data["housing_plans"]) == 1
    assert len(vm.project_data["investment_accounts"]) == 3
    assert len(vm.project_data["car_plans"]) == 1
    
    # 初期再計算実行
    vm.trigger_recalculation()
    results = vm.sim_results
    
    assert len(results) == 40
    
    # 26年後のライフプラン変更判定（繰上完済と賃貸化による利益75万円の検証）
    # 26年目のシミュレーションデータを確認
    r_26 = results[26]
    # 賃貸収入が 750,000円 計上されているか
    assert r_26["rental_income"] == 750000.0
    # 住宅ローン残高が0になっているか (sale_yearに完済する)
    assert r_26["loan_balance"] == 0.0
    
    # 夫が65歳になって定年したことを確認 (34歳スタートなので31年後)
    # 年収が0になり、代わりに年金受取が計上されているか
    r_31 = results[31]
    assert r_31["husband_age"] == 65
    
    # PDFとExcel出力テスト
    pdf_path = "test_output_report.pdf"
    excel_path = "test_output_report.xlsx"
    
    # 既存のテスト用出力ファイルがあれば事前に削除
    for p in [pdf_path, excel_path]:
        if os.path.exists(p):
            os.remove(p)
            
    try:
        # PDFエクスポート検証
        ReportGenerator.export_to_pdf(pdf_path, results, vm.project_data["metadata"])
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        
        # Excelエクスポート検証
        ReportGenerator.export_to_excel(excel_path, results, vm.project_data["metadata"])
        assert os.path.exists(excel_path)
        assert os.path.getsize(excel_path) > 0
    finally:
        # クリーンアップ
        for p in [pdf_path, excel_path]:
            if os.path.exists(p):
                os.remove(p)
