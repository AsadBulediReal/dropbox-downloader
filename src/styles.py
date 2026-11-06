"""
UI Stylesheet definitions for Dropbox Downloader GUI (Clean Light & Minimal Dark Themes).
"""

LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #f8fafc;
    color: #0f172a;
}
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #0f172a;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QDialog {
    background-color: #ffffff;
    color: #0f172a;
}
QMessageBox {
    background-color: #ffffff;
    color: #0f172a;
}
QMessageBox QLabel {
    color: #334155;
    font-size: 13px;
    background-color: transparent;
}
QFrame.header-card, QFrame[class="header-card"] {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    border-top: none;
    border-left: none;
    border-right: none;
    border-radius: 0px;
}
QFrame.wizard-pill-bar, QFrame[class="wizard-pill-bar"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 17px;
}
QPushButton.wizard-step-btn, QPushButton[class="wizard-step-btn"] {
    background-color: transparent;
    border: none;
    border-radius: 14px;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
}
QPushButton.wizard-step-btn:hover, QPushButton[class="wizard-step-btn"]:hover {
    color: #0f172a;
    background-color: #e2e8f0;
}
QPushButton.wizard-step-btn-active, QPushButton[class="wizard-step-btn-active"] {
    background-color: #0061ff;
    border: none;
    border-radius: 14px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 16px;
}
QPushButton.wizard-step-btn-active:hover, QPushButton[class="wizard-step-btn-active"]:hover {
    background-color: #0052d9;
    color: #ffffff;
}
QPushButton.btn-settings, QPushButton[class="btn-settings"] {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton.btn-settings:hover, QPushButton[class="btn-settings"]:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}
QFrame.login-banner, QFrame[class="login-banner"] {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 5px solid #0061ff;
    border-radius: 12px;
    padding: 12px 16px;
}
QFrame.account-pill, QFrame[class="account-pill"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame.url-command-card, QFrame[class="url-command-card"] {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 16px;
}
QFrame.card, QFrame[class="card"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
}
QFrame.subtle-card, QFrame[class="subtle-card"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame.stat-card, QFrame[class="stat-card"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
}
QFrame.metric-card, QFrame[class="metric-card"] {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
}
QFrame.settings-drawer, QFrame[class="settings-drawer"] {
    background-color: #ffffff;
    border-left: 1px solid #cbd5e1;
}
QLabel.hero-title, QLabel[class="hero-title"] {
    font-size: 23px;
    font-weight: 700;
    color: #0f172a;
    background-color: transparent;
}
QLabel.hero-subtitle, QLabel[class="hero-subtitle"] {
    font-size: 13px;
    color: #64748b;
    background-color: transparent;
}
QLabel.section-title, QLabel[class="section-title"] {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    background-color: transparent;
}
QLabel.metric-title, QLabel[class="metric-title"] {
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    background-color: transparent;
}
QLabel.metric-value, QLabel[class="metric-value"] {
    font-size: 19px;
    font-weight: 700;
    color: #0f172a;
    background-color: transparent;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    color: #0f172a;
    padding: 9px 12px;
    font-size: 13px;
    selection-background-color: #0061ff;
    selection-color: #ffffff;
}
QLineEdit.command-input, QLineEdit[class="command-input"] {
    background-color: transparent;
    border: none;
    color: #0f172a;
    padding: 8px 10px;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid #0061ff;
}
QLineEdit.command-input:focus, QLineEdit[class="command-input"]:focus {
    border: none;
}
QLineEdit:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}
QLineEdit.command-input:disabled, QLineEdit[class="command-input"]:disabled {
    background-color: transparent;
    border: none;
    color: #94a3b8;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background-color: #e2e8f0;
}
QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    color: #ffffff;
    border-radius: 10px;
}
QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #0052d9;
    border-color: #0052d9;
}
QPushButton.btn-primary:pressed, QPushButton[class="btn-primary"]:pressed {
    background-color: #0043b3;
}
QPushButton.btn-primary:disabled, QPushButton[class="btn-primary"]:disabled {
    background-color: #dbeafe;
    border: 1px solid #bfdbfe;
    color: #93c5fd;
}
QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #334155;
    border-radius: 10px;
}
QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}
QPushButton.btn-start, QPushButton[class="btn-start"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 11px;
}
QPushButton.btn-start:hover, QPushButton[class="btn-start"]:hover {
    background-color: #0052d9;
    border-color: #0052d9;
}
QPushButton.btn-start:disabled, QPushButton[class="btn-start"]:disabled {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    color: #94a3b8;
}
QPushButton.btn-stop, QPushButton[class="btn-stop"] {
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    color: #dc2626;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-stop:hover, QPushButton[class="btn-stop"]:hover {
    background-color: #dc2626;
    border-color: #dc2626;
    color: #ffffff;
}
QPushButton.btn-pause, QPushButton[class="btn-pause"] {
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    color: #b45309;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-pause:hover, QPushButton[class="btn-pause"]:hover {
    background-color: #fef3c7;
    border-color: #f59e0b;
}
QPushButton.btn-resume, QPushButton[class="btn-resume"] {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-resume:hover, QPushButton[class="btn-resume"]:hover {
    background-color: #047857;
}
QPushButton.qtab-btn, QPushButton[class="qtab-btn"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton.qtab-btn:hover, QPushButton[class="qtab-btn"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}
QPushButton.qtab-btn-active, QPushButton[class="qtab-btn-active"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    border-radius: 10px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
}
QPushButton.recent-chip, QPushButton[class="recent-chip"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    color: #334155;
    font-weight: 600;
}
QPushButton.recent-chip:hover, QPushButton[class="recent-chip"]:hover {
    background-color: #eff6ff;
    border-color: #93c5fd;
    color: #0061ff;
}
QPushButton.recent-row-btn, QPushButton[class="recent-row-btn"] {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 12px;
    text-align: left;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
}
QPushButton.recent-row-btn:hover, QPushButton[class="recent-row-btn"]:hover {
    background-color: #eff6ff;
    border-color: #93c5fd;
    color: #0061ff;
}
QFrame.ad-banner, QFrame[class="ad-banner"] {
    background-color: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 12px;
}
QLabel.ad-badge, QLabel[class="ad-badge"] {
    background-color: #dbeafe;
    color: #1d4ed8;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel.ad-text, QLabel[class="ad-text"] {
    color: #1e293b;
    font-size: 12px;
    background-color: transparent;
}
QPushButton.ad-cta, QPushButton[class="ad-cta"] {
    background-color: transparent;
    border: none;
    color: #0061ff;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 8px;
}
QPushButton.ad-cta:hover, QPushButton[class="ad-cta"]:hover {
    color: #0043b3;
    text-decoration: underline;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px;
    color: #0f172a;
}
QMenu::item {
    padding: 8px 18px 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #334155;
}
QMenu::item:selected {
    background-color: #eff6ff;
    color: #0061ff;
}
QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 6px;
}
QProgressBar {
    background-color: #f1f5f9;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: transparent;
    font-size: 10px;
    height: 9px;
}
QProgressBar::chunk {
    background-color: #0ea5e9;
    border-radius: 5px;
}
QProgressBar.overall::chunk, QProgressBar[class="overall"]::chunk {
    background-color: #10b981;
    border-radius: 5px;
}
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #0f172a;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background-color: #f1f5f9;
}
QTreeWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-size: 11px;
    font-weight: 700;
}
QPlainTextEdit {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    color: #334155;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
}
QCheckBox {
    color: #334155;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox:disabled {
    color: #94a3b8;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #0061ff;
    border-color: #0061ff;
}
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


