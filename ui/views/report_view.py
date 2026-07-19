from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, Slot
from core.report_generator import ReportGenerator

class ReportView(QWidget):
    """
    レポート出力用の View 画面。
    PDFエクスポート、Excelエクスポートボタンを配置し、保存ダイアログへ仲介します。
    """
    def __init__(self, main_vm, parent=None):
        super().__init__(parent)
        self.vm = main_vm
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("📄 レポート出力", self)
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        info_label = QLabel(
            "シミュレーションで算出した将来設計のキャッシュフローテーブルと診断データを\n"
            "PDFフォーマット、もしくはExcelシートとしてエクスポートします。"
        )
        info_label.setStyleSheet("color: #6b6b6b; line-height: 1.5; margin-bottom: 20px;")
        layout.addWidget(info_label)

        # 出力ボタンエリア
        card = QFrame(self)
        card.setStyleSheet("background-color: #fafafa; border: 1px solid #e9e9e7; border-radius: 6px; padding: 25px;")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        btn_pdf = QPushButton("📕 PDF フォーマットで出力", self)
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setMinimumHeight(45)
        btn_pdf.clicked.connect(self._export_pdf)
        card_layout.addWidget(btn_pdf)

        btn_excel = QPushButton("📗 Excel シートで出力", self)
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.setMinimumHeight(45)
        btn_excel.setObjectName("SecondaryButton")
        btn_excel.clicked.connect(self._export_excel)
        card_layout.addWidget(btn_excel)

        layout.addWidget(card)
        layout.addStretch()

    def _export_pdf(self):
        results = self.vm.sim_results
        if not results:
            QMessageBox.warning(self, "警告", "シミュレーション結果が空なため、レポートを作成できません。")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "PDFとして保存", "", "PDF Files (*.pdf)")
        if filepath:
            try:
                ReportGenerator.export_to_pdf(filepath, results, self.vm.project_data.get("metadata", {}))
                QMessageBox.information(self, "成功", "PDFレポートのエクスポートに成功しました！")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"PDF出力に失敗しました:\n{e}")

    def _export_excel(self):
        results = self.vm.sim_results
        if not results:
            QMessageBox.warning(self, "警告", "シミュレーション結果が空なため、レポートを作成できません。")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Excelとして保存", "", "Excel Files (*.xlsx)")
        if filepath:
            try:
                ReportGenerator.export_to_excel(filepath, results, self.vm.project_data.get("metadata", {}))
                QMessageBox.information(self, "成功", "Excelレポートのエクスポートに成功しました！")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"Excel出力に失敗しました:\n{e}")
