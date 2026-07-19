# Notion / Office風のクリーンでモダンな配色テーマ・QSSスタイルシート定義

NOTION_STYLE = """
/* 全体基本設定 */
QWidget {
    font-family: "Segoe UI", "Malgun Gothic", "Meiryo", sans-serif;
    font-size: 13px;
    color: #37352f;
    background-color: #ffffff;
}

/* メインフレーム / 背景 */
QMainWindow {
    background-color: #f7f6f3;
}

/* 左側サイドバー */
QFrame#SidebarFrame {
    background-color: #f7f6f3;
    border-right: 1px solid #e9e9e7;
}

/* サイドバー内のボタン */
QPushButton#SidebarButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 8px 12px;
    text-align: left;
    font-weight: 500;
    color: #4a4a46;
}

QPushButton#SidebarButton:hover {
    background-color: #efeee9;
    color: #080808;
}

QPushButton#SidebarButton:checked {
    background-color: #eceae2;
    color: #0f0f0f;
    font-weight: bold;
}

/* メインコンテンツ領域 */
QFrame#ContentFrame {
    background-color: #ffffff;
    border-top-left-radius: 8px;
    border-bottom-left-radius: 8px;
    border: 1px solid #edece9;
}

/* 各種カード表示 */
QFrame#SummaryCard {
    background-color: #ffffff;
    border: 1px solid #e9e9e7;
    border-radius: 6px;
    padding: 12px;
}

QLabel#CardTitle {
    font-size: 11px;
    color: #6b6b6b;
    font-weight: bold;
    text-transform: uppercase;
}

QLabel#CardValue {
    font-size: 20px;
    font-weight: bold;
    color: #1a1a1a;
}

/* 入力エリア */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #fafafa;
    border: 1px solid #e0dfdb;
    border-radius: 4px;
    padding: 6px 10px;
    color: #37352f;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    background-color: #ffffff;
    border: 1.5px solid #2383e2;
}

/* スクロールエリア */
QScrollArea {
    border: none;
    background-color: #ffffff;
}

/* ヘッダーやセクションタイトル */
QLabel#SectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #37352f;
    margin-bottom: 8px;
}

/* 標準押しボタン */
QPushButton {
    background-color: #2383e2;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1a6cb4;
}

QPushButton:pressed {
    background-color: #12548c;
}

/* セカンダリ（白色）ボタン */
QPushButton#SecondaryButton {
    background-color: #ffffff;
    color: #37352f;
    border: 1px solid #e0dfdb;
    border-radius: 4px;
    padding: 6px 12px;
}

QPushButton#SecondaryButton:hover {
    background-color: #f7f6f3;
}

/* テーブルスタイル */
QTableWidget {
    border: 1px solid #e9e9e7;
    gridline-color: #eceae2;
    background-color: #ffffff;
    alternate-background-color: #fafafa;
}

QHeaderView::section {
    background-color: #f7f6f3;
    color: #6b6b6b;
    padding: 6px;
    border: 1px solid #e9e9e7;
    font-weight: bold;
}
"""
