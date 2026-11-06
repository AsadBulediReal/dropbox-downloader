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
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv()
except ImportError:
    pass

import dropbox
from dropbox.oauth import DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import ApiError, AuthError

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt, QSettings, QTimer
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QTreeWidgetItem,
)

from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET, get_theme_stylesheet
from .ads import AdBannerWidget
from .utils import is_thread_running
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
from .mw_widgets_theme import (
    _ClickBackdrop,
    _RecentLinkRow,
    _ThemeBadgesMixin,
)
from .mw_ui_drawer import setup_main_window_ui
from .mw_queue import _QueueMixin
from .mw_account_state import _AccountStateMixin
from .mw_recent_links import _RecentLinksMixin
from .mw_settings_session import _SettingsSessionMixin
from .mw_oauth import _OAuthMixin
from .mw_scan_tree import _ScanTreeMixin
from .mw_tree_interactions import _TreeInteractionsMixin
from .mw_tree_selection import _TreeSelectionMixin
from .mw_transfer_start import _TransferStartMixin
from .mw_transfer_status import _TransferStatusMixin


class MainWindow(
    QMainWindow,
    _ThemeBadgesMixin,
    _QueueMixin,
    _AccountStateMixin,
    _RecentLinksMixin,
    _SettingsSessionMixin,
    _OAuthMixin,
    _ScanTreeMixin,
    _TreeInteractionsMixin,
    _TreeSelectionMixin,
    _TransferStartMixin,
    _TransferStatusMixin,
):
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
        self.custom_app_key: str = ""
        self.link_password: str = ""
        self.recent_links: list[dict[str, Any]] = []
        self._loading_settings: bool = False
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
        self._transfer_notice_state: str = "success"

        self.auto_scan_timer = QTimer(self)
        self.auto_scan_timer.setSingleShot(True)
        self.auto_scan_timer.timeout.connect(self.auto_scan_if_valid)

        self.realtime_stats_timer = QTimer(self)
        self.realtime_stats_timer.setInterval(250)
        self.realtime_stats_timer.timeout.connect(self.tick_realtime_stats)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        setup_main_window_ui(self)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if hasattr(self, "settings_overlay") and self.settings_overlay is not None:
            self.settings_overlay.setGeometry(self.rect())

    @Slot(str, str)
    def on_verify_finished(self, name: str, email: str):
        self._on_verify_finished_impl(name, email)

    @Slot(str)
    def on_verify_expired(self, exc_msg: str):
        self._on_verify_expired_impl(exc_msg)

    @Slot(str)
    def on_verify_failed(self, exc_msg: str):
        self._on_verify_failed_impl(exc_msg)

    @Slot(str)
    def on_auth_status(self, msg: str):
        self._on_auth_status_impl(msg)

    @Slot(str)
    def on_scan_status(self, text: str):
        self._on_scan_status_impl(text)

    @Slot(str)
    def add_log(self, text: str):
        self._add_log_impl(text)

    @Slot(str)
    def _on_worker_file_changed(self, text: str):
        self._on_worker_file_changed_impl(text)

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
