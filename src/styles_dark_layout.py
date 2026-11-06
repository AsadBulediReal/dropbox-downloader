DARK_LAYOUT_QSS = """
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
QWidget#workspaceContainer, QWidget#drawerScrollContent, QStackedWidget {
    background-color: transparent;
}
QLabel.brand-icon, QLabel[class="brand-icon"] {
    background-color: #0ea5e9;
    color: #ffffff;
    border-radius: 10px;
    font-size: 16px;
    font-weight: bold;
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
    border-radius: 19px;
}
QPushButton.wizard-step-btn, QPushButton[class="wizard-step-btn"] {
    background-color: transparent;
    border: none;
    border-radius: 15px;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton.wizard-step-btn:hover, QPushButton[class="wizard-step-btn"]:hover {
    color: #f8fafc;
    background-color: #1e293b;
}
QPushButton.wizard-step-btn-active, QPushButton[class="wizard-step-btn-active"] {
    background-color: #0ea5e9;
    border: none;
    border-radius: 15px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 7px 18px;
}
QPushButton.wizard-step-btn-active:hover, QPushButton[class="wizard-step-btn-active"]:hover {
    background-color: #0284c7;
    color: #ffffff;
}
QPushButton.btn-settings, QPushButton[class="btn-settings"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    color: #f8fafc;
    font-size: 18px;
    padding: 0px;
}
QPushButton.btn-settings:hover, QPushButton[class="btn-settings"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QFrame.login-banner, QFrame[class="login-banner"] {
    background-color: #0c182c;
    border: 1px solid #1e3a66;
    border-radius: 14px;
}
QLabel.login-banner-icon, QLabel[class="login-banner-icon"] {
    background-color: #172554;
    border-radius: 10px;
    font-size: 18px;
}
QFrame.account-pill, QFrame[class="account-pill"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 10px;
}
QFrame.url-command-card, QFrame[class="url-command-card"] {
    background-color: #1e293b;
    border: 1px solid #334155;
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
QLineEdit.drawer-subtle-input, QLineEdit[class="drawer-subtle-input"] {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #f8fafc;
    padding: 7px 12px;
    font-size: 12px;
}
QLineEdit.drawer-subtle-input:focus, QLineEdit[class="drawer-subtle-input"]:focus {
    border: 1px solid #38bdf8;
}
QLineEdit.drawer-subtle-input:disabled, QLineEdit[class="drawer-subtle-input"]:disabled {
    background-color: #080d18;
    color: #475569;
    border: 1px solid #1e293b;
}
QPushButton.drawer-card-btn, QPushButton[class="drawer-card-btn"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
}
QPushButton.drawer-card-btn:hover, QPushButton[class="drawer-card-btn"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QPushButton.drawer-card-btn:disabled, QPushButton[class="drawer-card-btn"]:disabled {
    background-color: #0d131f;
    color: #475569;
    border-color: #192436;
}
QPushButton.drawer-close-btn, QPushButton[class="drawer-close-btn"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
}
QPushButton.drawer-close-btn:hover, QPushButton[class="drawer-close-btn"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QPushButton.drawer-acct-btn, QPushButton[class="drawer-acct-btn"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 10px;
}
QPushButton.drawer-acct-btn:hover, QPushButton[class="drawer-acct-btn"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QPushButton.drawer-signout-btn, QPushButton[class="drawer-signout-btn"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f87171;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 10px;
}
QPushButton.drawer-signout-btn:hover, QPushButton[class="drawer-signout-btn"]:hover {
    background-color: #2d1215;
    border-color: #7f1d1d;
    color: #fca5a5;
}
QPushButton.drawer-theme-btn, QPushButton[class="drawer-theme-btn"] {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 12px;
    text-align: left;
}
QPushButton.drawer-theme-btn:hover, QPushButton[class="drawer-theme-btn"]:hover {
    background-color: #2b3952;
    border-color: #475569;
}
QPushButton.drawer-log-link, QPushButton[class="drawer-log-link"] {
    background-color: transparent;
    border: none;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
    padding: 2px 4px;
}
QPushButton.drawer-log-link:hover, QPushButton[class="drawer-log-link"]:hover {
    color: #f8fafc;
    text-decoration: underline;
}
QPushButton.drawer-save-btn, QPushButton[class="drawer-save-btn"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    border-radius: 8px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton.drawer-save-btn:hover, QPushButton[class="drawer-save-btn"]:hover {
    background-color: #0284c7;
    border-color: #7dd3fc;
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
"""

