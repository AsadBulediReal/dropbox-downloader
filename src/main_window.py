import os
import sys
import time
import re
import json
import webbrowser
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import ApiError, AuthError

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt, QSettings, QTimer
from PySide6.QtGui import QFont, QTextCursor, QCursor, QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QGridLayout,
    QCheckBox,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QHeaderView,
    QInputDialog,
    QDialog,
    QMenu,
)

from .styles import DARK_STYLESHEET
from .utils import (
    format_bytes,
    sanitize_filename,
    extract_folder_name_from_url,
    parse_friendly_error,
    is_thread_running,
    safe_local_path,
    strip_folder_prefix,
    check_single_folder_destination_match,
    resolve_download_root,
    relative_path,
    get_file_type_and_icon,
    natural_sort_key,
    natural_sort_path_key,
    compute_dropbox_content_hash,
    build_tree_hierarchy,
    is_path_selected,
    create_dropbox_client,
)
from .workers import (
    AuthWorker,
    SessionVerifyWorker,
    ScanWorker,
    DownloadFileItem,
    DownloadWorker,
)
from .dialogs import (
    ModernMessageBox,
    ModernInputDialog,
    ModernLoadingDialog,
    FileTreeWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dropbox Recursive Downloader Pro")
        self.resize(940, 860)
        self.setMinimumSize(840, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        self.settings = QSettings("DropboxDownloader", "RecursiveGUI")
        self._active_workers: dict[QThread, QObject] = {}
        self.download_thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.auth_thread: QThread | None = None
        self.auth_worker: AuthWorker | None = None
        self.verify_thread: QThread | None = None
        self.verify_worker: SessionVerifyWorker | None = None
        self._updating_tree = False
        self._tree_items_data: list[Any] = []

        self.current_access_token: str = ""
        self.current_refresh_token: str = ""
        self.current_user_name: str = ""
        self.current_user_email: str = ""
        self.link_password: str = ""
        self.recent_links: list[dict[str, Any]] = []
        self.is_download_paused: bool = False
        self._is_running: bool = False
        self.current_root_name: str = ""

        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.setSingleShot(True)
        self.auto_scan_timer.timeout.connect(self.auto_scan_if_valid)

        self.setup_ui()
        self.load_settings()

    def set_status_badge(self, text: str, state: str = "ready"):
        styles = {
            "ready": "background-color: #1e293b; color: #38bdf8; border: 1px solid #334155;",
            "running": "background-color: #0c2e59; color: #60a5fa; border: 1px solid #1d4ed8;",
            "verifying": "background-color: #2e1065; color: #c084fc; border: 1px solid #7e22ce;",
            "success": "background-color: #064e3b; color: #34d399; border: 1px solid #059669;",
            "warning": "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706;",
            "error": "background-color: #450a0a; color: #f87171; border: 1px solid #b91c1c;",
            "neutral": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;",
        }
        style_str = styles.get(state, styles["ready"])
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(
            f"{style_str} border-radius: 12px; padding: 4px 14px; font-weight: 600; font-size: 11px;"
        )

    def set_auth_badge(self, text: str, state: str = "neutral"):
        styles = {
            "connected": "background-color: #064e3b; color: #34d399; border: 1px solid #059669;",
            "neutral": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;",
        }
        style_str = styles.get(state, styles["neutral"])
        self.auth_badge.setText(text)
        self.auth_badge.setStyleSheet(
            f"{style_str} border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )

    def set_selection_summary(self, text: str, state: str = "neutral"):
        colors = {
            "neutral": "#94a3b8",
            "active": "#38bdf8",
            "success": "#10b981",
            "error": "#f87171",
        }
        col = colors.get(state, "#94a3b8")
        self.selection_summary_label.setText(text)
        self.selection_summary_label.setStyleSheet(f"font-size: 11px; color: {col}; font-weight: 600;")

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Section (Brand + Account + Status)
        header_card = QFrame()
        header_card.setProperty("class", "header-card")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        brand_icon = QLabel("📦")
        brand_icon.setStyleSheet("font-size: 20px;")
        title_label = QLabel("Dropbox Recursive Downloader Pro")
        title_font = QFont("Segoe UI", 15, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #38bdf8; font-weight: 700;")
        title_row.addWidget(brand_icon)
        title_row.addWidget(title_label)
        title_row.addStretch()

        subtitle_label = QLabel("Selectively download files and folder hierarchies directly from Dropbox shared links")
        subtitle_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        subtitle_label.setWordWrap(True)

        header_text_layout.addLayout(title_row)
        header_text_layout.addWidget(subtitle_label)
        header_layout.addLayout(header_text_layout)

        header_layout.addStretch()

        # Account Pill
        account_pill = QFrame()
        account_pill.setProperty("class", "account-pill")
        account_pill_layout = QHBoxLayout(account_pill)
        account_pill_layout.setContentsMargins(10, 5, 10, 5)
        account_pill_layout.setSpacing(8)

        self.account_info_layout = QVBoxLayout()
        self.account_info_layout.setSpacing(1)
        self.account_name_label = QLabel("No Dropbox account connected")
        self.account_name_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #f8fafc;")
        self.account_sub_label = QLabel("Sign in to your Dropbox account")
        self.account_sub_label.setStyleSheet("font-size: 10px; color: #94a3b8;")
        self.account_info_layout.addWidget(self.account_name_label)
        self.account_info_layout.addWidget(self.account_sub_label)
        account_pill_layout.addLayout(self.account_info_layout)

        self.auth_badge = QLabel()
        self.set_auth_badge("○ Not Logged In", "neutral")
        account_pill_layout.addWidget(self.auth_badge)

        self.btn_oauth_login = QPushButton("🌐  Log In")
        self.btn_oauth_login.setProperty("class", "btn-primary")
        self.btn_oauth_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_oauth_login.setToolTip("Sign into your Dropbox account via browser (PKCE OAuth)")
        self.btn_oauth_login.clicked.connect(self.login_with_dropbox)
        account_pill_layout.addWidget(self.btn_oauth_login)

        self.btn_logout = QPushButton("Sign Out")
        self.btn_logout.setProperty("class", "btn-secondary")
        self.btn_logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_logout.setToolTip("Sign out of current Dropbox account")
        self.btn_logout.clicked.connect(self.logout_dropbox)
        self.btn_logout.setVisible(False)
        account_pill_layout.addWidget(self.btn_logout)

        header_layout.addWidget(account_pill)

        self.status_badge = QLabel()
        self.set_status_badge("● Ready", "ready")
        header_layout.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(header_card)

        # Authentication Required Banner (shown when user is not logged in)
        self.login_banner = QFrame()
        self.login_banner.setProperty("class", "login-banner")
        banner_layout = QHBoxLayout(self.login_banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.setSpacing(12)

        banner_icon = QLabel("🔒")
        banner_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
        banner_layout.addWidget(banner_icon)

        banner_text_layout = QVBoxLayout()
        banner_text_layout.setSpacing(2)
        banner_title = QLabel("Dropbox Sign-In Required")
        banner_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f8fafc; background-color: transparent;")
        banner_desc = QLabel(
            "Features are locked. Please sign in to your Dropbox account to enable folder scanning and downloads."
        )
        banner_desc.setStyleSheet("font-size: 11px; color: #94a3b8; background-color: transparent;")
        banner_text_layout.addWidget(banner_title)
        banner_text_layout.addWidget(banner_desc)
        banner_layout.addLayout(banner_text_layout)
        banner_layout.addStretch()

        self.btn_banner_login = QPushButton("🌐  Log In to Dropbox")
        self.btn_banner_login.setProperty("class", "btn-primary")
        self.btn_banner_login.setFixedHeight(34)
        self.btn_banner_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_banner_login.clicked.connect(self.login_with_dropbox)
        banner_layout.addWidget(self.btn_banner_login)

        main_layout.addWidget(self.login_banner)

        # 1. Source & Local Destination Card
        self.target_card = QFrame()
        self.target_card.setProperty("class", "card")
        target_layout = QVBoxLayout(self.target_card)
        target_layout.setContentsMargins(16, 14, 16, 14)
        target_layout.setSpacing(10)

        target_title = QLabel("1. Source & Local Destination")
        target_title.setProperty("class", "section-title")
        target_layout.addWidget(target_title)

        url_label = QLabel("Dropbox Shared Link:")
        url_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        target_layout.addWidget(url_label)

        url_row = QHBoxLayout()
        url_row.setSpacing(6)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.dropbox.com/scl/fo/... or https://www.dropbox.com/sh/...")
        self.url_input.textChanged.connect(self.on_url_text_changed)
        self.url_input.returnPressed.connect(self.start_scan)

        self.btn_recent_links = QPushButton("🕒 Recent ▼")
        self.btn_recent_links.setToolTip("Select from previously saved Dropbox links")
        self.btn_recent_links.clicked.connect(self.show_recent_links_menu)

        self.btn_paste_url = QPushButton("📋 Paste")
        self.btn_paste_url.setToolTip("Paste link from clipboard and scan")
        self.btn_paste_url.clicked.connect(self.paste_url)

        self.btn_clear_url = QPushButton("✕ Clear")
        self.btn_clear_url.setToolTip("Clear link and file list")
        self.btn_clear_url.clicked.connect(self.clear_url_and_tree)

        self.btn_scan_url = QPushButton("🔍 Load Folders")
        self.btn_scan_url.setProperty("class", "btn-primary")
        self.btn_scan_url.setToolTip("Inspect shared folder and display files below (Enter)")
        self.btn_scan_url.clicked.connect(self.start_scan)

        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.btn_recent_links)
        url_row.addWidget(self.btn_paste_url)
        url_row.addWidget(self.btn_clear_url)
        url_row.addWidget(self.btn_scan_url)
        target_layout.addLayout(url_row)

        # Quick Recent Links Chips Row
        self.recent_chips_container = QWidget()
        self.recent_chips_layout = QHBoxLayout(self.recent_chips_container)
        self.recent_chips_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_chips_layout.setSpacing(6)
        self.recent_chips_container.setVisible(False)
        target_layout.addWidget(self.recent_chips_container)

        dest_label = QLabel("Save Downloaded Files To:")
        dest_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 4px;")
        target_layout.addWidget(dest_label)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(6)
        self.destination_input = QLineEdit()
        self.destination_input.setText(str(Path.home() / "Downloads"))
        self.destination_input.setPlaceholderText("Select local folder to save files...")
        self.destination_input.setToolTip(
            "Target folder for downloads.\n"
            "If the selected folder has the same name as the Dropbox folder, "
            "files will download directly into it without creating an extra root folder."
        )

        self.btn_browse = QPushButton("📁 Browse...")
        self.btn_browse.setFixedWidth(105)
        self.btn_browse.clicked.connect(self.browse_destination)

        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_open_folder.setFixedWidth(120)
        self.btn_open_folder.clicked.connect(self.open_destination_folder)

        dest_row.addWidget(self.destination_input, 1)
        dest_row.addWidget(self.btn_browse)
        dest_row.addWidget(self.btn_open_folder)
        target_layout.addLayout(dest_row)

        dest_opts_row = QHBoxLayout()
        dest_opts_row.setSpacing(14)
        self.check_skip_existing = QCheckBox("Skip files that already exist locally (matching exact size)")
        self.check_skip_existing.setChecked(True)
        self.check_skip_existing.setToolTip("Skip files that already exist on disk with the exact matching size.")
        self.check_skip_existing.stateChanged.connect(lambda: self.save_settings())
        dest_opts_row.addWidget(self.check_skip_existing)

        self.check_verify_integrity = QCheckBox("Verify file integrity after download (Dropbox checksum)")
        self.check_verify_integrity.setChecked(True)
        self.check_verify_integrity.setToolTip("Compute SHA-256 block hash of files and verify against Dropbox cloud checksum to guarantee 0% corruption.")
        self.check_verify_integrity.stateChanged.connect(lambda: self.save_settings())
        dest_opts_row.addWidget(self.check_verify_integrity)

        self.check_auto_repair = QCheckBox("Auto re-download if file is corrupted")
        self.check_auto_repair.setChecked(True)
        self.check_auto_repair.setToolTip("Automatically delete and re-download any file that fails integrity check or has checksum mismatch.")
        self.check_auto_repair.stateChanged.connect(lambda: self.save_settings())
        dest_opts_row.addWidget(self.check_auto_repair)

        dest_opts_row.addStretch()
        target_layout.addLayout(dest_opts_row)

        main_layout.addWidget(self.target_card)

        # 2. Tree Selection Card
        self.tree_card = QFrame()
        self.tree_card.setProperty("class", "card")
        tree_layout = QVBoxLayout(self.tree_card)
        tree_layout.setContentsMargins(16, 14, 16, 14)
        tree_layout.setSpacing(8)

        tree_header = QHBoxLayout()
        tree_title = QLabel("2. Folder & File Selection")
        tree_title.setProperty("class", "section-title")
        tree_header.addWidget(tree_title)

        self.selection_summary_label = QLabel("(Paste link above to inspect folders)")
        self.selection_summary_label.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        tree_header.addWidget(self.selection_summary_label)

        tree_header.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(self.select_all_items)
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)
        self.btn_expand_all = QPushButton("Expand All")
        self.btn_expand_all.clicked.connect(lambda: self.tree_widget.expandAll())
        self.btn_collapse_all = QPushButton("Collapse All")
        self.btn_collapse_all.clicked.connect(lambda: self.tree_widget.collapseAll())

        tree_header.addWidget(self.btn_select_all)
        tree_header.addWidget(self.btn_deselect_all)
        tree_header.addWidget(self.btn_expand_all)
        tree_header.addWidget(self.btn_collapse_all)
        tree_layout.addLayout(tree_header)

        self.tree_widget = FileTreeWidget()
        self.tree_widget.setHeaderLabels(["Name", "Type", "Size"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.setMinimumHeight(240)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setExpandsOnDoubleClick(True)
        self.tree_widget.itemChanged.connect(self.on_tree_item_changed)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.itemExpanded.connect(self.on_tree_item_expanded)
        self.tree_widget.itemCollapsed.connect(self.on_tree_item_collapsed)
        self.tree_widget.shiftRangeRequested.connect(self.on_tree_shift_range_selected)
        self.tree_widget.spacePressed.connect(self.on_tree_space_pressed)
        self.tree_widget.currentItemChanged.connect(self.on_tree_current_item_changed)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        tree_layout.addWidget(self.tree_widget)
        self.show_empty_tree_placeholder()

        self.tree_hint = QLabel("💡 Tip: Click or check files to select for download. Shift+Click to select a range. Space to toggle. Right-click for options.")
        self.tree_hint.setStyleSheet("font-size: 11px; color: #94a3b8;")
        tree_layout.addWidget(self.tree_hint)

        main_layout.addWidget(self.tree_card)

        # 3. Progress & Status Card
        self.progress_card = QFrame()
        self.progress_card.setProperty("class", "card")
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(10)

        prog_title = QLabel("3. Download Status & Progress")
        prog_title.setProperty("class", "section-title")
        progress_layout.addWidget(prog_title)

        # Current File Progress Row
        file_prog_header = QHBoxLayout()
        lbl_cur = QLabel("Current File:")
        lbl_cur.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.file_label = QLabel("Idle")
        self.file_label.setStyleSheet("font-size: 11px; color: #f1f5f9; font-weight: 600;")
        file_prog_header.addWidget(lbl_cur)
        file_prog_header.addWidget(self.file_label)
        file_prog_header.addStretch()
        self.file_pct_label = QLabel("0%")
        self.file_pct_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #38bdf8;")
        file_prog_header.addWidget(self.file_pct_label)
        progress_layout.addLayout(file_prog_header)

        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress.setValue(0)
        progress_layout.addWidget(self.file_progress)

        # Overall Progress Row
        overall_prog_header = QHBoxLayout()
        lbl_all = QLabel("Overall Download Progress:")
        lbl_all.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.folder_label = QLabel("Idle")
        self.folder_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        overall_prog_header.addWidget(lbl_all)
        overall_prog_header.addWidget(self.folder_label)
        overall_prog_header.addStretch()
        self.overall_pct_label = QLabel("0%")
        self.overall_pct_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #10b981;")
        overall_prog_header.addWidget(self.overall_pct_label)
        progress_layout.addLayout(overall_prog_header)

        self.overall_progress = QProgressBar()
        self.overall_progress.setProperty("class", "overall")
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        progress_layout.addWidget(self.overall_progress)

        # Live Metrics Grid
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)

        # Speed Card
        c_speed = QFrame()
        c_speed.setProperty("class", "metric-card")
        l_speed = QVBoxLayout(c_speed)
        l_speed.setContentsMargins(6, 4, 6, 4)
        t_speed = QLabel("⚡ Speed")
        t_speed.setProperty("class", "metric-title")
        self.val_speed = QLabel("0 B/s")
        self.val_speed.setProperty("class", "metric-value")
        l_speed.addWidget(t_speed)
        l_speed.addWidget(self.val_speed)
        metrics_grid.addWidget(c_speed, 0, 0)

        # Transferred Card
        c_data = QFrame()
        c_data.setProperty("class", "metric-card")
        l_data = QVBoxLayout(c_data)
        l_data.setContentsMargins(6, 4, 6, 4)
        t_data = QLabel("📦 Transferred")
        t_data.setProperty("class", "metric-title")
        self.val_data = QLabel("0 B")
        self.val_data.setProperty("class", "metric-value")
        l_data.addWidget(t_data)
        l_data.addWidget(self.val_data)
        metrics_grid.addWidget(c_data, 0, 1)

        # Files Completed Card
        c_files = QFrame()
        c_files.setProperty("class", "metric-card")
        l_files = QVBoxLayout(c_files)
        l_files.setContentsMargins(6, 4, 6, 4)
        t_files = QLabel("📑 Files")
        t_files.setProperty("class", "metric-title")
        self.val_files = QLabel("0 files")
        self.val_files.setProperty("class", "metric-value")
        l_files.addWidget(t_files)
        l_files.addWidget(self.val_files)
        metrics_grid.addWidget(c_files, 0, 2)

        # Time Card
        c_time = QFrame()
        c_time.setProperty("class", "metric-card")
        l_time = QVBoxLayout(c_time)
        l_time.setContentsMargins(6, 4, 6, 4)
        t_time = QLabel("⏱️ Time Elapsed")
        t_time.setProperty("class", "metric-title")
        self.val_time = QLabel("00:00")
        self.val_time.setProperty("class", "metric-value")
        l_time.addWidget(t_time)
        l_time.addWidget(self.val_time)
        metrics_grid.addWidget(c_time, 0, 3)

        progress_layout.addLayout(metrics_grid)

        # Action Buttons Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)

        self.start_button = QPushButton("📋  Paste Link & Select Files to Start")
        self.start_button.setProperty("class", "btn-start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_download)

        self.btn_verify_files = QPushButton("🔍  Verify Files")
        self.btn_verify_files.setProperty("class", "btn-primary")
        self.btn_verify_files.setEnabled(False)
        self.btn_verify_files.setToolTip("Verify existing downloaded files against Dropbox cloud checksums without re-downloading intact files.")
        self.btn_verify_files.clicked.connect(self.start_verification_only)

        self.pause_button = QPushButton("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        self.pause_button.setVisible(False)
        self.pause_button.clicked.connect(self.toggle_pause_download)

        self.stop_button = QPushButton("⏹  Stop Download")
        self.stop_button.setProperty("class", "btn-stop")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self.stop_download)

        actions_row.addWidget(self.start_button, 2)
        actions_row.addWidget(self.btn_verify_files, 1)
        actions_row.addWidget(self.pause_button, 1)
        actions_row.addWidget(self.stop_button, 1)
        progress_layout.addLayout(actions_row)

        main_layout.addWidget(self.progress_card)

        # 5. Activity Log Card
        log_card = QFrame()
        log_card.setProperty("class", "card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(14, 12, 14, 12)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()
        log_title = QLabel("Activity Log")
        log_title.setProperty("class", "section-title")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Filter logs...")
        self.log_filter.setFixedWidth(180)
        self.log_filter.textChanged.connect(self.filter_logs)
        log_header.addWidget(self.log_filter)

        btn_copy = QPushButton("Copy")
        btn_copy.clicked.connect(self.copy_log)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_log)
        self.btn_toggle_log = QPushButton("Hide Log")
        self.btn_toggle_log.clicked.connect(self.toggle_log_visibility)

        log_header.addWidget(btn_copy)
        log_header.addWidget(btn_clear)
        log_header.addWidget(self.btn_toggle_log)
        log_layout.addLayout(log_header)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(130)
        log_layout.addWidget(self.log_box)

        main_layout.addWidget(log_card)

        self.all_log_lines: list[str] = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(main_widget)
        self.setCentralWidget(scroll)

    def get_app_key(self) -> str:
        return os.getenv("DROPBOX_APP_KEY", "").strip()

    def is_logged_in(self) -> bool:
        return bool(self.current_refresh_token or self.current_access_token)

    def update_account_ui(self):
        logged_in = self.is_logged_in()
        if logged_in:
            display_name = self.current_user_name or "Connected User"
            email = self.current_user_email or "OAuth Account"
            self.account_name_label.setText(f"👤 {display_name}")
            self.account_sub_label.setText(email)
            self.account_sub_label.setStyleSheet("font-size: 10px; color: #94a3b8;")
            self.set_auth_badge("● Connected", "connected")
            self.btn_oauth_login.setText("🔄  Switch")
            self.btn_oauth_login.setProperty("class", "btn-secondary")
            self.btn_oauth_login.style().unpolish(self.btn_oauth_login)
            self.btn_oauth_login.style().polish(self.btn_oauth_login)
            self.btn_logout.setVisible(True)
            self.login_banner.setVisible(False)
        else:
            self.account_name_label.setText("No Dropbox account connected")
            self.account_sub_label.setText("Sign in to your Dropbox account")
            self.account_sub_label.setStyleSheet("font-size: 10px; color: #94a3b8;")
            self.set_auth_badge("○ Not Logged In", "neutral")
            self.btn_oauth_login.setText("🌐  Log In")
            self.btn_oauth_login.setProperty("class", "btn-primary")
            self.btn_oauth_login.style().unpolish(self.btn_oauth_login)
            self.btn_oauth_login.style().polish(self.btn_oauth_login)
            self.btn_logout.setVisible(False)
            self.login_banner.setVisible(True)

        self.update_feature_enabled_state()

    def update_feature_enabled_state(self):
        if not hasattr(self, "btn_recent_links") or self.btn_recent_links is None:
            return

        logged_in = self.is_logged_in()
        is_running = self._is_running or is_thread_running(self.download_thread)
        is_scanning = is_thread_running(self.scan_thread)

        if not logged_in:
            # Strictly disable all operational features until user signs in
            self.target_card.setEnabled(False)
            self.tree_card.setEnabled(False)
            self.url_input.setEnabled(False)
            self.url_input.setPlaceholderText("Please log in first to enter a Dropbox link...")
            self.btn_recent_links.setEnabled(False)
            self.btn_paste_url.setEnabled(False)
            self.btn_clear_url.setEnabled(False)
            self.btn_scan_url.setEnabled(False)
            self.destination_input.setEnabled(False)
            self.btn_browse.setEnabled(False)
            self.btn_open_folder.setEnabled(False)
            self.check_skip_existing.setEnabled(False)
            if hasattr(self, "check_verify_integrity"):
                self.check_verify_integrity.setEnabled(False)
            if hasattr(self, "check_auto_repair"):
                self.check_auto_repair.setEnabled(False)
            if hasattr(self, "btn_verify_files"):
                self.btn_verify_files.setEnabled(False)
            self.tree_widget.setEnabled(False)
            self.btn_select_all.setEnabled(False)
            self.btn_deselect_all.setEnabled(False)
            self.btn_expand_all.setEnabled(False)
            self.btn_collapse_all.setEnabled(False)
            self.show_empty_tree_placeholder()
            self.set_selection_summary("(Sign in required)", "neutral")
            self.set_status_badge("○ Login Required", "neutral")
        else:
            active = is_running or is_scanning
            self.target_card.setEnabled(not is_running)
            self.tree_card.setEnabled(not is_running)
            self.url_input.setEnabled(not active)
            self.url_input.setPlaceholderText("https://www.dropbox.com/scl/fo/... or https://www.dropbox.com/sh/...")
            self.btn_recent_links.setEnabled(not active)
            self.btn_paste_url.setEnabled(not active)
            self.btn_clear_url.setEnabled(not active)
            self.btn_scan_url.setEnabled(not active)
            self.destination_input.setEnabled(not is_running)
            self.btn_browse.setEnabled(not is_running)
            self.btn_open_folder.setEnabled(not is_running)
            self.check_skip_existing.setEnabled(not is_running)
            if hasattr(self, "check_verify_integrity"):
                self.check_verify_integrity.setEnabled(not is_running)
            if hasattr(self, "check_auto_repair"):
                self.check_auto_repair.setEnabled(not is_running)
            self.tree_widget.setEnabled(not is_running)
            has_items = False
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item and item.data(0, Qt.ItemDataRole.UserRole) is not None:
                    has_items = True
                    break

            can_act_tree = not is_running and not is_scanning and has_items
            self.btn_select_all.setEnabled(can_act_tree)
            self.btn_deselect_all.setEnabled(can_act_tree)
            self.btn_expand_all.setEnabled(can_act_tree)
            self.btn_collapse_all.setEnabled(can_act_tree)
            if not active:
                curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
                if not any(k in curr.lower() for k in ("completed", "error", "stopped")):
                    self.set_status_badge("● Ready", "ready")

            # Refresh placeholder item if tree is in empty placeholder state
            if self.tree_widget.topLevelItemCount() == 1:
                item = self.tree_widget.topLevelItem(0)
                if item and item.data(0, Qt.ItemDataRole.UserRole) is None:
                    self.show_empty_tree_placeholder()
                    if not self.url_input.text().strip():
                        self.set_selection_summary("(Paste link above to inspect folders)", "neutral")

        self.update_download_button_state()

    def update_download_button_state(self):
        if (
            not hasattr(self, "start_button")
            or not hasattr(self, "pause_button")
            or not hasattr(self, "stop_button")
            or self.start_button is None
            or self.pause_button is None
            or self.stop_button is None
        ):
            return

        logged_in = self.is_logged_in()
        is_running = self._is_running or is_thread_running(self.download_thread)
        is_scanning = is_thread_running(self.scan_thread)

        if is_running:
            self.start_button.setVisible(False)
            if hasattr(self, "btn_verify_files"):
                self.btn_verify_files.setVisible(False)
            self.pause_button.setVisible(True)
            self.stop_button.setVisible(True)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            return

        # Not running -> Hide pause and stop, show start button
        self.pause_button.setVisible(False)
        self.stop_button.setVisible(False)
        self.start_button.setVisible(True)
        if hasattr(self, "btn_verify_files"):
            self.btn_verify_files.setVisible(True)

        if not logged_in:
            self.start_button.setEnabled(False)
            self.start_button.setText("🔒  Log In to Start")
            self.start_button.setToolTip("Please sign in to Dropbox to enable downloading.")
            if hasattr(self, "btn_verify_files"):
                self.btn_verify_files.setEnabled(False)
            return

        if is_scanning:
            self.start_button.setEnabled(False)
            self.start_button.setText("⏳  Loading Folders...")
            self.start_button.setToolTip("Scanning Dropbox shared link hierarchy...")
            if hasattr(self, "btn_verify_files"):
                self.btn_verify_files.setEnabled(False)
            return

        url = self.url_input.text().strip()
        has_link = bool(url and ("dropbox.com" in url) and ("http://" in url or "https://" in url))

        info = self.get_tree_selection_info()
        has_tree = info.get("has_tree_items", False)
        selected_count = info.get("selected_file_count", 0)

        can_verify = bool(has_link and has_tree and selected_count > 0)
        if hasattr(self, "btn_verify_files"):
            self.btn_verify_files.setEnabled(can_verify)
            if can_verify:
                self.btn_verify_files.setText(f"🔍  Verify Files ({selected_count})")
            else:
                self.btn_verify_files.setText("🔍  Verify Files")

        if not has_link:
            self.start_button.setEnabled(False)
            self.start_button.setText("📋  Paste Link & Select Files to Start")
            self.start_button.setToolTip("Paste a Dropbox shared link above to get started.")
        elif not has_tree:
            self.start_button.setEnabled(False)
            self.start_button.setText("🔍  Load Folders to Select Files")
            self.start_button.setToolTip("Click 'Load Folders' (or press Enter) to inspect files.")
        elif selected_count == 0:
            self.start_button.setEnabled(False)
            self.start_button.setText("☑  Select Files to Start")
            self.start_button.setToolTip("Check at least one file or folder in the tree above to start download.")
        else:
            self.start_button.setEnabled(True)
            self.start_button.setText(f"▶  Start Download ({selected_count} file{'s' if selected_count != 1 else ''})")
            self.start_button.setToolTip(f"Download {selected_count} selected files to local destination")

    def toggle_pause_download(self):
        if self.worker:
            self.worker.toggle_pause()

    def on_download_paused_changed(self, is_paused: bool):
        self.is_download_paused = is_paused
        if is_paused:
            self.pause_button.setText("▶  Resume Download")
            self.pause_button.setProperty("class", "btn-resume")
            st = self.pause_button.style()
            if st is not None:
                st.unpolish(self.pause_button)
                st.polish(self.pause_button)
            self.set_status_badge("⏸ Paused", "warning")
            self.val_speed.setText("Paused")
            self.add_log("⏸ Download paused by user.")
        else:
            self.pause_button.setText("⏸  Pause Download")
            self.pause_button.setProperty("class", "btn-pause")
            st = self.pause_button.style()
            if st is not None:
                st.unpolish(self.pause_button)
                st.polish(self.pause_button)
            self.set_status_badge("● Downloading...", "running")
            self.add_log("▶ Download resumed.")

    def add_recent_link(self, url: str, title: str = "", item_count: int = 0):
        url = url.strip()
        if not url or "dropbox.com" not in url:
            return

        junk_titles = {"h", "fo", "fi", "sh", "scl", "dl", "dropbox folder", "dropboxfolder", ""}
        clean_title = (title or "").strip()
        if clean_title.lower() in junk_titles:
            clean_title = ""

        existing = next((item for item in self.recent_links if item.get("url") == url), None)

        if not clean_title:
            # 1. Prefer existing recent title if it has a real root folder name
            if existing and existing.get("title") and existing.get("title").strip().lower() not in junk_titles:
                clean_title = existing.get("title").strip()
            # 2. Check current_root_name on MainWindow
            elif hasattr(self, "current_root_name") and self.current_root_name and self.current_root_name.strip().lower() not in junk_titles:
                clean_title = self.current_root_name.strip()
            # 3. Check tree widget top item
            elif hasattr(self, "tree_widget") and self.tree_widget.topLevelItemCount() > 0:
                top = self.tree_widget.topLevelItem(0)
                if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                    raw = top.data(3, Qt.ItemDataRole.UserRole) or ""
                    if raw and raw.strip().lower() not in junk_titles:
                        clean_title = raw.strip()
            # 4. Try extracting folder name from URL path
            if not clean_title:
                clean_title = extract_folder_name_from_url(url)
            # 5. Fallback
            if not clean_title:
                clean_title = "Dropbox Folder"

        if item_count == 0 and existing and existing.get("item_count", 0) > 0:
            item_count = existing.get("item_count", 0)

        now = time.time()
        date_str = time.strftime("%b %d, %H:%M", time.localtime(now))

        filtered = [item for item in self.recent_links if item.get("url") != url]
        new_item = {
            "url": url,
            "title": clean_title,
            "item_count": item_count,
            "timestamp": now,
            "date_str": date_str,
        }
        self.recent_links = [new_item] + filtered
        self.recent_links = self.recent_links[:15]
        self.save_settings()
        self.update_recent_links_ui()

    def update_recent_links_ui(self):
        if (
            not hasattr(self, "recent_chips_layout")
            or not hasattr(self, "recent_chips_container")
            or self.recent_chips_layout is None
            or self.recent_chips_container is None
        ):
            return

        while self.recent_chips_layout.count():
            child = self.recent_chips_layout.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.deleteLater()

        if not self.recent_links:
            self.recent_chips_container.setVisible(False)
            return

        lbl = QLabel("Recent:")
        lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 600; padding-right: 2px;")
        self.recent_chips_layout.addWidget(lbl)

        for item in self.recent_links[:4]:
            title = item.get("title") or "Dropbox Folder"
            display_name = (title[:22] + "…") if len(title) > 24 else title

            chip_btn = QPushButton(f"📁 {display_name}")
            chip_btn.setProperty("class", "recent-chip")
            chip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tooltip_txt = f"📁 Root Folder: {title}\n🔗 {item.get('url', '')}\n📅 Saved: {item.get('date_str', '')}"
            if item.get("item_count"):
                tooltip_txt += f"\n📊 {item.get('item_count')} items discovered"
            chip_btn.setToolTip(tooltip_txt)

            chip_url = item.get("url", "")
            chip_btn.clicked.connect(lambda _, u=chip_url: self.load_recent_link(u))
            self.recent_chips_layout.addWidget(chip_btn)

        if len(self.recent_links) > 4:
            more_btn = QPushButton(f"⋯ All ({len(self.recent_links)})")
            more_btn.setProperty("class", "recent-chip")
            more_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            more_btn.setToolTip("View all recent links in dropdown")
            more_btn.clicked.connect(self.show_recent_links_menu)
            self.recent_chips_layout.addWidget(more_btn)

        self.recent_chips_layout.addStretch()
        self.recent_chips_container.setVisible(True)

    def show_recent_links_menu(self):
        if not self.is_logged_in():
            self.prompt_login_required("view recent links")
            return

        menu = QMenu(self)
        if not self.recent_links:
            empty_act = menu.addAction("No recent links saved")
            empty_act.setEnabled(False)
        else:
            for item in self.recent_links:
                title = item.get("title") or "Dropbox Folder"
                url = item.get("url", "")
                cnt = item.get("item_count")
                cnt_txt = f"  ({cnt} items)" if cnt else ""
                date_txt = f"  •  {item.get('date_str', '')}" if item.get("date_str") else ""
                short_url = url[:60] + ("..." if len(url) > 60 else "")
                action_text = f"📁 {title}{cnt_txt}{date_txt}\n    {short_url}"
                act = menu.addAction(action_text)
                act.triggered.connect(lambda _, u=url: self.load_recent_link(u))

            menu.addSeparator()
            clear_act = menu.addAction("🗑  Clear Recent Links History")
            clear_act.triggered.connect(self.clear_recent_links)

        if hasattr(self, "btn_recent_links") and self.btn_recent_links is not None:
            menu.exec(self.btn_recent_links.mapToGlobal(self.btn_recent_links.rect().bottomLeft()))
        else:
            menu.exec(QCursor.pos())

    def load_recent_link(self, url: str):
        if not self.is_logged_in():
            self.prompt_login_required("load this link")
            return
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            self.auto_scan_timer.stop()
        item = next((it for it in self.recent_links if it.get("url") == url), None)
        if item and item.get("title"):
            self.current_root_name = item.get("title")
        self.url_input.blockSignals(True)
        self.url_input.setText(url)
        self.url_input.blockSignals(False)
        self.start_scan()

    def clear_recent_links(self):
        self.recent_links = []
        self.save_settings()
        self.update_recent_links_ui()
        self.add_log("Recent links history cleared.")

    def prompt_login_required(self, action_desc: str = "use this feature"):
        confirmed = ModernMessageBox.question(
            self,
            "Dropbox Login Required",
            f"You must sign into your Dropbox account to {action_desc}.\n\n"
            "All folder scanning, selection, and download features are disabled until you sign in.\n\n"
            "Would you like to log in with Dropbox now?",
            yes_text="Log In with Dropbox",
            no_text="Cancel",
        )
        if confirmed:
            self.login_with_dropbox()

    def load_settings(self):
        saved_dest = str(self.settings.value("destination", str(Path.home() / "Downloads")))
        if saved_dest:
            self.destination_input.setText(saved_dest)

        skip_raw = self.settings.value("skip_existing", True)
        self.check_skip_existing.setChecked(str(skip_raw).lower() in ("true", "1"))

        if hasattr(self, "check_verify_integrity"):
            verify_raw = self.settings.value("verify_integrity", True)
            self.check_verify_integrity.setChecked(str(verify_raw).lower() in ("true", "1"))

        if hasattr(self, "check_auto_repair"):
            repair_raw = self.settings.value("auto_repair", True)
            self.check_auto_repair.setChecked(str(repair_raw).lower() in ("true", "1"))

        recent_raw = self.settings.value("recent_links_json", "")
        if recent_raw:
            try:
                loaded = json.loads(str(recent_raw))
                if isinstance(loaded, list):
                    junk_titles = {"h", "fo", "fi", "sh", "scl", "dl", ""}
                    for it in loaded:
                        t = (it.get("title") or "").strip()
                        if t.lower() in junk_titles:
                            it["title"] = extract_folder_name_from_url(it.get("url", "")) or "Dropbox Folder"
                    self.recent_links = loaded
                else:
                    self.recent_links = []
            except Exception:
                self.recent_links = []
        else:
            self.recent_links = []
        self.update_recent_links_ui()

        saved_refresh = str(self.settings.value("oauth_refresh_token", "")).strip()
        saved_access = str(self.settings.value("oauth_access_token", "")).strip()
        saved_name = str(self.settings.value("user_name", "")).strip()
        saved_email = str(self.settings.value("user_email", "")).strip()

        self.settings.remove("token")

        if saved_refresh or saved_access:
            self.current_refresh_token = saved_refresh
            self.current_access_token = saved_access
            self.current_user_name = saved_name
            self.current_user_email = saved_email
            self.update_account_ui()
            QTimer.singleShot(400, self.verify_saved_session)
        else:
            self.update_account_ui()
            self.add_log("🔒 Welcome! Please sign into your Dropbox account above to unlock features.")

    def cleanup_auth_thread(self):
        if self.auth_worker is not None:
            try:
                self.auth_worker.cancel()
            except Exception:
                pass
            self.auth_worker = None
        if self.auth_thread is not None:
            if is_thread_running(self.auth_thread):
                try:
                    self.auth_thread.quit()
                    self.auth_thread.wait(200)
                except Exception:
                    pass
            self.auth_thread = None

    def cleanup_verify_thread(self):
        if self.verify_worker is not None:
            self.verify_worker = None
        if self.verify_thread is not None:
            if is_thread_running(self.verify_thread):
                try:
                    self.verify_thread.quit()
                    self.verify_thread.wait(200)
                except Exception:
                    pass
            self.verify_thread = None

    def cleanup_download_thread(self):
        if self.worker is not None:
            try:
                self.worker.stop()
            except Exception:
                pass
            self.worker = None
        if self.download_thread is not None:
            if is_thread_running(self.download_thread):
                try:
                    self.download_thread.quit()
                    self.download_thread.wait(200)
                except Exception:
                    pass
            self.download_thread = None

    def cleanup_scan_thread(self):
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            try:
                self.auto_scan_timer.stop()
            except Exception:
                pass
        if self.scan_worker is not None:
            try:
                self.scan_worker.cancel()
            except Exception:
                pass
            self.scan_worker = None
        if self.scan_thread is not None:
            if is_thread_running(self.scan_thread):
                try:
                    self.scan_thread.quit()
                    self.scan_thread.wait(200)
                except Exception:
                    pass
            self.scan_thread = None

    @Slot(str, str)
    def on_verify_finished(self, name: str, email: str):
        if name:
            self.current_user_name = name
        if email:
            self.current_user_email = email
        self.save_settings()
        self.update_account_ui()
        self.add_log(f"🔑 Restored session: {self.current_user_name} <{self.current_user_email}>")

    @Slot(str)
    def on_verify_expired(self, exc_msg: str):
        title, msg = parse_friendly_error(exc_msg)
        self.add_log(f"⚠ Session expired: {msg.splitlines()[0]} Signing out...")
        self.current_access_token = ""
        self.current_refresh_token = ""
        self.current_user_name = ""
        self.current_user_email = ""
        self.save_settings()
        self.update_account_ui()

    @Slot(str)
    def on_verify_failed(self, exc_msg: str):
        title, msg = parse_friendly_error(exc_msg)
        self.add_log(f"⚠ Session check: {msg.splitlines()[0]} Please sign in again if needed.")

    @Slot(str)
    def on_auth_status(self, msg: str):
        self.add_log(f"ℹ {msg}")

    def verify_saved_session(self):
        if not self.is_logged_in():
            return

        self.cleanup_verify_thread()
        t = QThread()
        w = SessionVerifyWorker(
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
        )
        w.moveToThread(t)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.expired.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_session_verify_thread_finished(thread_ref=t):
            if getattr(self, "verify_thread", None) is thread_ref:
                self.verify_thread = None
                self.verify_worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_session_verify_thread_finished)

        self.verify_thread = t
        self.verify_worker = w
        self._active_workers[t] = w

        w.finished.connect(self.on_verify_finished)
        w.expired.connect(self.on_verify_expired)
        w.failed.connect(self.on_verify_failed)

        t.started.connect(w.run)
        t.start()

    def save_settings(self):
        self.settings.setValue("destination", self.destination_input.text().strip())
        if hasattr(self, "check_skip_existing"):
            self.settings.setValue("skip_existing", self.check_skip_existing.isChecked())
        if hasattr(self, "check_verify_integrity"):
            self.settings.setValue("verify_integrity", self.check_verify_integrity.isChecked())
        if hasattr(self, "check_auto_repair"):
            self.settings.setValue("auto_repair", self.check_auto_repair.isChecked())

        if self.current_refresh_token:
            self.settings.setValue("oauth_refresh_token", self.current_refresh_token)
        else:
            self.settings.remove("oauth_refresh_token")

        if self.current_access_token:
            self.settings.setValue("oauth_access_token", self.current_access_token)
        else:
            self.settings.remove("oauth_access_token")

        if self.current_user_name:
            self.settings.setValue("user_name", self.current_user_name)
        else:
            self.settings.remove("user_name")

        if self.current_user_email:
            self.settings.setValue("user_email", self.current_user_email)
        else:
            self.settings.remove("user_email")

        if self.recent_links:
            self.settings.setValue("recent_links_json", json.dumps(self.recent_links))
        else:
            self.settings.remove("recent_links_json")

    def login_with_dropbox(self):
        app_key = self.get_app_key()

        if not app_key:
            key, ok = ModernInputDialog.get_text(
                self,
                title="Dropbox App Key Required",
                heading="Dropbox App Key (Client ID) Required",
                message=(
                    "DROPBOX_APP_KEY was not found in your .env file.\n\n"
                    "Please enter your Dropbox App Key from https://www.dropbox.com/developers/apps:\n"
                    "(To avoid this prompt in the future, set DROPBOX_APP_KEY=... in your .env file)"
                ),
                placeholder="Paste your Dropbox App Key here...",
                confirm_text="Continue",
            )
            if not ok or not key:
                return
            app_key = key

        try:
            flow = dropbox.DropboxOAuth2FlowNoRedirect(
                consumer_key=app_key,
                consumer_secret=None,
                use_pkce=True,
                token_access_type="offline",
            )
            authorize_url = flow.start()
            webbrowser.open(authorize_url)

            code, ok = ModernInputDialog.get_text(
                self,
                title="Authorize Dropbox Account",
                heading="Authorize Your Dropbox Account",
                message=(
                    "Your browser has opened the Dropbox authorization page:\n\n"
                    "1. Sign into ANY Dropbox account in the opened browser window.\n"
                    "2. Click 'Allow' to grant folder read permissions.\n"
                    "3. Copy the authorization code shown on screen and paste it below:"
                ),
                placeholder="Paste Dropbox authorization code here...",
                confirm_text="Authorize & Sign In",
            )
            if not ok or not code:
                return

            # Show modern loader dialog immediately
            loading_dialog = ModernLoadingDialog(
                parent=self,
                title="Connecting to Dropbox",
                heading="Signing into Dropbox...",
                status="Exchanging authorization code with Dropbox API...",
            )

            self.set_status_badge("⏳ Signing In...", "running")
            self.add_log("⏳ Exchanging OAuth authorization code with Dropbox API...")
            self.btn_oauth_login.setEnabled(False)
            self.btn_oauth_login.setText("⏳ Signing in...")
            self.btn_banner_login.setEnabled(False)
            self.btn_banner_login.setText("⏳ Signing in...")

            self.cleanup_auth_thread()
            t = QThread()
            w = AuthWorker(flow=flow, code=code, app_key=app_key)
            w.moveToThread(t)

            w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
            w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
            t.finished.connect(w.deleteLater)
            t.finished.connect(t.deleteLater)

            def _on_auth_thread_finished(thread_ref=t):
                if getattr(self, "auth_thread", None) is thread_ref:
                    self.auth_thread = None
                    self.auth_worker = None
                self._active_workers.pop(thread_ref, None)

            t.finished.connect(_on_auth_thread_finished)

            self.auth_thread = t
            self.auth_worker = w
            self._active_workers[t] = w

            w.status.connect(loading_dialog.set_status)
            w.status.connect(self.on_auth_status)
            w.progress.connect(loading_dialog.set_progress)
            w.finished.connect(loading_dialog.on_auth_finished)
            w.failed.connect(loading_dialog.on_auth_failed)
            loading_dialog.cancelled.connect(w.cancel)

            t.started.connect(w.run)
            QTimer.singleShot(20, t.start)

            loading_dialog.exec()

            if loading_dialog.auth_success:
                self.current_access_token = loading_dialog.auth_data.get("access_token", "")
                self.current_refresh_token = loading_dialog.auth_data.get("refresh_token", "")
                self.current_user_name = loading_dialog.auth_data.get("user_name", "")
                self.current_user_email = loading_dialog.auth_data.get("user_email", "")

                self.save_settings()
                self.update_account_ui()
                self.add_log(
                    f"✓ Successfully authenticated as {self.current_user_name} "
                    f"<{self.current_user_email}> via Dropbox OAuth!"
                )
                self.set_status_badge("● Connected", "success")
                QTimer.singleShot(
                    2500,
                    lambda: self.set_status_badge("● Ready", "ready")
                    if self.is_logged_in() and not is_thread_running(self.download_thread)
                    else None,
                )

                if self.url_input.text().strip():
                    self.start_scan()
            elif loading_dialog.auth_error:
                self.update_account_ui()
                title, friendly = parse_friendly_error(loading_dialog.auth_error)
                self.add_log(f"✕ Login failed: {title} ({friendly.splitlines()[0]})")
                ModernMessageBox.error(
                    self,
                    f"Login Failed: {title}",
                    f"Could not complete Dropbox authorization:\n\n{friendly}",
                )
            elif loading_dialog.is_cancelled:
                self.update_account_ui()
                self.add_log("⚠ Login was cancelled by user.")
            else:
                self.update_account_ui()

        except Exception as exc:
            self.update_account_ui()
            title, friendly = parse_friendly_error(exc)
            ModernMessageBox.error(
                self,
                f"Login Failed: {title}",
                f"Could not initialize Dropbox authorization:\n\n{friendly}",
            )

    def logout_dropbox(self):
        confirmed = ModernMessageBox.question(
            self,
            "Sign Out",
            "Are you sure you want to sign out of your Dropbox account?\n\n"
            "All folder scanning, selection, and download features will be locked until you sign in again.",
            yes_text="Sign Out",
            no_text="Cancel",
            is_destructive=True,
        )
        if confirmed:
            self.current_access_token = ""
            self.current_refresh_token = ""
            self.current_user_name = ""
            self.current_user_email = ""
            self.link_password = ""
            self.settings.remove("oauth_refresh_token")
            self.settings.remove("oauth_access_token")
            self.settings.remove("user_name")
            self.settings.remove("user_email")
            self.settings.remove("token")
            self.clear_url_and_tree()
            self.update_account_ui()
            self.add_log("🔒 Logged out of Dropbox account. All features are now disabled.")

    def toggle_log_visibility(self):
        if self.log_box.isVisible():
            self.log_box.setVisible(False)
            self.btn_toggle_log.setText("Show Log")
        else:
            self.log_box.setVisible(True)
            self.btn_toggle_log.setText("Hide Log")

    def show_empty_tree_placeholder(self):
        self._updating_tree = True
        self.tree_widget.clear()
        if not self.is_logged_in():
            placeholder = QTreeWidgetItem(
                self.tree_widget,
                ["🔒 Please log in to Dropbox above to inspect and download folders", "—", "—"]
            )
        else:
            placeholder = QTreeWidgetItem(
                self.tree_widget,
                ["Paste a Dropbox link above and click '🔍 Load Folders'", "—", "—"]
            )
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder.setForeground(0, QColor("#64748b"))
        placeholder.setForeground(1, QColor("#64748b"))
        placeholder.setForeground(2, QColor("#64748b"))
        self._updating_tree = False

    def on_url_text_changed(self, text: str):
        self.update_download_button_state()
        text = text.strip()
        if "dropbox.com" in text and ("http://" in text or "https://" in text):
            self.auto_scan_timer.start(700)

    def auto_scan_if_valid(self):
        url = self.url_input.text().strip()
        if "dropbox.com" in url and ("http://" in url or "https://" in url) and self.is_logged_in():
            self.start_scan()

    def paste_url(self):
        if not self.is_logged_in():
            self.prompt_login_required("paste and inspect shared links")
            return
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            self.auto_scan_timer.stop()
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.blockSignals(True)
            self.url_input.setText(text)
            self.url_input.blockSignals(False)
            self.start_scan()

    def clear_url_and_tree(self):
        self.url_input.clear()
        self.link_password = ""
        self.show_empty_tree_placeholder()
        if self.is_logged_in():
            self.selection_summary_label.setText("(Paste link above to inspect folders)")
        else:
            self.selection_summary_label.setText("(Sign in required)")
        self.update_download_button_state()

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Local Download Destination",
            self.destination_input.text().strip() or str(Path.home()),
        )
        if folder:
            self.destination_input.setText(folder)
            self.save_settings()

    def open_destination_folder(self):
        dest = self.destination_input.text().strip()
        if not dest:
            ModernMessageBox.information(self, "Notice", "Download destination folder does not exist yet.")
            return

        target_path = Path(dest)
        if target_path.exists():
            os.startfile(str(target_path))
        else:
            ModernMessageBox.information(self, "Notice", "Download destination folder does not exist yet.")

    # ==========================================================================
    # Folder Scanning & Tree Population
    # ==========================================================================
    def start_scan(self):
        self.cleanup_scan_thread()

        if not self.is_logged_in():
            self.prompt_login_required("inspect folder contents")
            return

        url = self.url_input.text().strip()
        password = (self.link_password or "").strip()

        if not url:
            ModernMessageBox.warning(self, "Missing Link", "Please enter or paste a valid Dropbox shared link to inspect folders.")
            self.url_input.setFocus()
            return

        self.btn_scan_url.setEnabled(False)
        self.btn_scan_url.setText("⏳ Loading...")
        self.set_selection_summary("⏳ Scanning folder contents via Dropbox API...", "active")
        self.add_log(f"🔍 Inspecting folder hierarchy for: {url}")

        self.tree_widget.clear()
        loading_item = QTreeWidgetItem(self.tree_widget, ["⏳ Loading folders from Dropbox...", "", ""])
        loading_item.setFlags(loading_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        self.update_feature_enabled_state()
        self.update_download_button_state()

        t = QThread()
        w = ScanWorker(
            url=url,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            password=password,
        )
        w.moveToThread(t)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_scan_thread_finished(thread_ref=t):
            if getattr(self, "scan_thread", None) is thread_ref:
                self.scan_thread = None
                self.scan_worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_scan_thread_finished)

        self.scan_thread = t
        self.scan_worker = w
        self._active_workers[t] = w

        t.started.connect(w.run)
        w.status.connect(self.on_scan_status)
        w.finished.connect(self.on_scan_finished)
        w.failed.connect(self.on_scan_failed)

        t.start()

    @Slot(str)
    def on_scan_status(self, text: str):
        self.set_selection_summary(f"⏳ {text}", "active")

    def on_scan_finished(self, tree_dict: dict, root_name: str, entries: list):
        self.scan_thread = None
        self.scan_worker = None
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("🔍 Load Folders")

        self.current_root_name = root_name
        self._tree_items_data = entries
        self.populate_tree_widget(tree_dict, root_name)

        folders_count = sum(1 for e in entries if e.get("is_dir"))
        files_count = sum(1 for e in entries if not e.get("is_dir"))
        total_size = sum(e.get("size", 0) for e in entries if not e.get("is_dir"))

        self.add_log(f"✓ Found {len(entries)} items ({folders_count} folder(s), {files_count} file(s), {format_bytes(total_size)})")
        self.update_selection_summary()
        url = self.url_input.text().strip()
        self.add_recent_link(url, title=root_name, item_count=len(entries))
        self.update_feature_enabled_state()
        self.update_download_button_state()

    def on_scan_failed(self, error: str):
        self.scan_thread = None
        self.scan_worker = None
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("🔍 Load Folders")

        title, friendly_msg = parse_friendly_error(error)
        self.show_empty_tree_placeholder()
        self.set_selection_summary(f"⚠️ {title}", "error")
        self.add_log(f"⚠️ {title}: {friendly_msg.splitlines()[0]}")
        self.update_feature_enabled_state()
        self.update_download_button_state()

        if "password" in error.lower() or "access_denied" in error.lower():
            pwd, ok = ModernInputDialog.get_text(
                self,
                title="Password Protected Link",
                heading="Dropbox Link Password Required",
                message=(
                    "This Dropbox shared folder is protected with a password.\n\n"
                    "Please enter the password to inspect its contents:"
                ),
                placeholder="Enter folder link password...",
                is_password=True,
                confirm_text="Unlock & Load",
            )
            if ok and pwd:
                self.link_password = pwd.strip()
                self.start_scan()
                return
        else:
            ModernMessageBox.warning(self, title, friendly_msg)

    def populate_tree_widget(self, tree_dict: dict, root_name: str):
        self._updating_tree = True
        self.tree_widget.setUpdatesEnabled(False)
        try:
            self.tree_widget.clear()

            def add_item_recursive(parent_item: QTreeWidgetItem | None, node_data: dict[str, Any]):
                name = node_data["name"]
                is_dir = node_data["is_dir"]
                size: int = int(node_data.get("size") or 0)
                total_size: int = int(node_data.get("total_size") or size)
                children_count = len(node_data.get("children", {}))

                if is_dir:
                    icon_str = "📁 "
                    type_str = f"Folder ({children_count} items)" if children_count > 0 else "Folder"
                    size_str = format_bytes(total_size) if total_size > 0 else ""
                else:
                    type_str, icon_str = get_file_type_and_icon(name)
                    size_str = format_bytes(size) if size > 0 else "0 B"

                item = QTreeWidgetItem([f"{icon_str}{name}", type_str, size_str])
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(0, Qt.ItemDataRole.UserRole, node_data["path"])
                item.setData(1, Qt.ItemDataRole.UserRole, is_dir)
                item.setData(2, Qt.ItemDataRole.UserRole, size if not is_dir else total_size)
                item.setData(3, Qt.ItemDataRole.UserRole, name)
                item.setToolTip(0, f"{'Folder' if is_dir else 'File'}: {node_data['path'] or name}")

                if parent_item is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                for child_name, child_data in sorted(
                    node_data["children"].items(),
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0]))
                ):
                    add_item_recursive(item, child_data)

            if tree_dict["children"]:
                for child_name, child_data in sorted(
                    tree_dict["children"].items(),
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0]))
                ):
                    add_item_recursive(None, child_data)
            else:
                single_item = QTreeWidgetItem([f"📁 {root_name}", "Folder", ""])
                single_item.setCheckState(0, Qt.CheckState.Checked)
                single_item.setFlags(single_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                single_item.setData(0, Qt.ItemDataRole.UserRole, root_name)
                single_item.setData(1, Qt.ItemDataRole.UserRole, True)
                single_item.setData(2, Qt.ItemDataRole.UserRole, 0)
                single_item.setData(3, Qt.ItemDataRole.UserRole, root_name)
                single_item.setToolTip(0, f"Folder: {root_name}")
                self.tree_widget.addTopLevelItem(single_item)

            self.tree_widget.collapseAll()
        finally:
            self.tree_widget.setUpdatesEnabled(True)
            self._updating_tree = False
            self.update_selection_summary()
            self.update_feature_enabled_state()

    def _get_tree_items_between(self, item1: QTreeWidgetItem, item2: QTreeWidgetItem) -> list[QTreeWidgetItem]:
        """Return all visible tree items between item1 and item2 (inclusive) in top-to-bottom order."""
        all_visible: list[QTreeWidgetItem] = []
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            parent = item.parent()
            visible = not item.isHidden()
            while visible and parent:
                if not parent.isExpanded():
                    visible = False
                    break
                parent = parent.parent()
            if visible:
                all_visible.append(item)
            it += 1

        try:
            idx1 = all_visible.index(item1)
            idx2 = all_visible.index(item2)
        except ValueError:
            return [item2]

        start = min(idx1, idx2)
        end = max(idx1, idx2)
        return all_visible[start : end + 1]

    def set_items_checked(self, items: list[QTreeWidgetItem], state: Qt.CheckState):
        """Batch set check states on a list of items and propagate down/up properly."""
        if not items:
            return
        self._updating_tree = True
        try:
            for it in items:
                it.setCheckState(0, state)
                if bool(it.data(1, Qt.ItemDataRole.UserRole)):
                    self._propagate_check_down(it, state)
            for it in items:
                self._update_ancestors(it)
        finally:
            self._updating_tree = False
        self.update_selection_summary()

    def on_tree_shift_range_selected(self, anchor_item: QTreeWidgetItem, target_item: QTreeWidgetItem, is_checkbox: bool):
        """Handle Shift+Click range selection and update check states & row highlights."""
        items_range = self._get_tree_items_between(anchor_item, target_item)

        if is_checkbox:
            target_state = (
                Qt.CheckState.Unchecked
                if target_item.checkState(0) == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
        else:
            if anchor_item.checkState(0) == Qt.CheckState.Checked:
                target_state = Qt.CheckState.Checked
            else:
                target_state = (
                    Qt.CheckState.Checked
                    if target_item.checkState(0) == Qt.CheckState.Unchecked
                    else Qt.CheckState.Unchecked
                )

        self.tree_widget.clearSelection()
        for it in items_range:
            it.setSelected(True)
        self.tree_widget.setCurrentItem(target_item)

        self.set_items_checked(items_range, target_state)

    def on_tree_space_pressed(self):
        """Toggle check states for all currently selected items in the tree view."""
        selected = self.tree_widget.selectedItems()
        if not selected:
            curr = self.tree_widget.currentItem()
            if curr:
                selected = [curr]
        if not selected:
            return

        has_unchecked = any(it.checkState(0) != Qt.CheckState.Checked for it in selected)
        target_state = Qt.CheckState.Checked if has_unchecked else Qt.CheckState.Unchecked
        self.set_items_checked(selected, target_state)

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            return
        self.tree_widget._anchor_item = item
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir and item.childCount() > 0:
            pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
            rect = self.tree_widget.visualItemRect(item)
            if column != 0 or pos.x() > (rect.x() + 24):
                item.setExpanded(not item.isExpanded())
        elif not is_dir:
            pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
            rect = self.tree_widget.visualItemRect(item)
            if column != 0 or pos.x() > (rect.x() + 24):
                current_state = item.checkState(0)
                new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
                item.setCheckState(0, new_state)

    def show_tree_context_menu(self, point):
        item = self.tree_widget.itemAt(point)
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c1424;
                border: 1px solid #1e2d4a;
                border-radius: 8px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1e293b;
                margin: 4px 8px;
            }
        """)

        selected_items = self.tree_widget.selectedItems()
        is_multi = len(selected_items) > 1 and item in selected_items

        act_check_sel = None
        act_uncheck_sel = None
        act_only_sel = None

        if is_multi:
            act_check_sel = menu.addAction(f"☑ Check Selected ({len(selected_items)} items)")
            act_uncheck_sel = menu.addAction(f"☐ Deselect Selected ({len(selected_items)} items)")
            act_only_sel = menu.addAction(f"🎯 Select Only Selected ({len(selected_items)} items)")
            menu.addSeparator()

        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        raw_name = item.data(3, Qt.ItemDataRole.UserRole) or item.text(0)

        if not is_dir:
            act_only = menu.addAction(f"🎯 Select Only '{raw_name}'")
            is_checked = (item.checkState(0) == Qt.CheckState.Checked)
            act_toggle = menu.addAction(f"☐ Deselect '{raw_name}'" if is_checked else f"☑ Select '{raw_name}'")
            menu.addSeparator()
            act_select_all = menu.addAction("☑ Select All")
            act_deselect_all = menu.addAction("☐ Deselect All")

            action = menu.exec(self.tree_widget.viewport().mapToGlobal(point))
            if is_multi and action == act_check_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif is_multi and action == act_uncheck_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Unchecked)
            elif is_multi and action == act_only_sel:
                self.deselect_all_items()
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif action == act_only:
                self.deselect_all_items()
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_toggle:
                new_state = Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked
                item.setCheckState(0, new_state)
            elif action == act_select_all:
                self.select_all_items()
            elif action == act_deselect_all:
                self.deselect_all_items()
        else:
            act_only_folder = menu.addAction(f"🎯 Select Only '{raw_name}'")
            act_select_folder = menu.addAction(f"☑ Select All in '{raw_name}'")
            act_deselect_folder = menu.addAction(f"☐ Deselect All in '{raw_name}'")
            menu.addSeparator()
            act_expand = menu.addAction("📂 Expand Folder")
            act_collapse = menu.addAction("📁 Collapse Folder")
            menu.addSeparator()
            act_select_all = menu.addAction("☑ Select All")
            act_deselect_all = menu.addAction("☐ Deselect All")

            action = menu.exec(self.tree_widget.viewport().mapToGlobal(point))
            if is_multi and action == act_check_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif is_multi and action == act_uncheck_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Unchecked)
            elif is_multi and action == act_only_sel:
                self.deselect_all_items()
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif action == act_only_folder:
                self.deselect_all_items()
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_select_folder:
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_deselect_folder:
                item.setCheckState(0, Qt.CheckState.Unchecked)
            elif action == act_expand:
                item.setExpanded(True)
            elif action == act_collapse:
                item.setExpanded(False)
            elif action == act_select_all:
                self.select_all_items()
            elif action == act_deselect_all:
                self.deselect_all_items()

    def on_tree_item_expanded(self, item: QTreeWidgetItem):
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir:
            raw_name = item.data(3, Qt.ItemDataRole.UserRole)
            if raw_name:
                item.setText(0, f"📂 {raw_name}")
            self.on_tree_current_item_changed(item, None)

    def on_tree_item_collapsed(self, item: QTreeWidgetItem):
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir:
            raw_name = item.data(3, Qt.ItemDataRole.UserRole)
            if raw_name:
                item.setText(0, f"📁 {raw_name}")
            self.on_tree_current_item_changed(item, None)

    def on_tree_current_item_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None = None):
        if not current:
            return
        is_dir = bool(current.data(1, Qt.ItemDataRole.UserRole))
        raw_name = current.data(3, Qt.ItemDataRole.UserRole) or current.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "")
        if is_dir:
            child_count = current.childCount()
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            size_str = f" • {format_bytes(size)}" if size > 0 else ""
            status = "open — click to collapse" if current.isExpanded() else "closed — click to expand"
            self.tree_hint.setText(f"📁 Folder: {raw_name} ({child_count} items{size_str}) [{status}]")
            self.tree_hint.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 500;")
        else:
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            self.tree_hint.setText(f"📄 File: {raw_name} ({format_bytes(size) if size > 0 else '0 B'})")
            self.tree_hint.setStyleSheet("font-size: 11px; color: #94a3b8;")

    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != 0 or self._updating_tree:
            return

        self._updating_tree = True
        try:
            state = item.checkState(0)
            if state != Qt.CheckState.PartiallyChecked:
                self._propagate_check_down(item, state)

            self._update_ancestors(item)
        finally:
            self._updating_tree = False

        self.update_selection_summary()

    def _propagate_check_down(self, item: QTreeWidgetItem, state: Qt.CheckState):
        for i in range(item.childCount()):
            child = item.child(i)
            if child is not None:
                child.setCheckState(0, state)
                self._propagate_check_down(child, state)

    def _update_ancestors(self, item: QTreeWidgetItem):
        parent = item.parent()
        if not parent:
            return

        checked_count = 0
        partial_count = 0
        total = parent.childCount()

        for i in range(total):
            child = parent.child(i)
            if child is None:
                continue
            c_state = child.checkState(0)
            if c_state == Qt.CheckState.Checked:
                checked_count += 1
            elif c_state == Qt.CheckState.PartiallyChecked:
                partial_count += 1

        if checked_count == total:
            parent.setCheckState(0, Qt.CheckState.Checked)
        elif checked_count == 0 and partial_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        self._update_ancestors(parent)

    def select_all_items(self):
        self._updating_tree = True
        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            if top is not None:
                top.setCheckState(0, Qt.CheckState.Checked)
                self._propagate_check_down(top, Qt.CheckState.Checked)
        self._updating_tree = False
        self.update_selection_summary()

    def deselect_all_items(self):
        self._updating_tree = True
        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            if top is not None:
                top.setCheckState(0, Qt.CheckState.Unchecked)
                self._propagate_check_down(top, Qt.CheckState.Unchecked)
        self._updating_tree = False
        self.update_selection_summary()

    def update_selection_summary(self):
        total_files = 0
        selected_files = 0
        total_folders = 0
        selected_folders = 0
        selected_bytes = 0

        def count_recursive(item: QTreeWidgetItem | None):
            nonlocal total_files, selected_files, total_folders, selected_folders, selected_bytes
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
            state = item.checkState(0)
            size = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)

            if is_dir:
                total_folders += 1
                if state in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                    selected_folders += 1
            else:
                total_files += 1
                if state == Qt.CheckState.Checked:
                    selected_files += 1
                    selected_bytes += size

            for i in range(item.childCount()):
                count_recursive(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            count_recursive(self.tree_widget.topLevelItem(i))

        if total_files == 0 and total_folders == 0:
            self.selection_summary_label.setText("(No items scanned yet)")
            self.selection_summary_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        elif total_files == 0:
            folder_str = f"{selected_folders} of {total_folders} folder{'s' if total_folders != 1 else ''} selected"
            self.selection_summary_label.setText(folder_str)
            color = "#10b981" if selected_folders > 0 else "#94a3b8"
            self.selection_summary_label.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
        else:
            folder_str = f" ({selected_folders} folder{'s' if selected_folders != 1 else ''})" if selected_folders > 0 else ""
            summary_txt = f"{selected_files} of {total_files} file{'s' if total_files != 1 else ''} selected{folder_str}"
            if selected_bytes > 0:
                summary_txt += f" • {format_bytes(selected_bytes)}"
            self.selection_summary_label.setText(summary_txt)
            color = "#10b981" if selected_files > 0 or selected_folders > 0 else "#94a3b8"
            self.selection_summary_label.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")

        self.update_download_button_state()

    def get_tree_selection_info(self) -> dict[str, Any]:
        selected_files = set()
        deselected_files = set()
        selected_folders = set()
        deselected_folders = set()
        total_files = 0
        total_selected_files = 0
        has_tree_items = False
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            if top_item is not None and top_item.data(0, Qt.ItemDataRole.UserRole) is not None:
                has_tree_items = True
                break

        def traverse(item: QTreeWidgetItem | None, parent_path=""):
            nonlocal total_files, total_selected_files
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
            raw_name = item.data(3, Qt.ItemDataRole.UserRole) or item.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "").strip()
            item_path = item.data(0, Qt.ItemDataRole.UserRole) or ""

            current_path = f"{parent_path}/{raw_name}".strip("/") if parent_path else raw_name
            state = item.checkState(0)

            if is_dir:
                if state == Qt.CheckState.Checked:
                    if item_path:
                        selected_folders.add(item_path)
                    selected_folders.add(current_path)
                elif state == Qt.CheckState.Unchecked:
                    if item_path:
                        deselected_folders.add(item_path)
                    deselected_folders.add(current_path)

                for i in range(item.childCount()):
                    traverse(item.child(i), current_path)
            else:
                total_files += 1
                if state == Qt.CheckState.Checked:
                    total_selected_files += 1
                    if item_path:
                        selected_files.add(item_path)
                    selected_files.add(current_path)
                else:
                    if item_path:
                        deselected_files.add(item_path)
                    deselected_files.add(current_path)

        for i in range(self.tree_widget.topLevelItemCount()):
            traverse(self.tree_widget.topLevelItem(i))

        # Check if exactly 1 folder hierarchy is selected in tree
        checked_top_folders = []
        checked_top_files = []
        partially_checked_folders = []
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            if top_item is None or top_item.data(0, Qt.ItemDataRole.UserRole) is None:
                continue
            is_dir = bool(top_item.data(1, Qt.ItemDataRole.UserRole))
            state = top_item.checkState(0)
            if state == Qt.CheckState.Checked:
                if is_dir:
                    checked_top_folders.append(top_item)
                else:
                    checked_top_files.append(top_item)
            elif state == Qt.CheckState.PartiallyChecked and is_dir:
                partially_checked_folders.append(top_item)

        single_selected_folder = ""
        if len(checked_top_files) == 0:
            if len(checked_top_folders) == 1 and len(partially_checked_folders) == 0:
                f_item = checked_top_folders[0]
                single_selected_folder = (
                    f_item.data(0, Qt.ItemDataRole.UserRole)
                    or f_item.data(3, Qt.ItemDataRole.UserRole)
                    or ""
                )
            elif len(checked_top_folders) == 0 and len(partially_checked_folders) == 1:
                curr = partially_checked_folders[0]
                while curr is not None:
                    c_checked_f = []
                    c_checked_files = []
                    c_partial = []
                    for c_idx in range(curr.childCount()):
                        ch = curr.child(c_idx)
                        if ch is None:
                            continue
                        ch_dir = bool(ch.data(1, Qt.ItemDataRole.UserRole))
                        ch_st = ch.checkState(0)
                        if ch_st == Qt.CheckState.Checked:
                            if ch_dir:
                                c_checked_f.append(ch)
                            else:
                                c_checked_files.append(ch)
                        elif ch_st == Qt.CheckState.PartiallyChecked and ch_dir:
                            c_partial.append(ch)
                    if len(c_checked_files) == 0 and len(c_checked_f) == 1 and len(c_partial) == 0:
                        single_selected_folder = (
                            c_checked_f[0].data(0, Qt.ItemDataRole.UserRole)
                            or c_checked_f[0].data(3, Qt.ItemDataRole.UserRole)
                            or ""
                        )
                        break
                    elif len(c_checked_files) == 0 and len(c_checked_f) == 0 and len(c_partial) == 1:
                        curr = c_partial[0]
                    else:
                        break

        return {
            "selected_files": selected_files,
            "deselected_files": deselected_files,
            "selected_folders": selected_folders,
            "deselected_folders": deselected_folders,
            "single_selected_folder": single_selected_folder,
            "total_files": total_files,
            "selected_file_count": total_selected_files,
            "has_tree_items": has_tree_items,
        }

    # ==========================================================================
    # Download Execution
    # ==========================================================================
    @Slot(str)
    def add_log(self, text: str):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {text}"
        self.all_log_lines.append(formatted)
        filter_text = self.log_filter.text().strip().lower()
        if not filter_text or filter_text in formatted.lower():
            self.log_box.appendPlainText(formatted)
            self.log_box.moveCursor(QTextCursor.MoveOperation.End)

    def filter_logs(self, text: str):
        filter_text = text.strip().lower()
        self.log_box.clear()
        if not filter_text:
            for line in self.all_log_lines:
                self.log_box.appendPlainText(line)
        else:
            for line in self.all_log_lines:
                if filter_text in line.lower():
                    self.log_box.appendPlainText(line)
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.all_log_lines.clear()
        self.log_box.clear()

    def copy_log(self):
        QApplication.clipboard().setText(self.log_box.toPlainText())
        self.set_status_badge("● Log Copied", "success")

    def set_running(self, running: bool):
        self._is_running = running
        self.btn_oauth_login.setEnabled(not running)
        self.btn_logout.setEnabled(not running)
        if hasattr(self, "btn_verify_files"):
            self.btn_verify_files.setEnabled(not running)
        self.update_feature_enabled_state()

        if running:
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if "verifying" not in curr.lower():
                self.set_status_badge("● Downloading...", "running")
        else:
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if not any(k in curr.lower() for k in ("completed", "warning", "error")):
                if self.is_logged_in():
                    self.set_status_badge("● Ready", "ready")
                else:
                    self.set_status_badge("○ Login Required", "neutral")

    def start_download(self):
        if not self.is_logged_in():
            self.prompt_login_required("download files")
            return

        url = self.url_input.text().strip()
        destination = self.destination_input.text().strip()
        skip_existing = self.check_skip_existing.isChecked()
        verify_integrity = self.check_verify_integrity.isChecked() if hasattr(self, "check_verify_integrity") else True
        auto_repair = self.check_auto_repair.isChecked() if hasattr(self, "check_auto_repair") else True
        link_password = (self.link_password or "").strip()

        if not url:
            ModernMessageBox.warning(self, "Missing Link", "Please enter or paste a Dropbox shared link before downloading.")
            self.url_input.setFocus()
            return

        if not destination:
            ModernMessageBox.warning(self, "Missing Destination", "Please choose a local save destination folder before downloading.")
            return

        info = self.get_tree_selection_info()
        if info["has_tree_items"]:
            if info["total_files"] > 0 and info["selected_file_count"] == 0:
                ModernMessageBox.warning(
                    self,
                    "No Files Selected",
                    "All files in the folder are currently deselected.\n\n"
                    "Please check at least one folder or file to download.",
                )
                return
            if info["total_files"] == 0 and not info["selected_folders"]:
                ModernMessageBox.warning(
                    self,
                    "No Items Selected",
                    "All items in the folder are currently deselected.\n\n"
                    "Please check at least one item to download.",
                )
                return

        self.save_settings()
        root_name = getattr(self, "current_root_name", "")
        if not root_name and self.tree_widget.topLevelItemCount() > 0:
            top = self.tree_widget.topLevelItem(0)
            if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                root_name = top.data(3, Qt.ItemDataRole.UserRole) or ""
        self.add_recent_link(url, title=root_name, item_count=info.get("selected_file_count", 0))

        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Initializing...")
        self.file_label.setText("Connecting to Dropbox API...")
        self.val_speed.setText("0 B/s")
        self.val_data.setText("0 B")
        self.val_files.setText("0 files")
        self.val_time.setText("00:00")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        st = self.pause_button.style()
        if st is not None:
            st.unpolish(self.pause_button)
            st.polish(self.pause_button)

        self.set_running(True)
        self.add_log("▶ Starting selective download via Dropbox API...")
        if info["has_tree_items"] and info["total_files"] > 0:
            self.add_log(f"📋 Selection: {info['selected_file_count']} of {info['total_files']} files selected for download.")

        self.cleanup_download_thread()
        t = QThread()
        w = DownloadWorker(
            url=url,
            destination=destination,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            link_password=link_password,
            skip_existing=skip_existing,
            selected_files=info["selected_files"],
            deselected_files=info["deselected_files"],
            selected_folders=info["selected_folders"],
            deselected_folders=info["deselected_folders"],
            single_selected_folder=info.get("single_selected_folder", ""),
            has_tree_filter=info["has_tree_items"],
            verify_integrity=verify_integrity,
            auto_repair=auto_repair,
            verify_only=False,
        )

        w.moveToThread(t)
        t.started.connect(w.run)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_download_thread_finished(thread_ref=t):
            if getattr(self, "download_thread", None) is thread_ref:
                self.download_thread = None
                self.worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_download_thread_finished)

        self.download_thread = t
        self.worker = w
        self._active_workers[t] = w

        w.log.connect(self.add_log)
        w.folder_changed.connect(self.folder_label.setText)
        w.file_changed.connect(self.file_label.setText)
        w.current_progress.connect(self.update_file_progress)
        w.overall_progress.connect(self.update_overall_progress)
        w.stats_changed.connect(self.update_stats)
        w.paused_signal.connect(self.on_download_paused_changed)

        w.finished.connect(self.download_finished)
        w.failed.connect(self.download_failed)

        t.start()

    def start_verification_only(self):
        if not self.is_logged_in():
            self.prompt_login_required("verify downloaded files")
            return

        url = self.url_input.text().strip()
        destination = self.destination_input.text().strip()
        link_password = (self.link_password or "").strip()

        if not url:
            ModernMessageBox.warning(self, "Missing Link", "Please enter or paste a Dropbox shared link before verifying.")
            self.url_input.setFocus()
            return

        if not destination:
            ModernMessageBox.warning(self, "Missing Destination", "Please choose a local save destination folder before verifying.")
            return

        info = self.get_tree_selection_info()
        if info["has_tree_items"] and info["selected_file_count"] == 0:
            ModernMessageBox.warning(
                self,
                "No Files Selected",
                "Please select at least one file or folder from the tree above to verify."
            )
            return

        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Verifying Files...")
        self.file_label.setText("Connecting to Dropbox API to check metadata...")
        self.val_speed.setText("0 B/s")
        self.val_data.setText("0 B")
        self.val_files.setText("0 files")
        self.val_time.setText("00:00")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause")
        self.pause_button.setProperty("class", "btn-pause")
        st = self.pause_button.style()
        if st is not None:
            st.unpolish(self.pause_button)
            st.polish(self.pause_button)

        self.set_running(True)
        self.set_status_badge("● Verifying...", "verifying")
        self.add_log("🔍 Starting on-demand file integrity verification...")

        auto_repair = self.check_auto_repair.isChecked() if hasattr(self, "check_auto_repair") else True

        self.cleanup_download_thread()
        t = QThread()
        w = DownloadWorker(
            url=url,
            destination=destination,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            link_password=link_password,
            skip_existing=True,
            selected_files=info["selected_files"],
            deselected_files=info["deselected_files"],
            selected_folders=info["selected_folders"],
            deselected_folders=info["deselected_folders"],
            single_selected_folder=info.get("single_selected_folder", ""),
            has_tree_filter=info["has_tree_items"],
            verify_integrity=True,
            auto_repair=auto_repair,
            verify_only=True,
        )

        w.moveToThread(t)
        t.started.connect(w.run)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_verify_download_thread_finished(thread_ref=t):
            if getattr(self, "download_thread", None) is thread_ref:
                self.download_thread = None
                self.worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_verify_download_thread_finished)

        self.download_thread = t
        self.worker = w
        self._active_workers[t] = w

        w.log.connect(self.add_log)
        w.folder_changed.connect(self.folder_label.setText)
        w.file_changed.connect(self.file_label.setText)
        w.current_progress.connect(self.update_file_progress)
        w.overall_progress.connect(self.update_overall_progress)
        w.stats_changed.connect(self.update_stats)
        w.paused_signal.connect(self.on_download_paused_changed)

        w.finished.connect(self.download_finished)
        w.failed.connect(self.download_failed)

        t.start()

    def update_file_progress(self, val: int):
        self.file_progress.setValue(val)
        self.file_pct_label.setText(f"{val}%")

    def update_overall_progress(self, val: int):
        self.overall_progress.setValue(val)
        self.overall_pct_label.setText(f"{val}%")

    def update_stats(self, stats: dict):
        if "speed" in stats:
            self.val_speed.setText(stats["speed"])
        if "data" in stats:
            self.val_data.setText(stats["data"])
        if "files" in stats:
            self.val_files.setText(stats["files"])
        if "elapsed" in stats:
            self.val_time.setText(stats["elapsed"])

    def stop_download(self):
        if self.worker:
            if hasattr(self, "stop_button") and self.stop_button is not None:
                self.stop_button.setEnabled(False)
            if hasattr(self, "pause_button") and self.pause_button is not None:
                self.pause_button.setEnabled(False)
            self.worker.stop()
            self.add_log("⏹ Stop requested. Terminating whole operation...")
            self.set_status_badge("● Stopping...", "warning")

    def download_finished(self, message: str):
        self.download_thread = None
        self.set_running(False)
        self.add_log(f"\n{message}")

        has_corrupted = getattr(self.worker, "corrupted", 0) > 0 if self.worker else False
        has_missing = getattr(self.worker, "missing", 0) > 0 if self.worker else False
        has_errors = getattr(self.worker, "errors", 0) > 0 if self.worker else False

        if "stopped" in message.lower() or "cancelled" in message.lower():
            self.set_status_badge("⏹ Stopped", "neutral")
            self.folder_label.setText("Stopped")
            self.file_label.setText("Operation stopped by user")
            self.val_speed.setText("0 B/s")
            ModernMessageBox.information(self, "Operation Stopped", message)
        elif has_corrupted or has_missing or has_errors:
            self.set_status_badge("⚠️ Warnings", "warning")
            self.folder_label.setText("Completed with Warnings")
            self.file_label.setText("Some files had verification or download issues")
            self.overall_pct_label.setText("100%")
            self.file_pct_label.setText("100%")
            self.file_progress.setValue(100)
            self.overall_progress.setValue(100)
            self.val_speed.setText("0 B/s")
            ModernMessageBox.warning(self, "Completed with Warnings", message)
        else:
            self.set_status_badge("● Completed", "success")
            self.folder_label.setText("Completed")
            self.file_label.setText("Operation completed successfully")
            self.overall_pct_label.setText("100%")
            self.file_pct_label.setText("100%")
            self.file_progress.setValue(100)
            self.overall_progress.setValue(100)
            self.val_speed.setText("0 B/s")
            ModernMessageBox.information(self, "Completed Successfully", message)

        self.update_feature_enabled_state()
        self.update_download_button_state()

    def download_failed(self, error: str):
        self.download_thread = None
        self.set_running(False)
        self.update_feature_enabled_state()
        self.update_download_button_state()

        title, friendly_msg = parse_friendly_error(error)
        self.add_log(f"\n❌ FAILED: {title} - {friendly_msg.splitlines()[0]}")
        self.set_status_badge("● Error", "error")
        self.folder_label.setText(title)
        self.file_label.setText(friendly_msg.splitlines()[0])
        self.val_speed.setText("0 B/s")

        if "password" in error.lower() or "access_denied" in error.lower():
            pwd, ok = ModernInputDialog.get_text(
                self,
                title="Password Protected Link",
                heading="Dropbox Link Password Required",
                message=(
                    "This Dropbox shared link requires a password to download.\n\n"
                    "Please enter the folder link password below:"
                ),
                placeholder="Enter folder link password...",
                is_password=True,
                confirm_text="Set Password & Retry",
            )
            if ok and pwd:
                self.link_password = pwd.strip()
                self.start_download()
                return

        ModernMessageBox.error(self, title, friendly_msg)

    def closeEvent(self, event):
        self.save_settings()
        self.cleanup_download_thread()
        self.cleanup_scan_thread()
        self.cleanup_auth_thread()
        self.cleanup_verify_thread()

        deadline = time.time() + 1.5
        while getattr(self, "_active_workers", None) and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.02)

        if hasattr(self, "_active_workers"):
            for t in list(self._active_workers.keys()):
                if is_thread_running(t):
                    try:
                        t.quit()
                        t.wait(100)
                    except Exception:
                        pass

        event.accept()

