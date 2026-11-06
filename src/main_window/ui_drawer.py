from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QCheckBox,
    QScrollArea,
    QStackedWidget,
    QSizePolicy,
)

from ..ads import AdBannerWidget
from .widgets_theme import _ClickBackdrop
from .ui_steps12 import build_header_bar, build_step1_page, build_step2_page
from .ui_step3 import build_step3_page


def build_settings_drawer(win: Any):
    win.settings_overlay = QWidget(win)
    win.settings_overlay.setVisible(False)
    overlay_layout = QHBoxLayout(win.settings_overlay)
    overlay_layout.setContentsMargins(0, 0, 0, 0)
    overlay_layout.setSpacing(0)

    win.settings_backdrop = _ClickBackdrop(win.settings_overlay)
    win.settings_backdrop.clicked.connect(win.close_settings_drawer)
    overlay_layout.addWidget(win.settings_backdrop, 1)

    win.settings_drawer = QFrame(win.settings_overlay)
    win.settings_drawer.setProperty("class", "settings-drawer")
    win.settings_drawer.setFixedWidth(448)
    drawer_outer = QVBoxLayout(win.settings_drawer)
    drawer_outer.setContentsMargins(24, 20, 24, 20)
    drawer_outer.setSpacing(12)

    drawer_header = QHBoxLayout()
    drawer_header.setContentsMargins(0, 0, 0, 2)
    drawer_title = QLabel("⚙️ Settings & Diagnostics")
    drawer_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    drawer_title.setStyleSheet("background-color: transparent; font-size: 16px; font-weight: 700;")
    drawer_header.addWidget(drawer_title)
    drawer_header.addStretch()

    win.btn_close_settings = QPushButton("✕ Close")
    win.btn_close_settings.setProperty("class", "drawer-close-btn")
    win.btn_close_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_close_settings.clicked.connect(win.close_settings_drawer)
    drawer_header.addWidget(win.btn_close_settings)
    drawer_outer.addLayout(drawer_header)

    drawer_top_divider = QFrame()
    drawer_top_divider.setProperty("class", "divider-line")
    drawer_outer.addWidget(drawer_top_divider)

    drawer_scroll = QScrollArea()
    drawer_scroll.setWidgetResizable(True)
    drawer_scroll.setFrameShape(QFrame.Shape.NoFrame)
    drawer_scroll.viewport().setAutoFillBackground(False)
    drawer_content = QWidget()
    drawer_content.setObjectName("drawerScrollContent")
    drawer_layout = QVBoxLayout(drawer_content)
    drawer_layout.setContentsMargins(0, 4, 2, 4)
    drawer_layout.setSpacing(18)

    # 1. Default Download Folder
    dest_sec = QVBoxLayout()
    dest_sec.setSpacing(8)
    dest_lbl = QLabel("DEFAULT DOWNLOAD FOLDER")
    dest_lbl.setProperty("class", "section-title")
    dest_sec.addWidget(dest_lbl)

    dest_row = QHBoxLayout()
    dest_row.setSpacing(8)
    win.destination_input = QLineEdit()
    win.destination_input.setProperty("class", "drawer-subtle-input")
    win.destination_input.setText(str(Path.home() / "Downloads"))
    win.destination_input.setPlaceholderText("Select local folder to save files...")
    win.destination_input.textChanged.connect(win._on_destination_changed)
    win.destination_input.editingFinished.connect(win.save_settings)

    win.btn_browse = QPushButton("Browse")
    win.btn_browse.setProperty("class", "drawer-card-btn")
    win.btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_browse.clicked.connect(win.browse_destination)

    win.btn_open_folder = QPushButton("Open")
    win.btn_open_folder.setProperty("class", "drawer-card-btn")
    win.btn_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_open_folder.clicked.connect(win.open_destination_folder)

    dest_row.addWidget(win.destination_input, 1)
    dest_row.addWidget(win.btn_browse)
    dest_row.addWidget(win.btn_open_folder)
    dest_sec.addLayout(dest_row)
    drawer_layout.addLayout(dest_sec)

    # 2. Smart Download & Integrity Rules
    rules_sec = QVBoxLayout()
    rules_sec.setSpacing(10)
    rules_lbl = QLabel("DOWNLOAD & INTEGRITY RULES")
    rules_lbl.setProperty("class", "section-title")
    rules_sec.addWidget(rules_lbl)

    win.check_skip_existing = QCheckBox("Skip files that already exist locally (exact size)")
    win.check_skip_existing.setChecked(True)
    win.check_skip_existing.stateChanged.connect(lambda: win.save_settings())
    rules_sec.addWidget(win.check_skip_existing)

    win.check_verify_integrity = QCheckBox("Verify SHA-256 checksum after download")
    win.check_verify_integrity.setChecked(True)
    win.check_verify_integrity.stateChanged.connect(win._on_verify_setting_changed)
    rules_sec.addWidget(win.check_verify_integrity)

    win.check_auto_repair = QCheckBox("Auto re-download if file is corrupted")
    win.check_auto_repair.setChecked(True)
    win.check_auto_repair.stateChanged.connect(lambda: win.save_settings())
    rules_sec.addWidget(win.check_auto_repair)
    drawer_layout.addLayout(rules_sec)

    # 3. Dropbox Account
    acct_sec = QVBoxLayout()
    acct_sec.setSpacing(8)
    acct_lbl = QLabel("DROPBOX ACCOUNT")
    acct_lbl.setProperty("class", "section-title")
    acct_sec.addWidget(acct_lbl)

    account_pill = QFrame()
    account_pill.setProperty("class", "subtle-card")
    account_pill_layout = QHBoxLayout(account_pill)
    account_pill_layout.setContentsMargins(14, 12, 14, 12)
    account_pill_layout.setSpacing(6)

    win.account_info_layout = QVBoxLayout()
    win.account_info_layout.setSpacing(2)
    win.account_name_label = QLabel("No Dropbox account connected")
    win.account_name_label.setStyleSheet("font-size: 12px; font-weight: 700; background-color: transparent;")
    win.account_sub_label = QLabel("Sign in to your Dropbox account")
    win.account_sub_label.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    win.account_info_layout.addWidget(win.account_name_label)
    win.account_info_layout.addWidget(win.account_sub_label)
    account_pill_layout.addLayout(win.account_info_layout, 1)

    win.btn_oauth_login = QPushButton("Log In")
    win.btn_oauth_login.setProperty("class", "drawer-save-btn")
    win.btn_oauth_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_oauth_login.clicked.connect(win.login_with_dropbox)
    account_pill_layout.addWidget(win.btn_oauth_login)

    win.btn_logout = QPushButton("Sign Out")
    win.btn_logout.setProperty("class", "drawer-signout-btn")
    win.btn_logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_logout.clicked.connect(win.logout_dropbox)
    win.btn_logout.setVisible(False)
    account_pill_layout.addWidget(win.btn_logout)

    acct_sec.addWidget(account_pill)
    drawer_layout.addLayout(acct_sec)

    # 4. Appearance
    theme_sec = QVBoxLayout()
    theme_sec.setSpacing(8)
    theme_lbl = QLabel("APPEARANCE")
    theme_lbl.setProperty("class", "section-title")
    theme_sec.addWidget(theme_lbl)

    win.btn_theme_toggle = QPushButton("🌗  Switch Light / Dark Mode")
    win.btn_theme_toggle.setProperty("class", "drawer-theme-btn")
    win.btn_theme_toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    win.btn_theme_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_theme_toggle.clicked.connect(win.toggle_theme)
    theme_sec.addWidget(win.btn_theme_toggle)
    drawer_layout.addLayout(theme_sec)

    # 5. Activity Log & Diagnostics
    log_sec = QVBoxLayout()
    log_sec.setSpacing(8)
    log_header = QHBoxLayout()
    log_header.setSpacing(8)
    log_title = QLabel("ACTIVITY LOG")
    log_title.setProperty("class", "section-title")
    log_header.addWidget(log_title)
    log_header.addStretch()

    btn_copy = QPushButton("Copy")
    btn_copy.setProperty("class", "drawer-log-link")
    btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_copy.clicked.connect(win.copy_log)
    btn_clear = QPushButton("Clear")
    btn_clear.setProperty("class", "drawer-log-link")
    btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_clear.clicked.connect(win.clear_log)
    win.btn_toggle_log = QPushButton("Hide Log")
    win.btn_toggle_log.setProperty("class", "drawer-log-link")
    win.btn_toggle_log.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_toggle_log.clicked.connect(win.toggle_log_visibility)

    log_header.addWidget(btn_copy)
    log_header.addWidget(btn_clear)
    log_header.addWidget(win.btn_toggle_log)
    log_sec.addLayout(log_header)

    win.log_filter = QLineEdit()
    win.log_filter.setProperty("class", "drawer-subtle-input")
    win.log_filter.setPlaceholderText("Filter logs...")
    win.log_filter.textChanged.connect(win.filter_logs)
    log_sec.addWidget(win.log_filter)

    win.log_box = QPlainTextEdit()
    win.log_box.setReadOnly(True)
    win.log_box.setMinimumHeight(105)
    win.log_box.setMaximumHeight(135)
    log_sec.addWidget(win.log_box)
    drawer_layout.addLayout(log_sec)

    drawer_layout.addStretch(1)
    drawer_scroll.setWidget(drawer_content)
    drawer_outer.addWidget(drawer_scroll, 1)

    drawer_bot_divider = QFrame()
    drawer_bot_divider.setProperty("class", "divider-line")
    drawer_outer.addWidget(drawer_bot_divider)

    drawer_footer = QHBoxLayout()
    drawer_footer.setContentsMargins(0, 2, 0, 0)
    drawer_footer.addStretch()
    btn_save_close = QPushButton("Save && Close")
    btn_save_close.setProperty("class", "drawer-save-btn")
    btn_save_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn_save_close.clicked.connect(win._save_and_close_settings)
    drawer_footer.addWidget(btn_save_close)
    drawer_outer.addLayout(drawer_footer)

    overlay_layout.addWidget(win.settings_drawer)


