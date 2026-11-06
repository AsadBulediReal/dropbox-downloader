from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QSizePolicy,
    QHeaderView,
)

from .dialogs import FileTreeWidget


def build_header_bar(win: Any, root_layout: QVBoxLayout):
    header_card = QFrame()
    header_card.setProperty("class", "header-card")
    header_layout = QHBoxLayout(header_card)
    header_layout.setContentsMargins(24, 14, 24, 14)
    header_layout.setSpacing(12)

    brand_row = QHBoxLayout()
    brand_row.setSpacing(10)
    brand_icon = QLabel("📦")
    brand_icon.setProperty("class", "brand-icon")
    brand_icon.setFixedSize(32, 32)
    brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    brand_row.addWidget(brand_icon)

    title_label = QLabel("Dropbox Downloader")
    title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    title_label.setStyleSheet("background-color: transparent; font-weight: 700;")
    brand_row.addWidget(title_label)

    header_layout.addLayout(brand_row)
    header_layout.addStretch(1)

    # Center 3-Step Guided Wizard Pill Bar
    win.wizard_pill_bar = QFrame()
    win.wizard_pill_bar.setProperty("class", "wizard-pill-bar")
    win.wizard_pill_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    pill_layout = QHBoxLayout(win.wizard_pill_bar)
    pill_layout.setContentsMargins(4, 4, 4, 4)
    pill_layout.setSpacing(4)

    win.btn_step_1 = QPushButton("1. Link && Recent")
    win.btn_step_1.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    win.btn_step_1.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_step_1.clicked.connect(lambda: win.go_to_step(0))

    win.btn_step_2 = QPushButton("2. Select Files")
    win.btn_step_2.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    win.btn_step_2.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_step_2.clicked.connect(lambda: win.go_to_step(1))

    win.btn_step_3 = QPushButton("3. Transfers")
    win.btn_step_3.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    win.btn_step_3.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_step_3.clicked.connect(lambda: win.go_to_step(2))

    pill_layout.addWidget(win.btn_step_1)
    pill_layout.addWidget(win.btn_step_2)
    pill_layout.addWidget(win.btn_step_3)
    header_layout.addWidget(win.wizard_pill_bar, 0, Qt.AlignmentFlag.AlignVCenter)

    # Corner Settings Icon Button (right next to Steps Pill Bar)
    win.btn_settings = QPushButton("⚙️")
    win.btn_settings.setProperty("class", "btn-settings")
    win.btn_settings.setFixedSize(38, 38)
    win.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_settings.setToolTip("Settings — Open download folder, integrity rules, account, theme, and activity log")
    win.btn_settings.clicked.connect(win.toggle_settings_drawer)
    header_layout.addWidget(win.btn_settings, 0, Qt.AlignmentFlag.AlignVCenter)

    root_layout.addWidget(header_card)