DARK_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
    color: #f8fafc;
}
QWidget {
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #f8fafc;
}
QScrollArea {
    background-color: transparent;
    border: none;
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
QFrame.header-card, QFrame[class="header-card"] {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
    border-top: none;
    border-left: none;
    border-right: none;
    border-radius: 0px;
}
QFrame.wizard-pill-bar, QFrame[class="wizard-pill-bar"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 17px;
}
QPushButton.wizard-step-btn, QPushButton[class="wizard-step-btn"] {
    background-color: transparent;
    border: none;
    border-radius: 14px;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
}
QPushButton.wizard-step-btn:hover, QPushButton[class="wizard-step-btn"]:hover {
    color: #f8fafc;
    background-color: #1e293b;
}
QPushButton.wizard-step-btn-active, QPushButton[class="wizard-step-btn-active"] {
    background-color: #0ea5e9;
    border: none;
    border-radius: 14px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 16px;
}
QPushButton.wizard-step-btn-active:hover, QPushButton[class="wizard-step-btn-active"]:hover {
    background-color: #0284c7;
    color: #ffffff;
}
QPushButton.btn-settings, QPushButton[class="btn-settings"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton.btn-settings:hover, QPushButton[class="btn-settings"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QFrame.login-banner, QFrame[class="login-banner"] {
    background-color: #0c182c;
    border: 1px solid #1e3a66;
    border-left: 5px solid #38bdf8;
    border-radius: 12px;
    padding: 12px 16px;
}
QFrame.account-pill, QFrame[class="account-pill"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 10px;
}
QFrame.url-command-card, QFrame[class="url-command-card"] {
    background-color: #1e293b;
    border: 1.5px solid #334155;
    border-radius: 16px;
}
QFrame.card, QFrame[class="card"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
}
QFrame.subtle-card, QFrame[class="subtle-card"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QFrame.stat-card, QFrame[class="stat-card"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
}
QFrame.metric-card, QFrame[class="metric-card"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 10px 14px;
}
QFrame.settings-drawer, QFrame[class="settings-drawer"] {
    background-color: #0f172a;
    border-left: 1px solid #334155;
}
QLabel.hero-title, QLabel[class="hero-title"] {
    font-size: 23px;
    font-weight: 700;
    color: #f8fafc;
    background-color: transparent;
}
QLabel.hero-subtitle, QLabel[class="hero-subtitle"] {
    font-size: 13px;
    color: #94a3b8;
    background-color: transparent;
}
QLabel.section-title, QLabel[class="section-title"] {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    background-color: transparent;
}
QLabel.metric-title, QLabel[class="metric-title"] {
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    background-color: transparent;
}
QLabel.metric-value, QLabel[class="metric-value"] {
    font-size: 19px;
    font-weight: 700;
    color: #f8fafc;
    background-color: transparent;
}
QLineEdit {
    background-color: #0b1120;
    border: 1px solid #334155;
    border-radius: 10px;
    color: #f8fafc;
    padding: 9px 12px;
    font-size: 13px;
    selection-background-color: #0284c7;
}
QLineEdit.command-input, QLineEdit[class="command-input"] {
    background-color: transparent;
    border: none;
    color: #f8fafc;
    padding: 8px 10px;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QLineEdit.command-input:focus, QLineEdit[class="command-input"]:focus {
    border: none;
}
QLineEdit:disabled {
    background-color: #080d18;
    color: #475569;
    border: 1px solid #1e293b;
}
QLineEdit.command-input:disabled, QLineEdit[class="command-input"]:disabled {
    background-color: transparent;
    border: none;
    color: #475569;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
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
QPushButton:pressed {
    background-color: #162033;
}
QPushButton:disabled {
    background-color: #0d131f;
    color: #475569;
    border-color: #192436;
}
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    color: #ffffff;
    border-radius: 10px;
}
QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #0284c7;
    border-color: #7dd3fc;
}
QPushButton.btn-primary:pressed, QPushButton[class="btn-primary"]:pressed {
    background-color: #0369a1;
}
QPushButton.btn-primary:disabled, QPushButton[class="btn-primary"]:disabled {
    background-color: #0b1c2e;
    border: 1px solid #162a42;
    color: #3b5270;
}
QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #0b1120;
    border: 1px solid #334155;
    color: #cbd5e1;
    border-radius: 10px;
}
QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #1e293b;
    border-color: #475569;
    color: #ffffff;
}
QPushButton.btn-start, QPushButton[class="btn-start"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 11px;
}
QPushButton.btn-start:hover, QPushButton[class="btn-start"]:hover {
    background-color: #0284c7;
    border-color: #7dd3fc;
}
QPushButton.btn-start:disabled, QPushButton[class="btn-start"]:disabled {
    background-color: #0d131f;
    border: 1px solid #1e293b;
    color: #475569;
}
QPushButton.btn-stop, QPushButton[class="btn-stop"] {
    background-color: #2d1215;
    border: 1px solid #7f1d1d;
    color: #f87171;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-stop:hover, QPushButton[class="btn-stop"]:hover {
    background-color: #dc2626;
    border-color: #ef4444;
    color: #ffffff;
}
QPushButton.btn-pause, QPushButton[class="btn-pause"] {
    background-color: #2e1d09;
    border: 1px solid #78350f;
    color: #fbbf24;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-pause:hover, QPushButton[class="btn-pause"]:hover {
    background-color: #d97706;
    border-color: #f59e0b;
    color: #ffffff;
}
QPushButton.btn-resume, QPushButton[class="btn-resume"] {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-resume:hover, QPushButton[class="btn-resume"]:hover {
    background-color: #047857;
}
QPushButton.qtab-btn, QPushButton[class="qtab-btn"] {
    background-color: #0b1120;
    border: 1px solid #334155;
    border-radius: 10px;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton.qtab-btn:hover, QPushButton[class="qtab-btn"]:hover {
    background-color: #1e293b;
    color: #f8fafc;
}
QPushButton.qtab-btn-active, QPushButton[class="qtab-btn-active"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    border-radius: 10px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
}
QPushButton.recent-chip, QPushButton[class="recent-chip"] {
    background-color: #0b1120;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    color: #cbd5e1;
    font-weight: 600;
}
QPushButton.recent-chip:hover, QPushButton[class="recent-chip"]:hover {
    background-color: #1e293b;
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton.recent-row-btn, QPushButton[class="recent-row-btn"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 8px 12px;
    text-align: left;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
}
QPushButton.recent-row-btn:hover, QPushButton[class="recent-row-btn"]:hover {
    background-color: #172554;
    border-color: #3b82f6;
    color: #38bdf8;
}
QFrame.ad-banner, QFrame[class="ad-banner"] {
    background-color: #172554;
    border: 1px solid #3b82f6;
    border-radius: 12px;
}
QLabel.ad-badge, QLabel[class="ad-badge"] {
    background-color: #1e3a8a;
    color: #93c5fd;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel.ad-text, QLabel[class="ad-text"] {
    color: #f1f5f9;
    font-size: 12px;
    background-color: transparent;
}
QPushButton.ad-cta, QPushButton[class="ad-cta"] {
    background-color: transparent;
    border: none;
    color: #60a5fa;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 8px;
}
QPushButton.ad-cta:hover, QPushButton[class="ad-cta"]:hover {
    color: #93c5fd;
    text-decoration: underline;
}
QMenu {
    background-color: #0c1322;
    border: 1px solid #334155;
    border-radius: 10px;
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
    background-color: #0b1120;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: transparent;
    font-size: 10px;
    height: 9px;
}
QProgressBar::chunk {
    background-color: #0ea5e9;
    border-radius: 5px;
}
QProgressBar.overall::chunk, QProgressBar[class="overall"]::chunk {
    background-color: #10b981;
    border-radius: 5px;
}
QTreeWidget {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 12px;
    color: #f1f5f9;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget:disabled {
    background-color: #080d18;
    color: #475569;
    border: 1px solid #141c2b;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background-color: #141e30;
}
QTreeWidget::item:selected {
    background-color: #163b6b;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-size: 11px;
    font-weight: 700;
}
QPlainTextEdit {
    background-color: #060912;
    border: 1px solid #1e293b;
    border-radius: 10px;
    color: #cbd5e1;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
}
QCheckBox {
    color: #cbd5e1;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox:disabled {
    color: #475569;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #0b1120;
}
QCheckBox::indicator:checked {
    background-color: #0ea5e9;
    border-color: #38bdf8;
}
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def get_theme_stylesheet(theme: str = "light") -> str:
    """Return the Qt stylesheet for 'light' or 'dark' theme mode."""
    return DARK_STYLESHEET if str(theme).strip().lower() == "dark" else LIGHT_STYLESHEET