def setup_main_window_ui(win: Any):
    root_widget = QWidget()
    root_layout = QVBoxLayout(root_widget)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    build_header_bar(win, root_layout)

    workspace_scroll = QScrollArea()
    workspace_scroll.setWidgetResizable(True)
    workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
    workspace_scroll.viewport().setAutoFillBackground(False)

    workspace_container = QWidget()
    workspace_container.setObjectName("workspaceContainer")
    workspace_layout = QVBoxLayout(workspace_container)
    workspace_layout.setContentsMargins(28, 20, 28, 12)
    workspace_layout.setSpacing(14)

    win.wizard_stack = QStackedWidget()
    win.wizard_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    win.wizard_stack.addWidget(build_step1_page(win))
    win.wizard_stack.addWidget(build_step2_page(win))
    win.wizard_stack.addWidget(build_step3_page(win))

    workspace_layout.addWidget(win.wizard_stack, 1)
    workspace_scroll.setWidget(workspace_container)
    root_layout.addWidget(workspace_scroll, 1)

    # Persistent clean bottom banner ad
    ad_outer = QHBoxLayout()
    ad_outer.setContentsMargins(28, 4, 28, 18)
    ad_outer.addStretch(1)
    win.ad_banner = AdBannerWidget(win)
    win.ad_banner.setMaximumWidth(920)
    win.ad_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    ad_outer.addWidget(win.ad_banner, 100)
    ad_outer.addStretch(1)
    root_layout.addLayout(ad_outer)

    win.setCentralWidget(root_widget)

    build_settings_drawer(win)

    win.all_log_lines = []

    # Initialize states
    win.apply_theme("light", save=False)
    win._on_destination_changed(win.destination_input.text())
    win.go_to_step(0)
    win.set_queue_filter("all")
    win.show_empty_tree_placeholder()
    win._show_empty_queue_placeholder()

