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
from PySide6.QtGui import QFont, QTextCursor, QCursor, QColor, QKeyEvent, QMouseEvent, QResizeEvent
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
    QStackedWidget,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QHeaderView,
    QInputDialog,
    QDialog,
    QMenu,
)

from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET, get_theme_stylesheet
from .ads import AdBannerWidget
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


class _ClickBackdrop(QFrame):
    """Semi-transparent click-catcher backdrop for the slide-over Settings drawer."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(15, 23, 42, 125); border: none;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class _RecentLinkRow(QFrame):
    """Clickable two-line recent folder row matching the Guided Wizard design."""

    clicked = Signal()

    def __init__(self, title_text: str, url_text: str, show_top_border: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("class", "recent-row")
        if not show_top_border:
            self.setProperty("first", "true")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(8, 9, 8, 9)
        row_layout.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        lbl_title = QLabel(title_text)
        lbl_title.setProperty("class", "recent-row-title")
        lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        lbl_url = QLabel(url_text)
        lbl_url.setProperty("class", "recent-row-url")
        lbl_url.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        text_col.addWidget(lbl_title)
        text_col.addWidget(lbl_url)
        row_layout.addLayout(text_col, 1)

        lbl_open = QLabel("Open →")
        lbl_open.setProperty("class", "recent-row-open")
        lbl_open.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_open.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row_layout.addWidget(lbl_open, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    _RE_START_FILE = re.compile(
        r"^(?:GET\s+|🔄 RESUME |🔄 RESTART |🔄 REPAIRING )\[(.*?)\] (.*?)(?:\s+\(|\:\s+)"
    )
    _RE_DONE_FILE = re.compile(r"^DONE\s+\[(.*?)\] (.*)$")
    _RE_SKIP_FILE = re.compile(r"^SKIP\s+\[(.*?)\] (.*?) \(already exists\)$")
    _RE_VERIFIED_FILE = re.compile(r"^✓ VERIFIED \[(.*?)\] (.*?)(?:\s+\[Hash:.*)?$")
    _RE_QUEUE_FILE = re.compile(r"^⏳ QUEUE \[(.*?)\] (.*?):")
    _RE_REQUEUED_ONLY = re.compile(r"^⏳ REQUEUED \[(.*?)\]")
    _RE_ERROR_FILE = re.compile(
        r"^(?:❌ ERROR|🔒 ERROR|❌ CORRUPTED|❌ MISSING|❌ UNREADABLE) \[(.*?)\] (.*?):"
    )

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dropbox Downloader")
        self.resize(980, 780)
        self.setMinimumSize(820, 640)

        self.settings = QSettings("DropboxDownloader", "RecursiveGUI")
        self.theme_mode: str = "light"

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
        self._scanned_url: str = ""

        self.current_access_token: str = ""
        self.current_refresh_token: str = ""
        self.current_user_name: str = ""
        self.current_user_email: str = ""
        self.link_password: str = ""
        self.recent_links: list[dict[str, Any]] = []
        self.is_download_paused: bool = False
        self._is_running: bool = False
        self.current_root_name: str = ""
        self.current_step: int = 0

        # Live Queue & Downloaded/Remaining State
        self.queue_filter_mode: str = "all"  # "all" | "done" | "rem"
        self._queue_records: dict[str, dict[str, Any]] = {}
        self._queue_tree_items: dict[str, QTreeWidgetItem] = {}
        self._active_queue_key: str = ""
        self._total_batch_files: int = 0
        self._total_batch_bytes: int = 0

        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.setSingleShot(True)
        self.auto_scan_timer.timeout.connect(self.auto_scan_if_valid)

        self.realtime_stats_timer = QTimer(self)
        self.realtime_stats_timer.setInterval(250)
        self.realtime_stats_timer.timeout.connect(self.tick_realtime_stats)

        self.setup_ui()
        self.load_settings()

    # ==========================================================================
    # Theme & Top-Level Badges
    # ==========================================================================
    def _repolish(self, widget: QWidget | None):
        if widget is None:
            return
        st = widget.style()
        if st is not None:
            st.unpolish(widget)
            st.polish(widget)
        widget.update()

    def apply_theme(self, mode: str, save: bool = True):
        self.theme_mode = "dark" if str(mode).strip().lower() == "dark" else "light"
        self.setStyleSheet(get_theme_stylesheet(self.theme_mode))
        if hasattr(self, "btn_theme_toggle"):
            if self.theme_mode == "light":
                self.btn_theme_toggle.setText("🌙  Switch to Minimal Dark Mode")
            else:
                self.btn_theme_toggle.setText("☀️  Switch to Clean Light Mode")

        # Re-apply dynamic badges & colors
        if hasattr(self, "auth_badge"):
            self.set_auth_badge(
                self.auth_badge.text() or ("● Connected" if self.is_logged_in() else "○ Not Logged In"),
                "connected" if self.is_logged_in() else "neutral",
            )
        if hasattr(self, "status_badge"):
            self.set_status_badge(
                self.status_badge.text() or "● Ready",
                getattr(self, "_last_status_state", "ready"),
            )
        self._refresh_all_queue_item_styles()
        if save:
            self.settings.setValue("theme_mode", self.theme_mode)

    def toggle_theme(self):
        next_mode = "dark" if self.theme_mode == "light" else "light"
        self.apply_theme(next_mode, save=True)

    def set_status_badge(self, text: str, state: str = "ready"):
        self._last_status_state = state
        if not hasattr(self, "status_badge"):
            return
        is_light = self.theme_mode == "light"
        if is_light:
            styles = {
                "ready": "background-color: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd;",
                "running": "background-color: #eff6ff; color: #0061ff; border: 1px solid #93c5fd;",
                "verifying": "background-color: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe;",
                "success": "background-color: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;",
                "warning": "background-color: #fffbeb; color: #d97706; border: 1px solid #fde68a;",
                "error": "background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca;",
                "neutral": "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;",
            }
        else:
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
            f"{style_str} border-radius: 11px; padding: 3px 11px; font-weight: 600; font-size: 11px;"
        )

    def set_auth_badge(self, text: str, state: str = "neutral"):
        if not hasattr(self, "auth_badge"):
            return
        is_light = self.theme_mode == "light"
        if is_light:
            styles = {
                "connected": "background-color: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;",
                "neutral": "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;",
            }
        else:
            styles = {
                "connected": "background-color: #064e3b; color: #34d399; border: 1px solid #059669;",
                "neutral": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;",
            }
        style_str = styles.get(state, styles["neutral"])
        self.auth_badge.setText(text)
        self.auth_badge.setStyleSheet(
            f"{style_str} border-radius: 11px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )

    def set_selection_summary(self, text: str, state: str = "neutral"):
        is_light = self.theme_mode == "light"
        if is_light:
            colors = {
                "neutral": ("#f1f5f9", "#64748b"),
                "active": ("#eff6ff", "#0061ff"),
                "success": ("#ecfdf5", "#059669"),
                "error": ("#fef2f2", "#dc2626"),
            }
        else:
            colors = {
                "neutral": ("#0b1120", "#94a3b8"),
                "active": ("#0c2e59", "#38bdf8"),
                "success": ("#064e3b", "#34d399"),
                "error": ("#450a0a", "#f87171"),
            }
        bg, fg = colors.get(state, colors["neutral"])
        self.selection_summary_label.setText(text)
        self.selection_summary_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )

    # ==========================================================================
    # UI Construction (3-Step Guided Wizard + Queue Tabs + Bottom Ad + Settings)
    # ==========================================================================
    def setup_ui(self):
        root_widget = QWidget()
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----------------------------------------------------------------------
        # TOP HEADER BAR: Brand (Left) + 3-Step Pills (Center) + Settings (Right)
        # ----------------------------------------------------------------------
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
        self.wizard_pill_bar = QFrame()
        self.wizard_pill_bar.setProperty("class", "wizard-pill-bar")
        self.wizard_pill_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        pill_layout = QHBoxLayout(self.wizard_pill_bar)
        pill_layout.setContentsMargins(4, 4, 4, 4)
        pill_layout.setSpacing(4)

        self.btn_step_1 = QPushButton("1. Link && Recent")
        self.btn_step_1.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_step_1.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_step_1.clicked.connect(lambda: self.go_to_step(0))

        self.btn_step_2 = QPushButton("2. Select Files")
        self.btn_step_2.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_step_2.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_step_2.clicked.connect(lambda: self.go_to_step(1))

        self.btn_step_3 = QPushButton("3. Transfers")
        self.btn_step_3.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_step_3.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_step_3.clicked.connect(lambda: self.go_to_step(2))

        pill_layout.addWidget(self.btn_step_1)
        pill_layout.addWidget(self.btn_step_2)
        pill_layout.addWidget(self.btn_step_3)
        header_layout.addWidget(self.wizard_pill_bar)

        header_layout.addStretch(1)

        # Corner Settings Button
        self.btn_settings = QPushButton("⚙️  Settings")
        self.btn_settings.setProperty("class", "btn-settings")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.setToolTip("Open download folder, integrity rules, account, theme, and activity log")
        self.btn_settings.clicked.connect(self.toggle_settings_drawer)
        header_layout.addWidget(self.btn_settings)

        root_layout.addWidget(header_card)

        # ----------------------------------------------------------------------
        # MAIN SCROLLABLE WORKSPACE + WIZARD STACK
        # ----------------------------------------------------------------------
        workspace_scroll = QScrollArea()
        workspace_scroll.setWidgetResizable(True)
        workspace_scroll.setFrameShape(QFrame.Shape.NoFrame)
        workspace_scroll.viewport().setAutoFillBackground(False)

        workspace_container = QWidget()
        workspace_container.setObjectName("workspaceContainer")
        workspace_layout = QVBoxLayout(workspace_container)
        workspace_layout.setContentsMargins(28, 20, 28, 12)
        workspace_layout.setSpacing(14)

        self.wizard_stack = QStackedWidget()
        self.wizard_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # ==================== STEP 1: PASTE LINK & RECENT ====================
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
        self.login_banner = QFrame()
        self.login_banner.setProperty("class", "login-banner")
        banner_layout = QHBoxLayout(self.login_banner)
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

        self.btn_banner_login = QPushButton("🌐  Log In to Dropbox")
        self.btn_banner_login.setProperty("class", "btn-primary")
        self.btn_banner_login.setFixedHeight(36)
        self.btn_banner_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_banner_login.clicked.connect(self.login_with_dropbox)
        banner_layout.addWidget(self.btn_banner_login, 0, Qt.AlignmentFlag.AlignVCenter)
        step1_layout.addWidget(self.login_banner)

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
        self.target_card = QFrame()
        self.target_card.setProperty("class", "url-command-card")
        target_layout = QHBoxLayout(self.target_card)
        target_layout.setContentsMargins(12, 10, 12, 10)
        target_layout.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setProperty("class", "command-input")
        self.url_input.setPlaceholderText("https://www.dropbox.com/scl/fo/... or https://www.dropbox.com/sh/...")
        self.url_input.textChanged.connect(self.on_url_text_changed)
        self.url_input.returnPressed.connect(self.start_scan)

        self.btn_clear_url = QPushButton("✕ Clear")
        self.btn_clear_url.setProperty("class", "btn-ghost")
        self.btn_clear_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear_url.setToolTip("Clear link and file list")
        self.btn_clear_url.clicked.connect(self.clear_url_and_tree)

        self.btn_paste_url = QPushButton("📋 Paste")
        self.btn_paste_url.setProperty("class", "btn-secondary")
        self.btn_paste_url.setMinimumHeight(38)
        self.btn_paste_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_paste_url.setToolTip("Paste link from clipboard and scan")
        self.btn_paste_url.clicked.connect(self.paste_url)

        self.btn_scan_url = QPushButton("Load Folders →")
        self.btn_scan_url.setProperty("class", "btn-load-folders")
        self.btn_scan_url.setMinimumHeight(40)
        self.btn_scan_url.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scan_url.setToolTip("Inspect shared folder and select files (Enter)")
        self.btn_scan_url.clicked.connect(self.start_scan)

        target_layout.addWidget(self.url_input, 1)
        target_layout.addWidget(self.btn_clear_url)
        target_layout.addWidget(self.btn_paste_url)
        target_layout.addWidget(self.btn_scan_url)
        step1_layout.addWidget(self.target_card)

        # Recent Links Card (Quick Chips + Detailed Recent Rows)
        self.recent_card = QFrame()
        self.recent_card.setProperty("class", "card")
        recent_card_layout = QVBoxLayout(self.recent_card)
        recent_card_layout.setContentsMargins(20, 16, 20, 16)
        recent_card_layout.setSpacing(10)

        recent_header = QHBoxLayout()
        recent_title = QLabel("🕒 RECENT LINKS")
        recent_title.setProperty("class", "section-title")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()

        self.btn_recent_links = QPushButton("All History ▼")
        self.btn_recent_links.setProperty("class", "btn-ghost")
        self.btn_recent_links.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_recent_links.setToolTip("Open full recent links menu or clear history")
        self.btn_recent_links.clicked.connect(self.show_recent_links_menu)
        recent_header.addWidget(self.btn_recent_links)
        recent_card_layout.addLayout(recent_header)

        self.recent_chips_container = QWidget()
        self.recent_chips_container.setStyleSheet("background-color: transparent;")
        self.recent_chips_layout = QHBoxLayout(self.recent_chips_container)
        self.recent_chips_layout.setContentsMargins(0, 0, 0, 2)
        self.recent_chips_layout.setSpacing(8)
        self.recent_chips_container.setVisible(False)
        recent_card_layout.addWidget(self.recent_chips_container)

        self.recent_rows_container = QWidget()
        self.recent_rows_container.setStyleSheet("background-color: transparent;")
        self.recent_rows_layout = QVBoxLayout(self.recent_rows_container)
        self.recent_rows_layout.setContentsMargins(0, 2, 0, 0)
        self.recent_rows_layout.setSpacing(2)
        recent_card_layout.addWidget(self.recent_rows_container)

        step1_layout.addWidget(self.recent_card)
        step1_layout.addStretch(2)

        step1_outer.addWidget(step1_col, 100)
        step1_outer.addStretch(1)
        self.wizard_stack.addWidget(step1_page)

        # ==================== STEP 2: SELECT FILES ====================
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

        self.btn_back_to_link = QPushButton("← Change Link")
        self.btn_back_to_link.setProperty("class", "btn-secondary")
        self.btn_back_to_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back_to_link.clicked.connect(lambda: self.go_to_step(0))
        step2_top_bar.addWidget(self.btn_back_to_link)

        self.step2_folder_label = QLabel("📂 Shared Folder")
        self.step2_folder_label.setStyleSheet("font-size: 13px; font-weight: 700; background-color: transparent;")
        step2_top_bar.addWidget(self.step2_folder_label)

        self.selection_summary_label = QLabel("(Paste link in Step 1 to inspect folders)")
        self.set_selection_summary("(Paste link in Step 1 to inspect folders)", "neutral")
        step2_top_bar.addWidget(self.selection_summary_label)

        step2_top_bar.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_select_all.clicked.connect(self.select_all_items)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_deselect_all.clicked.connect(self.deselect_all_items)

        self.btn_expand_all = QPushButton("Expand All")
        self.btn_expand_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_expand_all.clicked.connect(lambda: self.tree_widget.expandAll())

        self.btn_collapse_all = QPushButton("Collapse All")
        self.btn_collapse_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_collapse_all.clicked.connect(lambda: self.tree_widget.collapseAll())

        step2_top_bar.addWidget(self.btn_select_all)
        step2_top_bar.addWidget(self.btn_deselect_all)
        step2_top_bar.addWidget(self.btn_expand_all)
        step2_top_bar.addWidget(self.btn_collapse_all)
        step2_layout.addLayout(step2_top_bar)

        # Spacious Tree Card
        self.tree_card = QFrame()
        self.tree_card.setProperty("class", "card")
        tree_layout = QVBoxLayout(self.tree_card)
        tree_layout.setContentsMargins(16, 14, 16, 14)
        tree_layout.setSpacing(8)

        self.tree_widget = FileTreeWidget()
        self.tree_widget.setHeaderLabels(["Folder / File Name", "Type", "Size"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_widget.setMinimumHeight(290)
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
        tree_layout.addWidget(self.tree_widget, 1)

        self.tree_hint = QLabel(
            "💡 Tip: Check files/folders to download. Shift+Click for range select. Space to toggle. Right-click for options."
        )
        self.tree_hint.setStyleSheet("font-size: 11px; color: #64748b; background-color: transparent;")
        tree_layout.addWidget(self.tree_hint)
        step2_layout.addWidget(self.tree_card, 1)

        # Bottom Action Footer
        step2_footer = QHBoxLayout()
        step2_footer.setSpacing(10)

        self.dest_summary_label = QLabel()
        self.dest_summary_label.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        step2_footer.addWidget(self.dest_summary_label)

        self.btn_change_dest = QPushButton("Change in ⚙️ Settings")
        self.btn_change_dest.setProperty("class", "ad-cta")
        self.btn_change_dest.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_change_dest.clicked.connect(self.open_settings_drawer)
        step2_footer.addWidget(self.btn_change_dest)

        step2_footer.addStretch()

        self.btn_verify_files = QPushButton("🔍  Verify Existing")
        self.btn_verify_files.setProperty("class", "btn-secondary")
        self.btn_verify_files.setEnabled(False)
        self.btn_verify_files.setMinimumHeight(40)
        self.btn_verify_files.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_verify_files.setToolTip(
            "Verify existing downloaded files against Dropbox cloud checksums without re-downloading intact files."
        )
        self.btn_verify_files.clicked.connect(self.start_verification_only)

        self.start_button = QPushButton("📋  Paste Link && Select Files to Start")
        self.start_button.setProperty("class", "btn-start")
        self.start_button.setEnabled(False)
        self.start_button.setMinimumHeight(40)
        self.start_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_button.clicked.connect(self.start_download)

        self.btn_view_active_transfer = QPushButton("View Active Transfer →")
        self.btn_view_active_transfer.setProperty("class", "btn-primary")
        self.btn_view_active_transfer.setMinimumHeight(40)
        self.btn_view_active_transfer.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_view_active_transfer.setVisible(False)
        self.btn_view_active_transfer.clicked.connect(lambda: self.go_to_step(2))

        step2_footer.addWidget(self.btn_verify_files)
        step2_footer.addWidget(self.start_button)
        step2_footer.addWidget(self.btn_view_active_transfer)
        step2_layout.addLayout(step2_footer)

        step2_outer.addWidget(step2_col, 100)
        step2_outer.addStretch(1)
        self.wizard_stack.addWidget(step2_page)

        # ==================== STEP 3: TRANSFERS & QUEUE TABS ====================
        step3_page = QWidget()
        step3_outer = QHBoxLayout(step3_page)
        step3_outer.setContentsMargins(0, 0, 0, 0)
        step3_outer.addStretch(1)

        self.progress_card = QWidget()
        self.progress_card.setMaximumWidth(920)
        self.progress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        step3_layout = QVBoxLayout(self.progress_card)
        step3_layout.setContentsMargins(0, 4, 0, 4)
        step3_layout.setSpacing(12)

        # Row 1: Design 3's 3 Bold Summary Stat Cards (Downloaded / Remaining / Speed & Time)
        stats_row = QGridLayout()
        stats_row.setSpacing(12)
        stats_row.setColumnStretch(0, 1)
        stats_row.setColumnStretch(1, 1)
        stats_row.setColumnStretch(2, 1)

        # Card A: Downloaded
        card_done = QFrame()
        card_done.setProperty("class", "stat-card")
        done_h = QHBoxLayout(card_done)
        done_h.setContentsMargins(16, 12, 16, 12)
        done_v = QVBoxLayout()
        done_v.setSpacing(2)
        lbl_done_title = QLabel("✓ Downloaded")
        lbl_done_title.setProperty("class", "metric-title")
        self.val_files = QLabel("0 files")
        self.val_files.setStyleSheet(
            "font-size: 19px; font-weight: 700; color: #10b981; background-color: transparent;"
        )
        self.val_data = QLabel("0 B saved to disk")
        self.val_data.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        done_v.addWidget(lbl_done_title)
        done_v.addWidget(self.val_files)
        done_v.addWidget(self.val_data)
        done_icon = QLabel("✅")
        done_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
        done_h.addLayout(done_v, 1)
        done_h.addWidget(done_icon)
        stats_row.addWidget(card_done, 0, 0)

        # Card B: Remaining
        card_rem = QFrame()
        card_rem.setProperty("class", "stat-card")
        rem_h = QHBoxLayout(card_rem)
        rem_h.setContentsMargins(16, 12, 16, 12)
        rem_v = QVBoxLayout()
        rem_v.setSpacing(2)
        lbl_rem_title = QLabel("⏳ Remaining")
        lbl_rem_title.setProperty("class", "metric-title")
        self.val_remaining_files = QLabel("0 files left")
        self.val_remaining_files.setStyleSheet(
            "font-size: 19px; font-weight: 700; color: #f59e0b; background-color: transparent;"
        )
        self.val_remaining_bytes = QLabel("0 B remaining")
        self.val_remaining_bytes.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        rem_v.addWidget(lbl_rem_title)
        rem_v.addWidget(self.val_remaining_files)
        rem_v.addWidget(self.val_remaining_bytes)
        rem_icon = QLabel("⏳")
        rem_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
        rem_h.addLayout(rem_v, 1)
        rem_h.addWidget(rem_icon)
        stats_row.addWidget(card_rem, 0, 1)

        # Card C: Speed & Time
        card_speed = QFrame()
        card_speed.setProperty("class", "stat-card")
        spd_h = QHBoxLayout(card_speed)
        spd_h.setContentsMargins(16, 12, 16, 12)
        spd_v = QVBoxLayout()
        spd_v.setSpacing(2)
        lbl_spd_title = QLabel("⚡ Speed & Time")
        lbl_spd_title.setProperty("class", "metric-title")
        self.val_speed = QLabel("0 B/s")
        self.val_speed.setProperty("class", "metric-value")
        time_eta_row = QHBoxLayout()
        time_eta_row.setContentsMargins(0, 0, 0, 0)
        time_eta_row.setSpacing(4)
        lbl_elapsed_prefix = QLabel("Elapsed")
        lbl_elapsed_prefix.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        self.val_time = QLabel("00:00")
        self.val_time.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 600; background-color: transparent;")
        self.val_eta = QLabel("")
        self.val_eta.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        time_eta_row.addWidget(lbl_elapsed_prefix)
        time_eta_row.addWidget(self.val_time)
        time_eta_row.addWidget(self.val_eta)
        time_eta_row.addStretch()
        spd_v.addWidget(lbl_spd_title)
        spd_v.addWidget(self.val_speed)
        spd_v.addLayout(time_eta_row)
        spd_icon = QLabel("🚀")
        spd_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
        spd_h.addLayout(spd_v, 1)
        spd_h.addWidget(spd_icon)
        stats_row.addWidget(card_speed, 0, 2)

        step3_layout.addLayout(stats_row)

        # Row 2: Dual Clean Progress Card + Transfer Controls
        prog_box = QFrame()
        prog_box.setProperty("class", "card")
        prog_box_layout = QVBoxLayout(prog_box)
        prog_box_layout.setContentsMargins(18, 14, 18, 14)
        prog_box_layout.setSpacing(8)

        file_prog_header = QHBoxLayout()
        lbl_cur = QLabel("Current File:")
        lbl_cur.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b; background-color: transparent;")
        self.file_label = QLabel("Idle")
        self.file_label.setStyleSheet("font-size: 12px; font-weight: 600; background-color: transparent;")
        file_prog_header.addWidget(lbl_cur)
        file_prog_header.addWidget(self.file_label, 1)
        self.file_pct_label = QLabel("0%")
        self.file_pct_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #0ea5e9; background-color: transparent;")
        file_prog_header.addWidget(self.file_pct_label)
        prog_box_layout.addLayout(file_prog_header)

        self.file_progress = QProgressBar()
        self.file_progress.setRange(0, 100)
        self.file_progress.setValue(0)
        prog_box_layout.addWidget(self.file_progress)

        overall_prog_header = QHBoxLayout()
        lbl_all = QLabel("Overall Batch Progress:")
        lbl_all.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b; background-color: transparent;")
        self.folder_label = QLabel("Idle")
        self.folder_label.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
        overall_prog_header.addWidget(lbl_all)
        overall_prog_header.addWidget(self.folder_label, 1)
        self.overall_pct_label = QLabel("0%")
        self.overall_pct_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #10b981; background-color: transparent;")
        overall_prog_header.addWidget(self.overall_pct_label)
        prog_box_layout.addLayout(overall_prog_header)

        self.overall_progress = QProgressBar()
        self.overall_progress.setProperty("class", "overall")
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        prog_box_layout.addWidget(self.overall_progress)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        self.btn_back_to_files = QPushButton("← Back to File Selection")
        self.btn_back_to_files.setProperty("class", "ad-cta")
        self.btn_back_to_files.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back_to_files.clicked.connect(lambda: self.go_to_step(1))
        controls_row.addWidget(self.btn_back_to_files)

        controls_row.addStretch()

        self.btn_step3_open_folder = QPushButton("📂 Open Folder")
        self.btn_step3_open_folder.setProperty("class", "btn-secondary")
        self.btn_step3_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_step3_open_folder.clicked.connect(self.open_destination_folder)
        controls_row.addWidget(self.btn_step3_open_folder)

        self.pause_button = QPushButton("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        self.pause_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pause_button.setVisible(False)
        self.pause_button.clicked.connect(self.toggle_pause_download)
        controls_row.addWidget(self.pause_button)

        self.stop_button = QPushButton("⏹  Stop Download")
        self.stop_button.setProperty("class", "btn-stop")
        self.stop_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self.stop_download)
        controls_row.addWidget(self.stop_button)

        prog_box_layout.addLayout(controls_row)
        step3_layout.addWidget(prog_box)

        # Row 3: Design 1's Interactive Queue Filter Tabs (All / ✓ Downloaded / ⏳ Remaining)
        queue_card = QFrame()
        queue_card.setProperty("class", "card")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(18, 14, 18, 14)
        queue_layout.setSpacing(10)

        qtab_header = QHBoxLayout()
        qtab_header.setSpacing(8)

        self.btn_qtab_all = QPushButton("All Selected (0)")
        self.btn_qtab_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_qtab_all.clicked.connect(lambda: self.set_queue_filter("all"))

        self.btn_qtab_done = QPushButton("✓ Downloaded (0)")
        self.btn_qtab_done.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_qtab_done.clicked.connect(lambda: self.set_queue_filter("done"))

        self.btn_qtab_rem = QPushButton("⏳ Remaining / Up Next (0)")
        self.btn_qtab_rem.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_qtab_rem.clicked.connect(lambda: self.set_queue_filter("rem"))

        qtab_header.addWidget(self.btn_qtab_all)
        qtab_header.addWidget(self.btn_qtab_done)
        qtab_header.addWidget(self.btn_qtab_rem)
        qtab_header.addStretch()

        self.lbl_integrity_badge = QLabel("SHA-256 Checksum Verified ✓")
        self.lbl_integrity_badge.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600; background-color: transparent;")
        qtab_header.addWidget(self.lbl_integrity_badge)
        queue_layout.addLayout(qtab_header)

        qtab_divider = QFrame()
        qtab_divider.setProperty("class", "divider-line")
        queue_layout.addWidget(qtab_divider)

        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderLabels(["File", "Folder", "Status • Size"])
        self.queue_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_tree.setRootIsDecorated(False)
        self.queue_tree.setMinimumHeight(165)
        self.queue_tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        queue_layout.addWidget(self.queue_tree, 1)

        step3_layout.addWidget(queue_card, 1)

        step3_outer.addWidget(self.progress_card, 100)
        step3_outer.addStretch(1)
        self.wizard_stack.addWidget(step3_page)

        workspace_layout.addWidget(self.wizard_stack, 1)
        workspace_scroll.setWidget(workspace_container)
        root_layout.addWidget(workspace_scroll, 1)

        # ----------------------------------------------------------------------
        # PERSISTENT CLEAN BOTTOM BANNER AD
        # ----------------------------------------------------------------------
        ad_outer = QHBoxLayout()
        ad_outer.setContentsMargins(28, 4, 28, 18)
        ad_outer.addStretch(1)
        self.ad_banner = AdBannerWidget(self)
        self.ad_banner.setMaximumWidth(920)
        self.ad_banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        ad_outer.addWidget(self.ad_banner, 100)
        ad_outer.addStretch(1)
        root_layout.addLayout(ad_outer)

        self.setCentralWidget(root_widget)

        # ----------------------------------------------------------------------
        # CORNER SETTINGS SLIDE-OVER DRAWER OVERLAY
        # ----------------------------------------------------------------------
        self.settings_overlay = QWidget(self)
        self.settings_overlay.setVisible(False)
        overlay_layout = QHBoxLayout(self.settings_overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)

        self.settings_backdrop = _ClickBackdrop(self.settings_overlay)
        self.settings_backdrop.clicked.connect(self.close_settings_drawer)
        overlay_layout.addWidget(self.settings_backdrop, 1)

        self.settings_drawer = QFrame(self.settings_overlay)
        self.settings_drawer.setProperty("class", "settings-drawer")
        self.settings_drawer.setFixedWidth(430)
        drawer_outer = QVBoxLayout(self.settings_drawer)
        drawer_outer.setContentsMargins(20, 18, 20, 18)
        drawer_outer.setSpacing(14)

        drawer_header = QHBoxLayout()
        drawer_title = QLabel("⚙️ Settings & Diagnostics")
        drawer_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        drawer_title.setStyleSheet("background-color: transparent; font-weight: 700;")
        drawer_header.addWidget(drawer_title)
        drawer_header.addStretch()

        self.btn_close_settings = QPushButton("✕ Close")
        self.btn_close_settings.setProperty("class", "btn-secondary")
        self.btn_close_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close_settings.clicked.connect(self.close_settings_drawer)
        drawer_header.addWidget(self.btn_close_settings)
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
        drawer_layout.setContentsMargins(0, 4, 4, 4)
        drawer_layout.setSpacing(16)

        # 1. Default Download Folder
        dest_sec = QVBoxLayout()
        dest_sec.setSpacing(6)
        dest_lbl = QLabel("DEFAULT DOWNLOAD FOLDER")
        dest_lbl.setProperty("class", "section-title")
        dest_sec.addWidget(dest_lbl)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(6)
        self.destination_input = QLineEdit()
        self.destination_input.setText(str(Path.home() / "Downloads"))
        self.destination_input.setPlaceholderText("Select local folder to save files...")
        self.destination_input.textChanged.connect(self._on_destination_changed)

        self.btn_browse = QPushButton("Browse")
        self.btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_browse.clicked.connect(self.browse_destination)

        self.btn_open_folder = QPushButton("Open")
        self.btn_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_folder.clicked.connect(self.open_destination_folder)

        dest_row.addWidget(self.destination_input, 1)
        dest_row.addWidget(self.btn_browse)
        dest_row.addWidget(self.btn_open_folder)
        dest_sec.addLayout(dest_row)
        drawer_layout.addLayout(dest_sec)

        # 2. Smart Download & Integrity Rules
        rules_sec = QVBoxLayout()
        rules_sec.setSpacing(8)
        rules_lbl = QLabel("DOWNLOAD & INTEGRITY RULES")
        rules_lbl.setProperty("class", "section-title")
        rules_sec.addWidget(rules_lbl)

        self.check_skip_existing = QCheckBox("Skip files that already exist locally (matching exact size)")
        self.check_skip_existing.setChecked(True)
        self.check_skip_existing.stateChanged.connect(lambda: self.save_settings())
        rules_sec.addWidget(self.check_skip_existing)

        self.check_verify_integrity = QCheckBox("Verify SHA-256 checksum after download")
        self.check_verify_integrity.setChecked(True)
        self.check_verify_integrity.stateChanged.connect(self._on_verify_setting_changed)
        rules_sec.addWidget(self.check_verify_integrity)

        self.check_auto_repair = QCheckBox("Auto re-download if file is corrupted")
        self.check_auto_repair.setChecked(True)
        self.check_auto_repair.stateChanged.connect(lambda: self.save_settings())
        rules_sec.addWidget(self.check_auto_repair)
        drawer_layout.addLayout(rules_sec)

        # 3. Dropbox Account
        acct_sec = QVBoxLayout()
        acct_sec.setSpacing(6)
        acct_lbl = QLabel("DROPBOX ACCOUNT")
        acct_lbl.setProperty("class", "section-title")
        acct_sec.addWidget(acct_lbl)

        account_pill = QFrame()
        account_pill.setProperty("class", "subtle-card")
        account_pill_layout = QHBoxLayout(account_pill)
        account_pill_layout.setContentsMargins(12, 10, 12, 10)
        account_pill_layout.setSpacing(8)

        self.account_info_layout = QVBoxLayout()
        self.account_info_layout.setSpacing(2)
        self.account_name_label = QLabel("No Dropbox account connected")
        self.account_name_label.setStyleSheet("font-size: 12px; font-weight: 700; background-color: transparent;")
        self.account_sub_label = QLabel("Sign in to your Dropbox account")
        self.account_sub_label.setStyleSheet("font-size: 11px; color: #64748b; background-color: transparent;")
        self.account_info_layout.addWidget(self.account_name_label)
        self.account_info_layout.addWidget(self.account_sub_label)
        account_pill_layout.addLayout(self.account_info_layout, 1)

        self.btn_oauth_login = QPushButton("🌐  Log In")
        self.btn_oauth_login.setProperty("class", "btn-primary")
        self.btn_oauth_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_oauth_login.clicked.connect(self.login_with_dropbox)
        account_pill_layout.addWidget(self.btn_oauth_login)

        self.btn_logout = QPushButton("Sign Out")
        self.btn_logout.setProperty("class", "btn-stop")
        self.btn_logout.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_logout.clicked.connect(self.logout_dropbox)
        self.btn_logout.setVisible(False)
        account_pill_layout.addWidget(self.btn_logout)

        acct_sec.addWidget(account_pill)
        drawer_layout.addLayout(acct_sec)

        # 4. Appearance
        theme_sec = QVBoxLayout()
        theme_sec.setSpacing(6)
        theme_lbl = QLabel("APPEARANCE")
        theme_lbl.setProperty("class", "section-title")
        theme_sec.addWidget(theme_lbl)

        self.btn_theme_toggle = QPushButton("🌙  Switch to Minimal Dark Mode")
        self.btn_theme_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        theme_sec.addWidget(self.btn_theme_toggle)
        drawer_layout.addLayout(theme_sec)

        # 5. Activity Log & Diagnostics
        log_sec = QVBoxLayout()
        log_sec.setSpacing(6)
        log_header = QHBoxLayout()
        log_title = QLabel("ACTIVITY LOG")
        log_title.setProperty("class", "section-title")
        log_header.addWidget(log_title)
        log_header.addStretch()

        btn_copy = QPushButton("Copy")
        btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy.clicked.connect(self.copy_log)
        btn_clear = QPushButton("Clear")
        btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_clear.clicked.connect(self.clear_log)
        self.btn_toggle_log = QPushButton("Hide Log")
        self.btn_toggle_log.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_log.clicked.connect(self.toggle_log_visibility)

        log_header.addWidget(btn_copy)
        log_header.addWidget(btn_clear)
        log_header.addWidget(self.btn_toggle_log)
        log_sec.addLayout(log_header)

        self.log_filter = QLineEdit()
        self.log_filter.setPlaceholderText("Filter logs...")
        self.log_filter.textChanged.connect(self.filter_logs)
        log_sec.addWidget(self.log_filter)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(140)
        log_sec.addWidget(self.log_box)
        drawer_layout.addLayout(log_sec)

        drawer_layout.addStretch(1)
        drawer_scroll.setWidget(drawer_content)
        drawer_outer.addWidget(drawer_scroll, 1)

        drawer_bot_divider = QFrame()
        drawer_bot_divider.setProperty("class", "divider-line")
        drawer_outer.addWidget(drawer_bot_divider)

        drawer_footer = QHBoxLayout()
        drawer_footer.addStretch()
        btn_save_close = QPushButton("Save && Close")
        btn_save_close.setProperty("class", "btn-primary")
        btn_save_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save_close.clicked.connect(self._save_and_close_settings)
        drawer_footer.addWidget(btn_save_close)
        drawer_outer.addLayout(drawer_footer)

        overlay_layout.addWidget(self.settings_drawer)

        self.all_log_lines: list[str] = []

        # Initialize states
        self.apply_theme("light", save=False)
        self._on_destination_changed(self.destination_input.text())
        self.go_to_step(0)
        self.set_queue_filter("all")
        self.show_empty_tree_placeholder()
        self._show_empty_queue_placeholder()

    # ==========================================================================
    # Wizard Navigation, Settings Drawer & Queue Filter Tabs
    # ==========================================================================
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if hasattr(self, "settings_overlay") and self.settings_overlay is not None:
            self.settings_overlay.setGeometry(self.rect())

    def _refresh_wizard_pill_geometry(self):
        if not hasattr(self, "wizard_pill_bar") or self.wizard_pill_bar is None:
            return
        for btn in (self.btn_step_1, self.btn_step_2, self.btn_step_3):
            self._repolish(btn)
            btn.updateGeometry()
        lay = self.wizard_pill_bar.layout()
        if lay is not None:
            lay.invalidate()
            lay.activate()
        self.wizard_pill_bar.updateGeometry()
        parent = self.wizard_pill_bar.parentWidget()
        if parent is not None and parent.layout() is not None:
            parent.layout().invalidate()
            parent.layout().activate()

    def go_to_step(self, step_index: int):
        idx = max(0, min(int(step_index), 2))
        self.current_step = idx
        self.wizard_stack.setCurrentIndex(idx)

        step_buttons = [self.btn_step_1, self.btn_step_2, self.btn_step_3]
        for i, btn in enumerate(step_buttons):
            cls_name = "wizard-step-btn-active" if i == idx else "wizard-step-btn"
            btn.setProperty("class", cls_name)
        self._refresh_wizard_pill_geometry()

    def open_settings_drawer(self):
        self.settings_overlay.setGeometry(self.rect())
        self.settings_overlay.setVisible(True)
        self.settings_overlay.raise_()

    def close_settings_drawer(self):
        self.settings_overlay.setVisible(False)

    def toggle_settings_drawer(self):
        if self.settings_overlay.isVisible():
            self.close_settings_drawer()
        else:
            self.open_settings_drawer()

    def _save_and_close_settings(self):
        self.save_settings()
        self.close_settings_drawer()

    def _on_destination_changed(self, text: str):
        dest_str = text.strip() or str(Path.home() / "Downloads")
        if hasattr(self, "dest_summary_label"):
            short_dest = dest_str if len(dest_str) <= 46 else ("…" + dest_str[-44:])
            self.dest_summary_label.setText(f"Saving to: {short_dest}")
            self.dest_summary_label.setToolTip(dest_str)

    def _on_verify_setting_changed(self):
        self.save_settings()
        if hasattr(self, "lbl_integrity_badge"):
            if self.check_verify_integrity.isChecked():
                self.lbl_integrity_badge.setText("SHA-256 Checksum Verified ✓")
                self.lbl_integrity_badge.setStyleSheet(
                    "font-size: 11px; color: #10b981; font-weight: 600; background-color: transparent;"
                )
            else:
                self.lbl_integrity_badge.setText("Standard Mode (Checksum Off)")
                self.lbl_integrity_badge.setStyleSheet(
                    "font-size: 11px; color: #64748b; font-weight: 600; background-color: transparent;"
                )

    def set_queue_filter(self, mode: str):
        if mode not in ("all", "done", "rem"):
            mode = "all"
        self.queue_filter_mode = mode

        tab_map = {
            "all": self.btn_qtab_all,
            "done": self.btn_qtab_done,
            "rem": self.btn_qtab_rem,
        }
        for key, btn in tab_map.items():
            btn.setProperty("class", "qtab-btn-active" if key == mode else "qtab-btn")
            self._repolish(btn)

        self._apply_queue_filter_visibility()

    def _show_empty_queue_placeholder(self):
        self.queue_tree.clear()
        placeholder = QTreeWidgetItem(
            self.queue_tree,
            ["Select files in Step 2 to view downloaded and remaining queue details", "—", "—"],
        )
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        col = QColor("#64748b")
        for c in range(3):
            placeholder.setForeground(c, col)

    def _make_queue_key(self, folder_display: str, file_display: str) -> str:
        return f"{folder_display}::{file_display}"

    def rebuild_queue_from_selection(self):
        """Populate Step 3 queue list and Downloaded/Remaining preview from selected tree files."""
        info = self.get_tree_selection_info()
        selected_entries: list[dict[str, Any]] = []

        if self._tree_items_data and info.get("has_tree_items"):
            for e in self._tree_items_data:
                if e.get("is_dir"):
                    continue
                rel = e.get("path") or e.get("rel_path") or ""
                if is_path_selected(
                    rel,
                    info["selected_files"],
                    info["deselected_files"],
                    info["selected_folders"],
                    info["deselected_folders"],
                    True,
                ):
                    selected_entries.append(
                        {
                            "name": e.get("name") or Path(rel).name,
                            "rel_path": rel,
                            "size": int(e.get("size", 0) or 0),
                        }
                    )
        elif info.get("has_tree_items"):
            def _collect_checked(item: QTreeWidgetItem | None):
                if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                    return
                is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
                if is_dir:
                    for idx in range(item.childCount()):
                        _collect_checked(item.child(idx))
                elif item.checkState(0) == Qt.CheckState.Checked:
                    rel = item.data(0, Qt.ItemDataRole.UserRole) or ""
                    raw_name = item.data(3, Qt.ItemDataRole.UserRole) or Path(rel).name
                    sz = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)
                    selected_entries.append({"name": raw_name, "rel_path": rel, "size": sz})

            for i in range(self.tree_widget.topLevelItemCount()):
                _collect_checked(self.tree_widget.topLevelItem(i))

        selected_entries.sort(key=lambda d: natural_sort_path_key(d["rel_path"]))

        # Match DownloadWorker's single-folder destination stripping so keys align 100%
        dest_str = self.destination_input.text().strip()
        if dest_str and selected_entries:
            matched_folder, stripped_prefix = check_single_folder_destination_match(
                selected_entries,
                Path(dest_str),
                info.get("single_selected_folder", ""),
            )
            if matched_folder and stripped_prefix:
                for d in selected_entries:
                    d["rel_path"] = strip_folder_prefix(d["rel_path"], stripped_prefix)

        self._queue_records.clear()
        self._queue_tree_items.clear()
        self._active_queue_key = ""

        total_bytes = 0
        self.queue_tree.setUpdatesEnabled(False)
        try:
            self.queue_tree.clear()
            if not selected_entries:
                self._show_empty_queue_placeholder()
            else:
                for idx, entry in enumerate(selected_entries):
                    rel_clean = str(entry["rel_path"]).replace("\\", "/").strip("/")
                    folder_disp = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
                    file_disp = entry["name"] or Path(rel_clean).name
                    sz = int(entry["size"] or 0)
                    total_bytes += sz
                    base_key = self._make_queue_key(folder_disp, file_disp)
                    key = base_key if base_key not in self._queue_records else f"{base_key}#{idx}"

                    _, icon_str = get_file_type_and_icon(file_disp)
                    status_label = "⏳ Up Next" if idx == 0 else "⏳ Queued"
                    sz_str = format_bytes(sz)
                    row_item = QTreeWidgetItem([f"{icon_str}{file_disp}", folder_disp, f"{status_label} • {sz_str}"])
                    self.queue_tree.addTopLevelItem(row_item)

                    rec = {
                        "key": key,
                        "name": file_disp,
                        "folder": folder_disp,
                        "size": sz,
                        "status": "queued",
                        "progress": 0,
                        "icon": icon_str,
                    }
                    self._queue_records[key] = rec
                    self._queue_tree_items[key] = row_item
                    self._style_queue_row(row_item, "queued")
        finally:
            self.queue_tree.setUpdatesEnabled(True)

        self._total_batch_files = len(selected_entries)
        self._total_batch_bytes = total_bytes
        self._refresh_queue_counts_and_cards()
        self._apply_queue_filter_visibility()

    def _style_queue_row(self, item: QTreeWidgetItem, status: str):
        is_light = self.theme_mode == "light"
        palette = {
            "downloading": "#0284c7" if is_light else "#38bdf8",
            "verifying": "#7c3aed" if is_light else "#c084fc",
            "done": "#059669" if is_light else "#34d399",
            "skipped": "#059669" if is_light else "#34d399",
            "verified": "#059669" if is_light else "#34d399",
            "queued": "#d97706" if is_light else "#fbbf24",
            "error": "#dc2626" if is_light else "#f87171",
        }
        fg_main = QColor("#0f172a" if is_light else "#f1f5f9")
        fg_muted = QColor("#64748b" if is_light else "#94a3b8")
        fg_status = QColor(palette.get(status, "#64748b"))
        item.setForeground(0, fg_main)
        item.setForeground(1, fg_muted)
        item.setForeground(2, fg_status)

    def _refresh_all_queue_item_styles(self):
        for key, rec in self._queue_records.items():
            row_item = self._queue_tree_items.get(key)
            if row_item is not None:
                self._style_queue_row(row_item, rec["status"])

    def _is_completed_status(self, status: str) -> bool:
        return status in ("done", "skipped", "verified")

    def _apply_queue_filter_visibility(self):
        if not self._queue_records:
            return
        mode = self.queue_filter_mode
        self.queue_tree.setUpdatesEnabled(False)
        try:
            for key, rec in self._queue_records.items():
                item = self._queue_tree_items.get(key)
                if item is None:
                    continue
                is_done = self._is_completed_status(rec["status"])
                if mode == "all":
                    item.setHidden(False)
                elif mode == "done":
                    item.setHidden(not is_done)
                else:
                    item.setHidden(is_done)
        finally:
            self.queue_tree.setUpdatesEnabled(True)

    def _refresh_queue_counts_and_cards(self):
        total = len(self._queue_records)
        done_count = 0
        done_bytes = 0
        for rec in self._queue_records.values():
            if self._is_completed_status(rec["status"]):
                done_count += 1
                done_bytes += int(rec["size"] or 0)

        # Incorporate live worker counters if running
        if self.worker is not None and (self._is_running or is_thread_running(self.download_thread)):
            w_total = len(self.worker.files) or total
            total = max(total, w_total)
            w_done = int(self.worker.done + self.worker.skipped)
            if self.worker.verify_only:
                w_done = int(self.worker.verified_ok)
            done_count = max(done_count, min(w_done, total))
            live_bytes = int(self.worker.bytes_done + self.worker.current_downloading_bytes)
            done_bytes = max(done_bytes, live_bytes)

        rem_count = max(total - done_count, 0)
        total_bytes = max(self._total_batch_bytes, done_bytes)
        rem_bytes = max(total_bytes - done_bytes, 0)

        self.btn_qtab_all.setText(f"All Selected ({total})")
        self.btn_qtab_done.setText(f"✓ Downloaded ({done_count})")
        self.btn_qtab_rem.setText(f"⏳ Remaining / Up Next ({rem_count})")

        if total > 0:
            self.val_files.setText(f"{done_count} / {total} files")
            self.val_data.setText(f"{format_bytes(done_bytes)} saved to disk")
            self.val_remaining_files.setText(f"{rem_count} file{'s' if rem_count != 1 else ''} left")
            self.val_remaining_bytes.setText(f"{format_bytes(rem_bytes)} remaining")
            self.btn_step_3.setText(f"3. Transfers ({done_count}/{total})")
        else:
            self.val_files.setText("0 files")
            self.val_data.setText("0 B saved to disk")
            self.val_remaining_files.setText("0 files left")
            self.val_remaining_bytes.setText("0 B remaining")
            self.btn_step_3.setText("3. Transfers")
        self._refresh_wizard_pill_geometry()

        # Live ETA calculation when actively transferring
        if (
            self.worker is not None
            and (self._is_running or is_thread_running(self.download_thread))
            and getattr(self.worker, "instant_speed", 0.0) > 0
            and rem_bytes > 0
            and not self.is_download_paused
        ):
            eta_secs = int(rem_bytes / max(self.worker.instant_speed, 1.0))
            if eta_secs < 60:
                self.val_eta.setText(f"• ETA ~{max(eta_secs, 1)}s")
            else:
                mins, secs = divmod(eta_secs, 60)
                self.val_eta.setText(f"• ETA ~{mins:02d}:{secs:02d}")
        else:
            self.val_eta.setText("")

    def _find_queue_key(self, folder_display: str | None, file_display: str) -> str | None:
        if folder_display is not None:
            exact = self._make_queue_key(folder_display, file_display)
            if exact in self._queue_records:
                return exact
        # Fallback match by file name preferring non-completed entries
        for key, rec in self._queue_records.items():
            if rec["name"] == file_display and not self._is_completed_status(rec["status"]):
                return key
        for key, rec in self._queue_records.items():
            if rec["name"] == file_display:
                return key
        return None

    def _set_queue_item_status(
        self,
        key: str,
        status: str,
        progress: int | None = None,
        move_to_end: bool = False,
    ):
        rec = self._queue_records.get(key)
        item = self._queue_tree_items.get(key)
        if rec is None or item is None:
            return

        rec["status"] = status
        if progress is not None:
            rec["progress"] = progress
        sz_str = format_bytes(rec["size"])

        if status == "downloading":
            pct = rec["progress"]
            label = f"⬇ Downloading ({pct}%) • {sz_str}"
        elif status == "verifying":
            pct = rec["progress"]
            label = f"🔍 Verifying ({pct}%) • {sz_str}"
        elif status == "done":
            verified_tag = " & Verified" if self.check_verify_integrity.isChecked() else ""
            label = f"✓ Downloaded{verified_tag} • {sz_str}"
        elif status == "skipped":
            label = f"✓ Already Exists • {sz_str}"
        elif status == "verified":
            label = f"✓ Verified Intact • {sz_str}"
        elif status == "error":
            label = f"❌ Failed / Corrupted • {sz_str}"
        else:
            label = f"⏳ Queued • {sz_str}"

        item.setText(2, label)
        self._style_queue_row(item, status)

        if move_to_end:
            idx = self.queue_tree.indexOfTopLevelItem(item)
            if idx >= 0:
                taken = self.queue_tree.takeTopLevelItem(idx)
                if taken is not None:
                    self.queue_tree.addTopLevelItem(taken)

        is_done = self._is_completed_status(status)
        if self.queue_filter_mode == "done":
            item.setHidden(not is_done)
        elif self.queue_filter_mode == "rem":
            item.setHidden(is_done)
        else:
            item.setHidden(False)

        self._refresh_queue_counts_and_cards()

    def _update_queue_from_log(self, raw_text: str):
        if not self._queue_records:
            return

        for line in raw_text.splitlines():
            clean = line.strip()
            if not clean:
                continue

            m = self._RE_START_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    self._active_queue_key = key
                    self._set_queue_item_status(key, "downloading", progress=0)
                continue

            m = self._RE_DONE_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    if self._active_queue_key == key:
                        self._active_queue_key = ""
                    self._set_queue_item_status(key, "done", progress=100)
                continue

            m = self._RE_SKIP_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    self._set_queue_item_status(key, "skipped", progress=100)
                continue

            m = self._RE_VERIFIED_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    if self._active_queue_key == key:
                        self._active_queue_key = ""
                    self._set_queue_item_status(key, "verified", progress=100)
                continue

            m = self._RE_QUEUE_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    if self._active_queue_key == key:
                        self._active_queue_key = ""
                    self._set_queue_item_status(key, "queued", progress=0, move_to_end=True)
                continue

            m = self._RE_REQUEUED_ONLY.match(clean)
            if m:
                key = self._find_queue_key(None, m.group(1))
                if key:
                    if self._active_queue_key == key:
                        self._active_queue_key = ""
                    self._set_queue_item_status(key, "queued", progress=0, move_to_end=True)
                continue

            m = self._RE_ERROR_FILE.match(clean)
            if m:
                key = self._find_queue_key(m.group(1), m.group(2))
                if key:
                    if self._active_queue_key == key:
                        self._active_queue_key = ""
                    self._set_queue_item_status(key, "error")
                continue

    # ==========================================================================
    # Account & Feature State Management
    # ==========================================================================
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
            self.set_auth_badge("● Connected", "connected")
            self.btn_oauth_login.setText("🔄  Switch")
            self.btn_oauth_login.setProperty("class", "btn-secondary")
            self._repolish(self.btn_oauth_login)
            self.btn_logout.setVisible(True)
            self.login_banner.setVisible(False)
        else:
            self.account_name_label.setText("No Dropbox account connected")
            self.account_sub_label.setText("Sign in to your Dropbox account")
            self.set_auth_badge("○ Not Logged In", "neutral")
            self.btn_oauth_login.setText("🌐  Log In")
            self.btn_oauth_login.setProperty("class", "btn-primary")
            self._repolish(self.btn_oauth_login)
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
            self.target_card.setEnabled(False)
            self.recent_card.setEnabled(False)
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
            self.check_verify_integrity.setEnabled(False)
            self.check_auto_repair.setEnabled(False)
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
            self.recent_card.setEnabled(not active)
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
            self.check_verify_integrity.setEnabled(not is_running)
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

            if self.tree_widget.topLevelItemCount() == 1:
                item = self.tree_widget.topLevelItem(0)
                if item and item.data(0, Qt.ItemDataRole.UserRole) is None:
                    self.show_empty_tree_placeholder()
                    if not self.url_input.text().strip():
                        self.set_selection_summary("(Paste link in Step 1 to inspect folders)", "neutral")

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
            self.btn_verify_files.setVisible(False)
            self.btn_view_active_transfer.setVisible(True)
            self.pause_button.setVisible(True)
            self.stop_button.setVisible(True)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            return

        self.pause_button.setVisible(False)
        self.stop_button.setVisible(False)
        self.btn_view_active_transfer.setVisible(False)
        self.start_button.setVisible(True)
        self.btn_verify_files.setVisible(True)

        if not logged_in:
            self.start_button.setEnabled(False)
            self.start_button.setText("🔒  Log In to Start")
            self.btn_verify_files.setEnabled(False)
            return

        if is_scanning:
            self.start_button.setEnabled(False)
            self.start_button.setText("⏳  Loading Folders...")
            self.btn_verify_files.setEnabled(False)
            return

        url = self.url_input.text().strip()
        has_link = bool(url and ("dropbox.com" in url) and ("http://" in url or "https://" in url))

        info = self.get_tree_selection_info()
        has_tree = info.get("has_tree_items", False)
        selected_count = info.get("selected_file_count", 0)
        selected_bytes = info.get("selected_bytes", 0)

        can_verify = bool(has_link and has_tree and selected_count > 0)
        self.btn_verify_files.setEnabled(can_verify)
        if can_verify:
            self.btn_verify_files.setText(f"🔍  Verify Existing ({selected_count})")
        else:
            self.btn_verify_files.setText("🔍  Verify Existing")

        if not has_link:
            self.start_button.setEnabled(False)
            self.start_button.setText("📋  Paste Link && Select Files to Start")
        elif not has_tree:
            self.start_button.setEnabled(False)
            self.start_button.setText("🔍  Load Folders to Select Files")
        elif selected_count == 0:
            self.start_button.setEnabled(False)
            self.start_button.setText("☑  Select Files to Start")
        else:
            self.start_button.setEnabled(True)
            size_part = f" • {format_bytes(selected_bytes)}" if selected_bytes > 0 else ""
            self.start_button.setText(
                f"⬇  Start Download ({selected_count} file{'s' if selected_count != 1 else ''}{size_part}) →"
            )

    def toggle_pause_download(self):
        if self.worker:
            self.worker.toggle_pause()

    def on_download_paused_changed(self, is_paused: bool):
        self.is_download_paused = is_paused
        if is_paused:
            self.pause_button.setText("▶  Resume Download")
            self.pause_button.setProperty("class", "btn-resume")
            self._repolish(self.pause_button)
            self.set_status_badge("⏸ Paused", "warning")
            self.val_speed.setText("Paused")
            self.val_eta.setText("")
            self.add_log("⏸ Download paused.")
        else:
            self.pause_button.setText("⏸  Pause Download")
            self.pause_button.setProperty("class", "btn-pause")
            self._repolish(self.pause_button)
            self.set_status_badge("● Downloading...", "running")
            self.add_log("▶ Download resumed.")

    # ==========================================================================
    # Recent Links Management (Chips + Detailed Recent Rows + Dropdown Menu)
    # ==========================================================================
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
            if existing and existing.get("title") and existing.get("title").strip().lower() not in junk_titles:
                clean_title = existing.get("title").strip()
            elif hasattr(self, "current_root_name") and self.current_root_name and self.current_root_name.strip().lower() not in junk_titles:
                clean_title = self.current_root_name.strip()
            elif hasattr(self, "tree_widget") and self.tree_widget.topLevelItemCount() > 0:
                top = self.tree_widget.topLevelItem(0)
                if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                    raw = top.data(3, Qt.ItemDataRole.UserRole) or ""
                    if raw and raw.strip().lower() not in junk_titles:
                        clean_title = raw.strip()
            if not clean_title:
                clean_title = extract_folder_name_from_url(url)
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

    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()

    def update_recent_links_ui(self):
        if not hasattr(self, "recent_chips_layout") or not hasattr(self, "recent_rows_layout"):
            return

        self._clear_layout(self.recent_chips_layout)
        self._clear_layout(self.recent_rows_layout)

        if not self.recent_links:
            self.recent_chips_container.setVisible(False)
            empty_lbl = QLabel("Your recently opened Dropbox folders will appear here for 1-click access.")
            empty_lbl.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent; padding: 6px 0px;")
            self.recent_rows_layout.addWidget(empty_lbl)
            return

        # 1. Quick Recent Chips Row
        for item in self.recent_links[:4]:
            title = item.get("title") or "Dropbox Folder"
            display_name = (title[:22] + "…") if len(title) > 24 else title
            safe_chip_text = display_name.replace("&", "&&")

            chip_btn = QPushButton(f"📁 {safe_chip_text}")
            chip_btn.setProperty("class", "recent-chip")
            chip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tooltip_txt = f"📁 {title}\n🔗 {item.get('url', '')}\n📅 Saved: {item.get('date_str', '')}"
            if item.get("item_count"):
                tooltip_txt += f"\n📊 {item.get('item_count')} items"
            chip_btn.setToolTip(tooltip_txt)

            chip_url = item.get("url", "")
            chip_btn.clicked.connect(lambda _, u=chip_url: self.load_recent_link(u))
            self.recent_chips_layout.addWidget(chip_btn)

        self.recent_chips_layout.addStretch()
        self.recent_chips_container.setVisible(True)

        # 2. Detailed Recent Rows (top 3)
        for idx, item in enumerate(self.recent_links[:3]):
            title = item.get("title") or "Dropbox Folder"
            url = item.get("url", "")
            cnt = item.get("item_count")
            meta_parts = []
            if cnt:
                meta_parts.append(f"{cnt} items")
            if item.get("date_str"):
                meta_parts.append(item.get("date_str"))
            meta_suffix = f"  •  {' • '.join(meta_parts)}" if meta_parts else ""
            short_url = url if len(url) <= 72 else (url[:69] + "...")

            row_widget = _RecentLinkRow(
                title_text=f"📂 {title}{meta_suffix}",
                url_text=short_url,
                show_top_border=(idx > 0),
            )
            row_widget.setToolTip(url)
            row_widget.clicked.connect(lambda u=url: self.load_recent_link(u))
            self.recent_rows_layout.addWidget(row_widget)

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
                title = (item.get("title") or "Dropbox Folder").replace("&", "&&")
                url = item.get("url", "")
                cnt = item.get("item_count")
                cnt_txt = f"  ({cnt} items)" if cnt else ""
                date_txt = f"  •  {item.get('date_str', '')}" if item.get("date_str") else ""
                short_url = (url[:60] + ("..." if len(url) > 60 else "")).replace("&", "&&")
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

    # ==========================================================================
    # Settings Persistence & Worker Cleanup
    # ==========================================================================
    def load_settings(self):
        saved_theme = str(self.settings.value("theme_mode", "light")).strip().lower()
        self.apply_theme(saved_theme if saved_theme in ("light", "dark") else "light", save=False)

        saved_dest = str(self.settings.value("destination", str(Path.home() / "Downloads")))
        if saved_dest:
            self.destination_input.setText(saved_dest)

        skip_raw = self.settings.value("skip_existing", True)
        self.check_skip_existing.setChecked(str(skip_raw).lower() in ("true", "1"))

        verify_raw = self.settings.value("verify_integrity", True)
        self.check_verify_integrity.setChecked(str(verify_raw).lower() in ("true", "1"))
        self._on_verify_setting_changed()

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
            self.add_log("🔒 Welcome! Please sign into your Dropbox account to unlock features.")

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
        self.settings.setValue("theme_mode", self.theme_mode)
        self.settings.setValue("destination", self.destination_input.text().strip())
        self.settings.setValue("skip_existing", self.check_skip_existing.isChecked())
        self.settings.setValue("verify_integrity", self.check_verify_integrity.isChecked())
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

            self.btn_oauth_login.setEnabled(True)
            self.btn_banner_login.setEnabled(True)
            self.btn_banner_login.setText("🌐  Log In to Dropbox")

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
            self.btn_oauth_login.setEnabled(True)
            self.btn_banner_login.setEnabled(True)
            self.btn_banner_login.setText("🌐  Log In to Dropbox")
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
            self.close_settings_drawer()
            self.go_to_step(0)
            self.add_log("🔒 Logged out of Dropbox account. All features are now disabled.")

    def toggle_log_visibility(self):
        if not self.log_box.isHidden():
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
                ["🔒 Please log in to Dropbox to inspect and download folders", "—", "—"],
            )
        else:
            placeholder = QTreeWidgetItem(
                self.tree_widget,
                ["Paste a Dropbox link in Step 1 and click 'Load Folders →'", "—", "—"],
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
        self.current_root_name = ""
        self._tree_items_data = []
        self._scanned_url = ""
        self.step2_folder_label.setText("📂 Shared Folder")
        self.btn_step_2.setText("2. Select Files")
        self.show_empty_tree_placeholder()
        self.rebuild_queue_from_selection()
        if self.is_logged_in():
            self.set_selection_summary("(Paste link in Step 1 to inspect folders)", "neutral")
        else:
            self.set_selection_summary("(Sign in required)", "neutral")
        self.update_download_button_state()
        self.go_to_step(0)

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Local Download Destination",
            self.destination_input.text().strip() or str(Path.home()),
        )
        if folder:
            self.destination_input.setText(folder)
            self.save_settings()
            if not self._is_running:
                self.rebuild_queue_from_selection()

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
            ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a valid Dropbox shared link to inspect folders."
            )
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
        self.btn_scan_url.setText("Load Folders →")

        self.current_root_name = root_name
        self.step2_folder_label.setText(f"📂 {root_name}")
        self._tree_items_data = entries
        url = self.url_input.text().strip()
        self._scanned_url = url
        self.populate_tree_widget(tree_dict, root_name)

        folders_count = sum(1 for e in entries if e.get("is_dir"))
        files_count = sum(1 for e in entries if not e.get("is_dir"))
        total_size = sum(e.get("size", 0) for e in entries if not e.get("is_dir"))

        self.add_log(
            f"✓ Found {len(entries)} items ({folders_count} folder(s), {files_count} file(s), {format_bytes(total_size)})"
        )
        self.update_selection_summary()
        self.add_recent_link(url, title=root_name, item_count=len(entries))
        self.update_feature_enabled_state()
        self.update_download_button_state()

        # Automatically advance to Step 2 (Select Files)
        self.go_to_step(1)

    def on_scan_failed(self, error: str):
        self.scan_thread = None
        self.scan_worker = None
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("Load Folders →")

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

                if is_dir:
                    icon_str = "📁 "
                    file_cnt = int(node_data.get("file_count") or 0)
                    folder_cnt = len([c for c in node_data.get("children", {}).values() if c.get("is_dir")])
                    if file_cnt > 0 and folder_cnt > 0:
                        type_str = f"Folder ({file_cnt} {'file' if file_cnt == 1 else 'files'}, {folder_cnt} {'subfolder' if folder_cnt == 1 else 'subfolders'})"
                    elif file_cnt > 0:
                        type_str = f"Folder ({file_cnt} {'file' if file_cnt == 1 else 'files'})"
                    elif folder_cnt > 0:
                        type_str = f"Folder ({folder_cnt} {'subfolder' if folder_cnt == 1 else 'subfolders'})"
                    else:
                        type_str = "Folder (empty)"
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
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0])),
                ):
                    add_item_recursive(item, child_data)

            if tree_dict["children"]:
                for child_name, child_data in sorted(
                    tree_dict["children"].items(),
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0])),
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
                new_state = (
                    Qt.CheckState.Unchecked
                    if current_state == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
                item.setCheckState(0, new_state)

    def show_tree_context_menu(self, point):
        item = self.tree_widget.itemAt(point)
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        menu = QMenu(self)
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
            is_checked = item.checkState(0) == Qt.CheckState.Checked
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
        raw_name = (
            current.data(3, Qt.ItemDataRole.UserRole)
            or current.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "")
        )
        if is_dir:
            child_count = current.childCount()
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            size_str = f" • {format_bytes(size)}" if size > 0 else ""
            status = "open — click to collapse" if current.isExpanded() else "closed — click to expand"
            self.tree_hint.setText(f"📁 Folder: {raw_name} ({child_count} items{size_str}) [{status}]")
        else:
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            self.tree_hint.setText(f"📄 File: {raw_name} ({format_bytes(size) if size > 0 else '0 B'})")

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
            self.set_selection_summary("(No items scanned yet)", "neutral")
            self.btn_step_2.setText("2. Select Files")
        elif total_files == 0:
            folder_str = f"{selected_folders} of {total_folders} folder{'s' if total_folders != 1 else ''} selected"
            self.set_selection_summary(folder_str, "success" if selected_folders > 0 else "neutral")
            self.btn_step_2.setText(f"2. Select Files ({selected_folders})")
        else:
            summary_txt = f"{selected_files} of {total_files} file{'s' if total_files != 1 else ''} selected"
            if selected_bytes > 0:
                summary_txt += f" • {format_bytes(selected_bytes)}"
            self.set_selection_summary(summary_txt, "success" if selected_files > 0 else "neutral")
            self.btn_step_2.setText(f"2. Select Files ({selected_files})")
        self._refresh_wizard_pill_geometry()

        if not self._is_running:
            self.rebuild_queue_from_selection()

        self.update_download_button_state()

    def get_tree_selection_info(self) -> dict[str, Any]:
        selected_files = set()
        deselected_files = set()
        selected_folders = set()
        deselected_folders = set()
        total_files = 0
        total_selected_files = 0
        selected_bytes = 0
        has_tree_items = False

        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            if top_item is not None and top_item.data(0, Qt.ItemDataRole.UserRole) is not None:
                has_tree_items = True
                break

        def traverse(item: QTreeWidgetItem | None, parent_path=""):
            nonlocal total_files, total_selected_files, selected_bytes
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
            raw_name = (
                item.data(3, Qt.ItemDataRole.UserRole)
                or item.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "").strip()
            )
            item_path = item.data(0, Qt.ItemDataRole.UserRole) or ""
            size = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)

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
                    selected_bytes += size
                    if item_path:
                        selected_files.add(item_path)
                    selected_files.add(current_path)
                else:
                    if item_path:
                        deselected_files.add(item_path)
                    deselected_files.add(current_path)

        for i in range(self.tree_widget.topLevelItemCount()):
            traverse(self.tree_widget.topLevelItem(i))

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
            "selected_bytes": selected_bytes,
            "has_tree_items": has_tree_items,
        }

    # ==========================================================================
    # Activity Logging, Download Execution & Live Transfer Telemetry
    # ==========================================================================
    @Slot(str)
    def add_log(self, text: str):
        self._update_queue_from_log(text)
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
        self.btn_verify_files.setEnabled(not running)
        self.update_feature_enabled_state()

        if running:
            self.realtime_stats_timer.start()
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if "verifying" not in curr.lower():
                self.set_status_badge("● Downloading...", "running")
        else:
            self.realtime_stats_timer.stop()
            self.tick_realtime_stats()
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if not any(k in curr.lower() for k in ("completed", "warning", "error", "stopped")):
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
        verify_integrity = self.check_verify_integrity.isChecked()
        auto_repair = self.check_auto_repair.isChecked()
        link_password = (self.link_password or "").strip()

        if not url:
            ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a Dropbox shared link before downloading."
            )
            self.go_to_step(0)
            self.url_input.setFocus()
            return

        if not destination:
            ModernMessageBox.warning(
                self, "Missing Destination", "Please choose a local save destination folder in ⚙️ Settings."
            )
            self.open_settings_drawer()
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
        self.close_settings_drawer()

        root_name = getattr(self, "current_root_name", "")
        if not root_name and self.tree_widget.topLevelItemCount() > 0:
            top = self.tree_widget.topLevelItem(0)
            if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                root_name = top.data(3, Qt.ItemDataRole.UserRole) or ""
        self.add_recent_link(url, title=root_name, item_count=info.get("selected_file_count", 0))

        self.rebuild_queue_from_selection()
        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Initializing...")
        self.file_label.setText("Connecting to Dropbox API...")
        self.val_speed.setText("0 B/s")
        self.val_time.setText("00:00")
        self.val_eta.setText("")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        self._repolish(self.pause_button)

        self.set_running(True)
        self.go_to_step(2)

        self.add_log("▶ Starting selective download via Dropbox API...")
        if info["has_tree_items"] and info["total_files"] > 0:
            self.add_log(
                f"📋 Selection: {info['selected_file_count']} of {info['total_files']} files selected for download."
            )

        scanned_entries = None
        if getattr(self, "_tree_items_data", None) and getattr(self, "_scanned_url", None) == url:
            scanned_entries = self._tree_items_data

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
            scanned_entries=scanned_entries,
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
        w.file_changed.connect(self._on_worker_file_changed)
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
            ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a Dropbox shared link before verifying."
            )
            self.go_to_step(0)
            self.url_input.setFocus()
            return

        if not destination:
            ModernMessageBox.warning(
                self, "Missing Destination", "Please choose a local save destination folder in ⚙️ Settings."
            )
            self.open_settings_drawer()
            return

        info = self.get_tree_selection_info()
        if info["has_tree_items"] and info["selected_file_count"] == 0:
            ModernMessageBox.warning(
                self,
                "No Files Selected",
                "Please select at least one file or folder from the tree to verify.",
            )
            return

        self.close_settings_drawer()
        self.rebuild_queue_from_selection()

        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Verifying Files...")
        self.file_label.setText("Connecting to Dropbox API to check metadata...")
        self.val_speed.setText("0 B/s")
        self.val_time.setText("00:00")
        self.val_eta.setText("")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause")
        self.pause_button.setProperty("class", "btn-pause")
        self._repolish(self.pause_button)

        self.set_running(True)
        self.set_status_badge("● Verifying...", "verifying")
        self.go_to_step(2)
        self.add_log("🔍 Starting on-demand file integrity verification...")

        auto_repair = self.check_auto_repair.isChecked()

        scanned_entries = None
        if getattr(self, "_tree_items_data", None) and getattr(self, "_scanned_url", None) == url:
            scanned_entries = self._tree_items_data

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
            scanned_entries=scanned_entries,
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
        w.file_changed.connect(self._on_worker_file_changed)
        w.current_progress.connect(self.update_file_progress)
        w.overall_progress.connect(self.update_overall_progress)
        w.stats_changed.connect(self.update_stats)
        w.paused_signal.connect(self.on_download_paused_changed)

        w.finished.connect(self.download_finished)
        w.failed.connect(self.download_failed)

        t.start()

    @Slot(str)
    def _on_worker_file_changed(self, text: str):
        self.file_label.setText(text)
        if text.startswith("🔍 Verifying file") and self._active_queue_key:
            self._set_queue_item_status(self._active_queue_key, "verifying")

    def update_file_progress(self, val: int):
        self.file_progress.setValue(val)
        self.file_pct_label.setText(f"{val}%")
        if self._active_queue_key and self._active_queue_key in self._queue_records:
            cur_status = self._queue_records[self._active_queue_key]["status"]
            if cur_status in ("downloading", "verifying"):
                self._set_queue_item_status(self._active_queue_key, cur_status, progress=val)

    def update_overall_progress(self, val: int):
        self.overall_progress.setValue(val)
        self.overall_pct_label.setText(f"{val}%")

    def update_stats(self, stats: dict):
        if "speed" in stats:
            self.val_speed.setText(stats["speed"])
        if "elapsed" in stats:
            self.val_time.setText(stats["elapsed"])
        if self.worker is not None:
            self._refresh_queue_counts_and_cards()
        else:
            if "data" in stats:
                self.val_data.setText(f"{stats['data']} saved to disk")
            if "files" in stats:
                self.val_files.setText(stats["files"])

    def tick_realtime_stats(self):
        if self.worker and is_thread_running(self.download_thread):
            try:
                self.worker.emit_stats(force=True)
            except Exception:
                pass

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
            self.val_eta.setText("")
            if self._active_queue_key and self._active_queue_key in self._queue_records:
                if not self._is_completed_status(self._queue_records[self._active_queue_key]["status"]):
                    self._set_queue_item_status(self._active_queue_key, "queued")
                self._active_queue_key = ""
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
            self.val_eta.setText("")
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
            self.val_eta.setText("")
            self._refresh_queue_counts_and_cards()
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
        self.val_eta.setText("")

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
        if hasattr(self, "ad_banner") and self.ad_banner is not None:
            self.ad_banner.cleanup_feed_thread()
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
