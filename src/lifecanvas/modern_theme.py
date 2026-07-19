MODERN_STYLESHEET = r"""
QMainWindow {
    background: #f4f7fb;
    color: #152033;
}
QWidget {
    font-family: "Yu Gothic UI", "Yu Gothic", "Meiryo";
    font-size: 13px;
}
QLabel#appTitle {
    font-size: 30px;
    font-weight: 800;
    color: #12213a;
}
QLabel#appSubtitle, QLabel#sectionNote {
    color: #66758d;
}
QLabel#statusFresh {
    color: #147d64;
    background: #e6f7f1;
    border-radius: 12px;
    padding: 5px 10px;
    font-weight: 700;
}
QLabel#statusDirty {
    color: #9a5b00;
    background: #fff3d8;
    border-radius: 12px;
    padding: 5px 10px;
    font-weight: 700;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #e0e7f0;
    border-radius: 14px;
    margin-top: 18px;
    padding: 16px;
    font-size: 14px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: #263957;
}
QPushButton {
    min-height: 34px;
    padding: 7px 15px;
    border: 1px solid #d6deea;
    border-radius: 9px;
    background: #ffffff;
    color: #233550;
    font-weight: 700;
}
QPushButton:hover {
    background: #f1f5fb;
    border-color: #aebbd0;
}
QPushButton#primaryButton {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
}
QPushButton#pdfButton {
    background: #14213d;
    color: #ffffff;
    border-color: #14213d;
}
QLineEdit, QComboBox, QTextEdit {
    background: #ffffff;
    border: 1px solid #ced8e6;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #bfdbfe;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 2px solid #3b82f6;
    padding: 6px 8px;
}
QTabWidget::pane {
    border: 0;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #65748a;
    padding: 11px 20px;
    margin-right: 4px;
    border-radius: 9px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #1d4ed8;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #e0e7f0;
    border-radius: 10px;
    gridline-color: #edf1f6;
}
QHeaderView::section {
    background: #eef3f9;
    color: #40516b;
    border: 0;
    border-right: 1px solid #dde5ef;
    padding: 8px;
    font-weight: 700;
}
QScrollArea {
    border: 0;
    background: transparent;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #e0e7f0;
    border-radius: 10px;
    padding: 4px;
}
"""
