"""
UI Stylesheet definitions for Dropbox Downloader GUI.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #0a0f1d;
    color: #f1f5f9;
}
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #e2e8f0;
}
QDialog {
    background-color: #0c1322;
    color: #f8fafc;
}
QMessageBox {
    background-color: #0c1322;
    color: #f8fafc;
}
QMessageBox QLabel {
    color: #cbd5e1;
    font-size: 13px;
    background-color: transparent;
}
QMessageBox QPushButton {
    min-width: 82px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 6px;
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
}
QMessageBox QPushButton:hover {
    background-color: #2b3952;
    border-color: #475569;
    color: #ffffff;
}
QMessageBox QPushButton:default {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}
QMessageBox QPushButton:default:hover {
    background-color: #0369a1;
    border-color: #7dd3fc;
}
QInputDialog {
    background-color: #0c1322;
    color: #f8fafc;
}
QInputDialog QLabel {
    color: #cbd5e1;
    font-size: 13px;
    background-color: transparent;
}
QInputDialog QLineEdit {
    background-color: #070c18;
    border: 1px solid #273956;
    border-radius: 7px;
    color: #f8fafc;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #0284c7;
}
QInputDialog QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #0c1424;
}
QInputDialog QPushButton {
    min-width: 80px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 6px;
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
}
QInputDialog QPushButton:hover {
    background-color: #2b3952;
    border-color: #475569;
    color: #ffffff;
}
QInputDialog QPushButton:default {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}
QFrame.header-card, QFrame[class="header-card"] {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
}
QFrame.login-banner, QFrame[class="login-banner"] {
    background-color: #0c182c;
    border: 1px solid #1e3a66;
    border-left: 5px solid #38bdf8;
    border-radius: 10px;
    padding: 12px 16px;
}
QFrame.account-pill, QFrame[class="account-pill"] {
    background-color: #0c1424;
    border: 1px solid #1e2d4a;
    border-radius: 8px;
}
QFrame.card, QFrame[class="card"] {
    background-color: #111a2e;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 14px;
}
QFrame.metric-card, QFrame[class="metric-card"] {
    background-color: #0c1424;
    border: 1px solid #1a263c;
    border-radius: 8px;
    padding: 10px 14px;
}
QLabel.section-title, QLabel[class="section-title"] {
    font-size: 12px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
QLabel.metric-title, QLabel[class="metric-title"] {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel.metric-value, QLabel[class="metric-value"] {
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
}
QLineEdit {
    background-color: #0a101d;
    border: 1px solid #273956;
    border-radius: 7px;
    color: #f8fafc;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #0284c7;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #0c1424;
}
QLineEdit:disabled {
    background-color: #080d18;
    color: #475569;
    border: 1px solid #162032;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 7px;
    color: #e2e8f0;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton:hover {
    background-color: #2b3952;
    border-color: #475569;
    color: #ffffff;
}
QPushButton:checked {
    background-color: #0c4a6e;
    border-color: #0284c7;
    color: #38bdf8;
}
QPushButton:pressed {
    background-color: #162033;
}
QPushButton:disabled {
    background-color: #0d131f;
    color: #475569;
    border-color: #192436;
}
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}
QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #0369a1;
    border-color: #7dd3fc;
}
QPushButton.btn-primary:pressed, QPushButton[class="btn-primary"]:pressed {
    background-color: #075985;
}
QPushButton.btn-primary:disabled, QPushButton[class="btn-primary"]:disabled {
    background-color: #0b1c2e;
    border: 1px solid #162a42;
    color: #3b5270;
}
QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #cbd5e1;
}
QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #2b3952;
    border-color: #475569;
    color: #ffffff;
}
QPushButton.btn-secondary:pressed, QPushButton[class="btn-secondary"]:pressed {
    background-color: #162033;
}
QPushButton.btn-secondary:disabled, QPushButton[class="btn-secondary"]:disabled {
    background-color: #0d131f;
    border: 1px solid #192436;
    color: #475569;
}
QPushButton.btn-start, QPushButton[class="btn-start"] {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton.btn-start:hover, QPushButton[class="btn-start"]:hover {
    background-color: #047857;
    border-color: #34d399;
}
QPushButton.btn-start:pressed, QPushButton[class="btn-start"]:pressed {
    background-color: #065f46;
}
QPushButton.btn-start:disabled, QPushButton[class="btn-start"]:disabled {
    background-color: #072218;
    border: 1px solid #0f3d2c;
    color: #2e5948;
}
QPushButton.btn-stop, QPushButton[class="btn-stop"] {
    background-color: #dc2626;
    border: 1px solid #ef4444;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton.btn-stop:hover, QPushButton[class="btn-stop"]:hover {
    background-color: #b91c1c;
    border-color: #f87171;
}
QPushButton.btn-stop:pressed, QPushButton[class="btn-stop"]:pressed {
    background-color: #991b1b;
}
QPushButton.btn-stop:disabled, QPushButton[class="btn-stop"]:disabled {
    background-color: #220d0f;
    border: 1px solid #3b171c;
    color: #592d33;
}
QPushButton.btn-pause, QPushButton[class="btn-pause"] {
    background-color: #d97706;
    border: 1px solid #f59e0b;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton.btn-pause:hover, QPushButton[class="btn-pause"]:hover {
    background-color: #b45309;
    border-color: #fbbf24;
}
QPushButton.btn-pause:pressed, QPushButton[class="btn-pause"]:pressed {
    background-color: #92400e;
}
QPushButton.btn-pause:disabled, QPushButton[class="btn-pause"]:disabled {
    background-color: #261b0c;
    border: 1px solid #3d2912;
    color: #6e4f2a;
}
QPushButton.btn-resume, QPushButton[class="btn-resume"] {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 8px;
}
QPushButton.btn-resume:hover, QPushButton[class="btn-resume"]:hover {
    background-color: #047857;
    border-color: #34d399;
}
QPushButton.btn-resume:pressed, QPushButton[class="btn-resume"]:pressed {
    background-color: #065f46;
}
QPushButton.recent-chip, QPushButton[class="recent-chip"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 13px;
    padding: 3px 10px;
    font-size: 11px;
    color: #cbd5e1;
    font-weight: 500;
}
QPushButton.recent-chip:hover, QPushButton[class="recent-chip"]:hover {
    background-color: #2b3952;
    border-color: #38bdf8;
    color: #ffffff;
}
QMenu {
    background-color: #0c1322;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px;
    color: #f1f5f9;
}
QMenu::item {
    padding: 8px 18px 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #cbd5e1;
}
QMenu::item:selected {
    background-color: #1e293b;
    color: #38bdf8;
}
QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 6px;
}
QProgressBar {
    background-color: #090e1a;
    border: 1px solid #1a2538;
    border-radius: 5px;
    text-align: center;
    color: #f8fafc;
    font-size: 10px;
    font-weight: 600;
    height: 10px;
}
QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 4px;
}
QProgressBar.overall::chunk, QProgressBar[class="overall"]::chunk {
    background-color: #10b981;
    border-radius: 4px;
}
QTreeWidget {
    background-color: #080d18;
    border: 1px solid #1a2538;
    border-radius: 8px;
    color: #f1f5f9;
    font-size: 12px;
    padding: 4px;
}
QTreeWidget:disabled {
    background-color: #070b14;
    color: #475569;
    border: 1px solid #141c2b;
}
QTreeWidget::item {
    padding: 5px 4px;
    border-radius: 4px;
}
QTreeWidget::item:hover {
    background-color: #141e30;
}
QTreeWidget::item:selected {
    background-color: #163b6b;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0e1628;
    color: #94a3b8;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #1a2538;
    font-size: 11px;
    font-weight: 600;
}
QPlainTextEdit {
    background-color: #060912;
    border: 1px solid #1a2538;
    border-radius: 8px;
    color: #cbd5e1;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
}
QCheckBox {
    color: #cbd5e1;
    font-size: 12px;
    spacing: 7px;
}
QCheckBox:disabled {
    color: #475569;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #0a101d;
}
QCheckBox::indicator:hover {
    border-color: #475569;
}
QCheckBox::indicator:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
}
QCheckBox::indicator:disabled {
    background-color: #080d18;
    border-color: #1a2538;
}
QScrollBar:vertical {
    border: none;
    background-color: #0a0f1d;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #1e293b;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #334155;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