def build_step1_page(win: Any) -> QWidget:
    step1_page = QWidget()
    step1_outer = QHBoxLayout(step1_page)
    step1_outer.setContentsMargins(0, 0, 0, 0)
    step1_outer.addStretch(1)

    step1_col = QWidget()
    step1_col.setMaximumWidth(768)
    step1_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    step1_layout = QVBoxLayout(step1_col)
    step1_layout.setContentsMargins(0, 12, 0, 12)
    step1_layout.setSpacing(20)
    step1_layout.addStretch(1)

    # Login Required Banner (shown when signed out)
    win.login_banner = QFrame()
    win.login_banner.setProperty("class", "login-banner")
    banner_layout = QHBoxLayout(win.login_banner)
    banner_layout.setContentsMargins(18, 14, 18, 14)
    banner_layout.setSpacing(14)

    banner_icon = QLabel("🔒")
    banner_icon.setProperty("class", "login-banner-icon")
    banner_icon.setFixedSize(40, 40)
    banner_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    banner_layout.addWidget(banner_icon, 0, Qt.AlignmentFlag.AlignVCenter)

    banner_text_layout = QVBoxLayout()
    banner_text_layout.setSpacing(2)
    banner_title = QLabel("Dropbox Sign-In Required")
    banner_title.setStyleSheet("font-size: 13px; font-weight: 700; background-color: transparent;")
    banner_desc = QLabel(
        "Sign in with your Dropbox account to unlock folder scanning and selective downloads."
    )
    banner_desc.setWordWrap(True)
    banner_desc.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    banner_text_layout.addWidget(banner_title)
    banner_text_layout.addWidget(banner_desc)
    banner_layout.addLayout(banner_text_layout, 1)

    win.btn_banner_login = QPushButton("🌐  Log In to Dropbox")
    win.btn_banner_login.setProperty("class", "btn-primary")
    win.btn_banner_login.setFixedHeight(36)
    win.btn_banner_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_banner_login.clicked.connect(win.login_with_dropbox)
    banner_layout.addWidget(win.btn_banner_login, 0, Qt.AlignmentFlag.AlignVCenter)
    step1_layout.addWidget(win.login_banner)

    # Centered Hero Title
    hero_box = QVBoxLayout()
    hero_box.setSpacing(6)
    hero_title = QLabel("Paste Dropbox Shared Link")
    hero_title.setProperty("class", "hero-title")
    hero_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hero_subtitle = QLabel("Enter a shared folder or file link, or reload a recent link in one click.")
    hero_subtitle.setProperty("class", "hero-subtitle")
    hero_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hero_subtitle.setWordWrap(True)
    hero_box.addWidget(hero_title)
    hero_box.addWidget(hero_subtitle)
    step1_layout.addLayout(hero_box)

    # Unified URL Command Card
    win.target_card = QFrame()
    win.target_card.setProperty("class", "url-command-card")
    target_layout = QHBoxLayout(win.target_card)
    target_layout.setContentsMargins(12, 10, 12, 10)
    target_layout.setSpacing(8)

    win.url_input = QLineEdit()
    win.url_input.setProperty("class", "command-input")
    win.url_input.setPlaceholderText("https://www.dropbox.com/scl/fo/... or https://www.dropbox.com/sh/...")
    win.url_input.textChanged.connect(win.on_url_text_changed)
    win.url_input.returnPressed.connect(win.start_scan)

    win.btn_clear_url = QPushButton("✕ Clear")
    win.btn_clear_url.setProperty("class", "btn-ghost")
    win.btn_clear_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_clear_url.setToolTip("Clear link and file list")
    win.btn_clear_url.clicked.connect(win.clear_url_and_tree)

    win.btn_paste_url = QPushButton("📋 Paste")
    win.btn_paste_url.setProperty("class", "btn-secondary")
    win.btn_paste_url.setMinimumHeight(38)
    win.btn_paste_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_paste_url.setToolTip("Paste link from clipboard and scan")
    win.btn_paste_url.clicked.connect(win.paste_url)

    win.btn_scan_url = QPushButton("Load Folders →")
    win.btn_scan_url.setProperty("class", "btn-load-folders")
    win.btn_scan_url.setMinimumHeight(40)
    win.btn_scan_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_scan_url.setToolTip("Inspect shared folder and select files (Enter)")
    win.btn_scan_url.clicked.connect(win.start_scan)

    target_layout.addWidget(win.url_input, 1)
    target_layout.addWidget(win.btn_clear_url)
    target_layout.addWidget(win.btn_paste_url)
    target_layout.addWidget(win.btn_scan_url)
    step1_layout.addWidget(win.target_card)

    # Recent Links Card (Quick Chips + Detailed Recent Rows)
    win.recent_card = QFrame()
    win.recent_card.setProperty("class", "card")
    recent_card_layout = QVBoxLayout(win.recent_card)
    recent_card_layout.setContentsMargins(20, 16, 20, 16)
    recent_card_layout.setSpacing(10)

    recent_header = QHBoxLayout()
    recent_title = QLabel("🕒 RECENT LINKS")
    recent_title.setProperty("class", "section-title")
    recent_header.addWidget(recent_title)
    recent_header.addStretch()

    win.btn_recent_links = QPushButton("All History ▼")
    win.btn_recent_links.setProperty("class", "btn-ghost")
    win.btn_recent_links.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_recent_links.setToolTip("Open full recent links menu or clear history")
    win.btn_recent_links.clicked.connect(win.show_recent_links_menu)
    recent_header.addWidget(win.btn_recent_links)
    recent_card_layout.addLayout(recent_header)

    win.recent_chips_container = QWidget()
    win.recent_chips_container.setStyleSheet("background-color: transparent;")
    win.recent_chips_layout = QHBoxLayout(win.recent_chips_container)
    win.recent_chips_layout.setContentsMargins(0, 0, 0, 2)
    win.recent_chips_layout.setSpacing(8)
    win.recent_chips_container.setVisible(False)
    recent_card_layout.addWidget(win.recent_chips_container)

    win.recent_rows_container = QWidget()
    win.recent_rows_container.setStyleSheet("background-color: transparent;")
    win.recent_rows_layout = QVBoxLayout(win.recent_rows_container)
    win.recent_rows_layout.setContentsMargins(0, 2, 0, 0)
    win.recent_rows_layout.setSpacing(2)
    recent_card_layout.addWidget(win.recent_rows_container)

    step1_layout.addWidget(win.recent_card)
    step1_layout.addStretch(2)

    step1_outer.addWidget(step1_col, 100)
    step1_outer.addStretch(1)
    return step1_page


