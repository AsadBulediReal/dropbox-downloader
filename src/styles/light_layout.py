LIGHT_LAYOUT_QSS = """
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
QWidget#workspaceContainer, QWidget#drawerScrollContent, QStackedWidget {
    background-color: transparent;
}
QLabel.brand-icon, QLabel[class="brand-icon"] {
    background-color: #0061ff;
    color: #ffffff;
    border-radius: 10px;
    font-size: 16px;
    font-weight: bold;
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
    border-radius: 19px;
}
QPushButton.wizard-step-btn, QPushButton[class="wizard-step-btn"] {
    background-color: transparent;
    border: none;
    border-radius: 15px;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton.wizard-step-btn:hover, QPushButton[class="wizard-step-btn"]:hover {
    color: #0f172a;
    background-color: #e2e8f0;
}
QPushButton.wizard-step-btn-active, QPushButton[class="wizard-step-btn-active"] {
    background-color: #0061ff;
    border: none;
    border-radius: 15px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 7px 18px;
}
QPushButton.wizard-step-btn-active:hover, QPushButton[class="wizard-step-btn-active"]:hover {
    background-color: #0052d9;
    color: #ffffff;
}
QPushButton.btn-settings, QPushButton[class="btn-settings"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #0f172a;
    font-size: 18px;
    padding: 0px;
}
QPushButton.btn-settings:hover, QPushButton[class="btn-settings"]:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}
QFrame.login-banner, QFrame[class="login-banner"] {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 14px;
}
QLabel.login-banner-icon, QLabel[class="login-banner-icon"] {
    background-color: #dbeafe;
    border-radius: 10px;
    font-size: 18px;
}
QFrame.account-pill, QFrame[class="account-pill"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame.url-command-card, QFrame[class="url-command-card"] {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
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
    background-color: #f8fafc;
    border-left: 1px solid #e2e8f0;
}
QLineEdit.drawer-subtle-input, QLineEdit[class="drawer-subtle-input"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    padding: 7px 12px;
    font-size: 12px;
}
QLineEdit.drawer-subtle-input:focus, QLineEdit[class="drawer-subtle-input"]:focus {
    border: 1px solid #0061ff;
}
QLineEdit.drawer-subtle-input:disabled, QLineEdit[class="drawer-subtle-input"]:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}
QPushButton.drawer-card-btn, QPushButton[class="drawer-card-btn"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
}
QPushButton.drawer-card-btn:hover, QPushButton[class="drawer-card-btn"]:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}
QPushButton.drawer-card-btn:disabled, QPushButton[class="drawer-card-btn"]:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}
QPushButton.drawer-close-btn, QPushButton[class="drawer-close-btn"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
}
QPushButton.drawer-close-btn:hover, QPushButton[class="drawer-close-btn"]:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}
QPushButton.drawer-acct-btn, QPushButton[class="drawer-acct-btn"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 10px;
}
QPushButton.drawer-acct-btn:hover, QPushButton[class="drawer-acct-btn"]:hover {
    background-color: #f8fafc;
    border-color: #cbd5e1;
}
QPushButton.drawer-signout-btn, QPushButton[class="drawer-signout-btn"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #ef4444;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 10px;
}
QPushButton.drawer-signout-btn:hover, QPushButton[class="drawer-signout-btn"]:hover {
    background-color: #fef2f2;
    border-color: #fecaca;
    color: #dc2626;
}
QPushButton.drawer-theme-btn, QPushButton[class="drawer-theme-btn"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 12px;
    text-align: left;
}
QPushButton.drawer-theme-btn:hover, QPushButton[class="drawer-theme-btn"]:hover {
    background-color: #f1f5f9;
    border-color: #cbd5e1;
}
QPushButton.drawer-log-link, QPushButton[class="drawer-log-link"] {
    background-color: transparent;
    border: none;
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
    padding: 2px 4px;
}
QPushButton.drawer-log-link:hover, QPushButton[class="drawer-log-link"]:hover {
    color: #0f172a;
    text-decoration: underline;
}
QPushButton.drawer-save-btn, QPushButton[class="drawer-save-btn"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    border-radius: 8px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton.drawer-save-btn:hover, QPushButton[class="drawer-save-btn"]:hover {
    background-color: #0052d9;
    border-color: #0052d9;
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
"""