def build_step2_page(win: Any) -> QWidget:
    step2_page = QWidget()
    step2_outer = QHBoxLayout(step2_page)
    step2_outer.setContentsMargins(0, 0, 0, 0)
    step2_outer.addStretch(1)

    step2_col = QWidget()
    step2_col.setMaximumWidth(920)
    step2_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    step2_layout = QVBoxLayout(step2_col)
    step2_layout.setContentsMargins(0, 4, 0, 4)
    step2_layout.setSpacing(12)

    # Top Toolbar Row
    step2_top_bar = QHBoxLayout()
    step2_top_bar.setSpacing(8)

    win.btn_back_to_link = QPushButton("← Change Link")
    win.btn_back_to_link.setProperty("class", "btn-secondary")
    win.btn_back_to_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_back_to_link.clicked.connect(lambda: win.go_to_step(0))
    step2_top_bar.addWidget(win.btn_back_to_link)

    win.step2_folder_label = QLabel("📂 Shared Folder")
    win.step2_folder_label.setStyleSheet("font-size: 13px; font-weight: 700; background-color: transparent;")
    step2_top_bar.addWidget(win.step2_folder_label)

    win.selection_summary_label = QLabel("(Paste link in Step 1 to inspect folders)")
    win.set_selection_summary("(Paste link in Step 1 to inspect folders)", "neutral")
    step2_top_bar.addWidget(win.selection_summary_label)

    step2_top_bar.addStretch()

    win.btn_select_all = QPushButton("Select All")
    win.btn_select_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_select_all.clicked.connect(win.select_all_items)

    win.btn_deselect_all = QPushButton("Deselect All")
    win.btn_deselect_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_deselect_all.clicked.connect(win.deselect_all_items)

    win.btn_expand_all = QPushButton("Expand All")
    win.btn_expand_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_expand_all.clicked.connect(lambda: win.tree_widget.expandAll())

    win.btn_collapse_all = QPushButton("Collapse All")
    win.btn_collapse_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_collapse_all.clicked.connect(lambda: win.tree_widget.collapseAll())

    step2_top_bar.addWidget(win.btn_select_all)
    step2_top_bar.addWidget(win.btn_deselect_all)
    step2_top_bar.addWidget(win.btn_expand_all)
    step2_top_bar.addWidget(win.btn_collapse_all)
    step2_layout.addLayout(step2_top_bar)

    # Spacious Tree Card
    win.tree_card = QFrame()
    win.tree_card.setProperty("class", "card")
    tree_layout = QVBoxLayout(win.tree_card)
    tree_layout.setContentsMargins(16, 14, 16, 14)
    tree_layout.setSpacing(8)

    win.tree_widget = FileTreeWidget()
    win.tree_widget.setHeaderLabels(["Folder / File Name", "Type", "Size"])
    win.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    win.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    win.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    win.tree_widget.setMinimumHeight(290)
    win.tree_widget.setAnimated(True)
    win.tree_widget.setExpandsOnDoubleClick(True)
    win.tree_widget.itemChanged.connect(win.on_tree_item_changed)
    win.tree_widget.itemClicked.connect(win.on_tree_item_clicked)
    win.tree_widget.itemExpanded.connect(win.on_tree_item_expanded)
    win.tree_widget.itemCollapsed.connect(win.on_tree_item_collapsed)
    win.tree_widget.shiftRangeRequested.connect(win.on_tree_shift_range_selected)
    win.tree_widget.spacePressed.connect(win.on_tree_space_pressed)
    win.tree_widget.currentItemChanged.connect(win.on_tree_current_item_changed)
    win.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    win.tree_widget.customContextMenuRequested.connect(win.show_tree_context_menu)
    tree_layout.addWidget(win.tree_widget, 1)

    win.tree_hint = QLabel(
        "💡 Tip: Check files/folders to download. Shift+Click for range select. Space to toggle. Right-click for options."
    )
    win.tree_hint.setStyleSheet("font-size: 11px; color: #64748b; background-color: transparent;")
    tree_layout.addWidget(win.tree_hint)
    step2_layout.addWidget(win.tree_card, 1)

    # Bottom Action Footer
    step2_footer = QHBoxLayout()
    step2_footer.setSpacing(10)

    win.dest_summary_label = QLabel()
    win.dest_summary_label.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    step2_footer.addWidget(win.dest_summary_label)

    win.btn_change_dest = QPushButton("Change in ⚙️ Settings")
    win.btn_change_dest.setProperty("class", "ad-cta")
    win.btn_change_dest.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_change_dest.clicked.connect(win.open_settings_drawer)
    step2_footer.addWidget(win.btn_change_dest)

    step2_footer.addStretch()

    win.btn_verify_files = QPushButton("🔍  Verify Existing")
    win.btn_verify_files.setProperty("class", "btn-secondary")
    win.btn_verify_files.setEnabled(False)
    win.btn_verify_files.setMinimumHeight(40)
    win.btn_verify_files.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_verify_files.setToolTip(
        "Verify existing downloaded files against Dropbox cloud checksums without re-downloading intact files."
    )
    win.btn_verify_files.clicked.connect(win.start_verification_only)

    win.start_button = QPushButton("📋  Paste Link && Select Files to Start")
    win.start_button.setProperty("class", "btn-start")
    win.start_button.setEnabled(False)
    win.start_button.setMinimumHeight(40)
    win.start_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.start_button.clicked.connect(win.start_download)

    win.btn_view_active_transfer = QPushButton("View Active Transfer →")
    win.btn_view_active_transfer.setProperty("class", "btn-primary")
    win.btn_view_active_transfer.setMinimumHeight(40)
    win.btn_view_active_transfer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_view_active_transfer.setVisible(False)
    win.btn_view_active_transfer.clicked.connect(lambda: win.go_to_step(2))

    step2_footer.addWidget(win.btn_verify_files)
    step2_footer.addWidget(win.start_button)
    step2_footer.addWidget(win.btn_view_active_transfer)
    step2_layout.addLayout(step2_footer)

    step2_outer.addWidget(step2_col, 100)
    step2_outer.addStretch(1)
    return step2_page

