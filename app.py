import os
import sys
import time
import re
import json
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import dropbox
from dropbox.files import FileMetadata, FolderMetadata, SharedLink
from dropbox.exceptions import ApiError, AuthError

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt, QSettings, QTimer
from PySide6.QtGui import QFont, QTextCursor, QCursor, QColor
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
    QHeaderView,
    QInputDialog,
    QDialog,
    QMenu,
)


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


def format_bytes(value: Any) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    try:
        size = float(value)
    except (ValueError, TypeError):
        return "0 B"
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    return sanitized or "DropboxDownload"


def extract_folder_name_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path).strip("/")
        parts = [p.strip() for p in path.split("/") if p.strip()]
        # /scl/fo/<id>/... paths contain an opaque internal ID, not the folder name
        if "scl" in parts and "fo" in parts:
            return ""
        ignore_parts = {"scl", "fo", "fi", "sh", "s", "h", "dl", "home", "personal", "work"}
        valid_parts = [p for p in parts if p.lower() not in ignore_parts and len(p) > 2]
        if valid_parts:
            candidate = valid_parts[-1]
            if candidate.lower() not in ignore_parts:
                if re.match(r'^[a-zA-Z0-9_-]{16,}$', candidate) and any(c.isdigit() for c in candidate) and any(c.isalpha() for c in candidate):
                    return ""
                return sanitize_filename(candidate)
    except Exception:
        pass
    return ""


def parse_friendly_error(error: Any) -> tuple[str, str]:
    err_str = str(error or "").strip()
    err_lower = err_str.lower()

    # 1. Broken / Not found / Expired link
    if any(k in err_lower for k in (
        "shared_link_not_found", "link_not_found", "not_found", "does not exist",
        "could not find", "endpoint_not_found", "path/not_found"
    )):
        return (
            "Link Not Working",
            "This Dropbox link is not working or could not be found.\n\n"
            "• The shared link may have been deleted, expired, or mistyped.\n"
            "• Please ensure you copied the full Dropbox shared link correctly."
        )

    # 2. Password protected / Access denied
    if any(k in err_lower for k in ("password", "requires_password")):
        return (
            "Password Required",
            "This Dropbox shared folder is protected with a password.\n\n"
            "Please enter the link password to view and download files."
        )

    if any(k in err_lower for k in ("shared_link_access_denied", "access_denied", "access denied", "permission_denied")):
        return (
            "Access Restricted",
            "Access to this Dropbox link is restricted.\n\n"
            "• You may not have permission to view or download this content.\n"
            "• If this folder requires a password, please provide it."
        )

    # 3. Invalid link / malformed URL
    if any(k in err_lower for k in (
        "invalid dropbox", "valid dropbox shared url", "invalid_shared_link",
        "malformed_path", "unsupported_link_type"
    )):
        return (
            "Invalid Dropbox Link",
            "The entered address is not a valid Dropbox link.\n\n"
            "Please paste a link starting with https://www.dropbox.com/scl/... or https://www.dropbox.com/sh/..."
        )

    # 4. Authentication / Session expired
    if any(k in err_lower for k in (
        "expired_access_token", "invalid_access_token", "autherror",
        "sign in with your dropbox account", "session expired", "invalid or expired"
    )):
        return (
            "Sign-In Required",
            "Your Dropbox sign-in session is missing or has expired.\n\n"
            "Please click 'Disconnect' (or 'Sign in with Dropbox') above to reconnect your account."
        )

    # 5. Network / Offline / Connection errors
    if any(k in err_lower for k in (
        "connectionerror", "max retries exceeded", "failed to establish a new connection",
        "getaddrinfo failed", "nodename nor servname provided", "network is unreachable",
        "name or service not known", "dns_probe"
    )):
        return (
            "Network Connection Error",
            "Could not connect to Dropbox servers.\n\n"
            "Please check your internet connection and verify that you are online."
        )

    # 6. Timeout
    if "timeout" in err_lower or "timed out" in err_lower:
        return (
            "Connection Timed Out",
            "The request to Dropbox took too long to complete.\n\n"
            "Please check your network speed and try again."
        )

    # 7. SSL / Firewall
    if "sslerror" in err_lower or "certificate verify failed" in err_lower:
        return (
            "Secure Connection Failed",
            "Could not establish a secure SSL connection to Dropbox.\n\n"
            "Please check if a VPN, proxy, or antivirus firewall is blocking Dropbox."
        )

    # 8. Rate Limiting / 429
    if any(k in err_lower for k in ("ratelimit", "too_many_requests", "too_many_write_operations", "429")):
        return (
            "Dropbox Busy",
            "Dropbox is temporarily rate limiting requests due to high traffic.\n\n"
            "Please wait a minute or two and try again."
        )

    # 9. Local disk & file system
    if any(k in err_lower for k in ("permission denied", "access is denied", "winerror 5")):
        return (
            "Permission Denied",
            "Cannot write to the selected destination folder.\n\n"
            "Please choose a local folder with write permissions (e.g. your Downloads or Documents folder)."
        )

    if any(k in err_lower for k in ("no space left on device", "enospc", "disk full")):
        return (
            "Disk Full",
            "There is not enough free storage space on your hard drive.\n\n"
            "Please free up disk space or choose a different save drive."
        )

    if "unsafe dropbox path" in err_lower:
        return (
            "Invalid Destination Path",
            "The save destination path is invalid.\n\n"
            "Please choose a standard local folder on your computer."
        )

    # 10. File size mismatch
    if "size mismatch" in err_lower:
        return (
            "Download Interrupted",
            "A file download was interrupted before completing.\n\n"
            "Please click 'Start Download' again to resume downloading the remaining files."
        )

    # Clean fallback
    cleaned = err_str
    cleaned = re.sub(r'^[a-zA-Z0-9_.]+(?:Error|Exception)\s*:\s*', '', cleaned)
    cleaned = re.sub(r'^ApiError\([\'"][^\'"]*[\'"],\s*', '', cleaned).rstrip(')')
    if not cleaned or len(cleaned) < 3:
        cleaned = "An unexpected error occurred while communicating with Dropbox."

    return (
        "Dropbox Error",
        f"{cleaned}\n\nPlease verify your link and connection, then try again."
    )


def safe_local_path(root: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").strip("/")
    parts = []
    for p in normalized.split("/"):
        p = p.strip()
        if not p or p in (".", ".."):
            continue
        clean_part = re.sub(r'[<>:"/\\|?*]', '_', p).strip('. ')
        if clean_part:
            parts.append(clean_part)
    destination = root.joinpath(*parts).resolve()
    root_resolved = root.resolve()
    try:
        destination.relative_to(root_resolved)
    except ValueError:
        raise ValueError(f"Unsafe Dropbox path: {relative_path}")
    return destination


def relative_path(entry: Any) -> str:
    if hasattr(entry, "rel_path"):
        return entry.rel_path
    path = getattr(entry, "path_display", None)
    return path.lstrip("/") if path else getattr(entry, "name", "")


def get_file_type_and_icon(filename: str) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.tiff'):
        return f"{ext[1:].upper()} Image" if ext else "Image", "🖼️ "
    elif ext in ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'):
        return f"{ext[1:].upper()} Video" if ext else "Video", "🎬 "
    elif ext in ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'):
        return f"{ext[1:].upper()} Audio" if ext else "Audio", "🎵 "
    elif ext in ('.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.xz'):
        return f"{ext[1:].upper()} Archive" if ext else "Archive", "📦 "
    elif ext in ('.pdf',):
        return "PDF Document", "📕 "
    elif ext in ('.doc', '.docx', '.odt'):
        return "Word Document", "📘 "
    elif ext in ('.xls', '.xlsx', '.csv'):
        return "Spreadsheet", "📊 "
    elif ext in ('.ppt', '.pptx'):
        return "Presentation", "📙 "
    elif ext in ('.txt', '.md', '.rtf', '.log', '.json', '.xml', '.yaml', '.yml', '.py', '.js', '.ts', '.html', '.css'):
        return f"{ext[1:].upper()} Text" if ext else "Text File", "📝 "
    elif ext in ('.exe', '.msi', '.apk'):
        return "Executable", "⚙️ "
    else:
        return f"{ext[1:].upper()} File" if ext else "File", "📄 "


def build_tree_hierarchy(entries: list, root_name: str = "DropboxFolder") -> dict[str, Any]:
    root: dict[str, Any] = {
        "name": root_name,
        "path": "",
        "is_dir": True,
        "size": 0,
        "total_size": 0,
        "file_count": 0,
        "folder_count": 0,
        "children": {},
    }
    for item in entries:
        raw_path = item.get("path", "").replace("\\", "/").strip("/")
        if not raw_path:
            continue
        parts = [p.strip() for p in raw_path.split("/") if p.strip()]
        if not parts:
            continue

        if len(parts) > 1 and parts[0].lower() == root_name.lower():
            parts = parts[1:]
        elif len(parts) == 1 and parts[0].lower() == root_name.lower() and item.get("is_dir"):
            continue

        curr: dict[str, Any] = root
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            children: dict[str, Any] = curr["children"]
            if part not in children:
                children[part] = {
                    "name": part,
                    "path": "/".join(parts[:i + 1]),
                    "is_dir": item["is_dir"] if is_last else True,
                    "size": item.get("size", 0) if is_last else 0,
                    "total_size": 0,
                    "file_count": 0,
                    "folder_count": 0,
                    "children": {},
                }
            elif is_last:
                children[part]["is_dir"] = item["is_dir"]
                children[part]["size"] = item.get("size", 0)
            curr = children[part]

    def compute_metrics(node: dict[str, Any]) -> tuple[int, int]:
        if not node["is_dir"]:
            return int(node.get("size", 0) or 0), 1
        total_sz = 0
        total_fl = 0
        total_fo = 0
        for child in node["children"].values():
            c_sz, c_fl = compute_metrics(child)
            total_sz += c_sz
            total_fl += c_fl
            if child["is_dir"]:
                total_fo += 1
        node["total_size"] = total_sz
        node["file_count"] = total_fl
        node["folder_count"] = total_fo
        return total_sz, total_fl

    compute_metrics(root)
    return root


def is_path_selected(
    candidate_path: str,
    selected_files: set,
    deselected_files: set,
    selected_folders: set,
    deselected_folders: set,
    has_tree_filter: bool = True,
) -> bool:
    if not has_tree_filter:
        return True

    norm = candidate_path.replace("\\", "/").strip("/")
    if not norm:
        return False

    parts = [p for p in norm.split("/") if p]
    if not parts:
        return False

    all_suffixes = ["/".join(parts[i:]) for i in range(len(parts))]

    for suffix in all_suffixes:
        if suffix in deselected_files:
            return False

    for suffix in all_suffixes:
        if suffix in selected_files:
            return True

    for suffix in all_suffixes:
        if suffix in deselected_folders:
            return False

    for suffix in all_suffixes:
        if suffix in selected_folders:
            return True

    for i in range(len(parts) - 1, 0, -1):
        ancestor = "/".join(parts[:i])
        for suffix in ["/".join(ancestor.split("/")[j:]) for j in range(len(ancestor.split("/")))]:
            if suffix in deselected_folders:
                return False
            if suffix in selected_folders:
                return True

    if selected_files or selected_folders:
        return False

    return True


def create_dropbox_client(
    access_token: str | None = None,
    refresh_token: str | None = None,
    app_key: str | None = None,
) -> dropbox.Dropbox:
    """Create an authenticated Dropbox client, supporting OAuth PKCE refresh tokens."""
    r_token = (refresh_token or "").strip()
    a_token = (access_token or "").strip()
    k = (app_key or "").strip()

    if r_token and k:
        return dropbox.Dropbox(
            oauth2_access_token=a_token or None,
            oauth2_refresh_token=r_token,
            app_key=k,
        )
    if a_token:
        return dropbox.Dropbox(oauth2_access_token=a_token)
    raise ValueError("Not authenticated. Please sign in with your Dropbox account first.")


# ==============================================================================
# Auth Worker (Authenticates via OAuth PKCE in background thread)
# ==============================================================================
class AuthWorker(QObject):
    finished = Signal(str, str, str, str)  # access_token, refresh_token, user_name, user_email
    failed = Signal(str)
    status = Signal(str)
    progress = Signal(int)

    def __init__(self, flow: Any, code: str, app_key: str):
        super().__init__()
        self.flow = flow
        self.code = code.strip()
        self.app_key = app_key.strip()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    @Slot()
    def run(self):
        try:
            self.status.emit("Exchanging authorization code with Dropbox...")
            self.progress.emit(25)
            oauth_res: Any = self.flow.finish(self.code)
            if self._is_cancelled:
                return

            access_token = getattr(oauth_res, "access_token", None) or ""
            refresh_token = getattr(oauth_res, "refresh_token", None) or ""

            self.status.emit("Connecting to Dropbox API...")
            self.progress.emit(55)
            dbx = create_dropbox_client(
                access_token=access_token,
                refresh_token=refresh_token,
                app_key=self.app_key,
            )
            if self._is_cancelled:
                return

            self.status.emit("Retrieving account profile...")
            self.progress.emit(80)
            account: Any = dbx.users_get_current_account()
            if self._is_cancelled:
                return

            user_name = (
                account.name.display_name
                if account and hasattr(account, "name") and account.name
                else "Dropbox User"
            )
            user_email = account.email if account and hasattr(account, "email") else ""

            self.status.emit("Completing sign in...")
            self.progress.emit(95)
            self.finished.emit(access_token, refresh_token, user_name, user_email)
        except Exception as exc:
            if not self._is_cancelled:
                self.failed.emit(str(exc))


class SessionVerifyWorker(QObject):
    finished = Signal(str, str)  # user_name, user_email
    expired = Signal(str)
    failed = Signal(str)

    def __init__(self, access_token: str, refresh_token: str, app_key: str):
        super().__init__()
        self.access_token = access_token.strip()
        self.refresh_token = refresh_token.strip()
        self.app_key = app_key.strip()

    @Slot()
    def run(self):
        try:
            dbx = create_dropbox_client(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                app_key=self.app_key,
            )
            account: Any = dbx.users_get_current_account()
            user_name = (
                account.name.display_name
                if account and hasattr(account, "name") and account.name
                else "Dropbox User"
            )
            user_email = account.email if account and hasattr(account, "email") else ""
            self.finished.emit(user_name, user_email)
        except AuthError as exc:
            self.expired.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))


# ==============================================================================
# Scan Worker (Inspects folders via Dropbox API)
# ==============================================================================
class ScanWorker(QObject):
    finished = Signal(dict, str, list)  # tree_dict, root_name, entries_list
    failed = Signal(str)
    status = Signal(str)

    def __init__(
        self,
        url: str,
        token: str = "",
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_key: str | None = None,
    ):
        super().__init__()
        self.url = url.strip()
        self.access_token = (access_token or token or "").strip()
        self.refresh_token = (refresh_token or "").strip()
        self.app_key = (app_key or "").strip()
        self.token = self.access_token
        self.password = password.strip() if password else None
        self._is_cancelled: bool = False

    def cancel(self):
        self._is_cancelled = True

    @Slot()
    def run(self):
        try:
            if self._is_cancelled:
                return
            parsed = urlparse(self.url)
            if parsed.scheme not in ("http", "https") or "dropbox.com" not in parsed.netloc:
                raise ValueError("Please enter a valid Dropbox shared URL.")

            if not self.access_token and not self.refresh_token:
                raise ValueError("Please sign in with your Dropbox account to inspect folders.")

            entries = []
            root_name = "DropboxFolder"

            self.status.emit("Connecting to Dropbox API...")
            dbx = create_dropbox_client(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                app_key=self.app_key,
            )

            try:
                meta_kwargs: dict[str, Any] = {"url": self.url}
                if self.password:
                    meta_kwargs["link_password"] = self.password
                meta = dbx.sharing_get_shared_link_metadata(**meta_kwargs)
                root_name = getattr(meta, "name", None) or "DropboxFolder"
            except ApiError as exc:
                if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                    raise ValueError(
                        "Access Denied: This link is password-protected.\n"
                        "Please enter the link password in the credentials section."
                    )
                raise

            shared_link = SharedLink(
                url=self.url,
                password=self.password if self.password else None,
            )

            self.status.emit("Querying folder hierarchy...")

            def collect_recursive(api_path="", rel_dir=""):
                if self._is_cancelled:
                    return
                res: Any = dbx.files_list_folder(path=api_path, shared_link=shared_link, recursive=False)
                subfolders_to_visit = []
                if res and hasattr(res, "entries"):
                    for e in res.entries:
                        if self._is_cancelled:
                            return
                        is_dir = isinstance(e, FolderMetadata)
                        name = e.name
                        if not name:
                            continue
                        rel = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                        size = getattr(e, "size", 0) if not is_dir else 0
                        entries.append({"name": name, "path": rel, "is_dir": is_dir, "size": size})
                        if is_dir:
                            next_api = f"{api_path}/{name}" if api_path else f"/{name}"
                            subfolders_to_visit.append((next_api, rel))

                while res and getattr(res, "has_more", False):
                    if self._is_cancelled:
                        return
                    res = dbx.files_list_folder_continue(res.cursor)
                    if res and hasattr(res, "entries"):
                        for e in res.entries:
                            if self._is_cancelled:
                                return
                            is_dir = isinstance(e, FolderMetadata)
                            name = e.name
                            if not name:
                                continue
                            rel = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                            size = getattr(e, "size", 0) if not is_dir else 0
                            entries.append({"name": name, "path": rel, "is_dir": is_dir, "size": size})
                            if is_dir:
                                next_api = f"{api_path}/{name}" if api_path else f"/{name}"
                                subfolders_to_visit.append((next_api, rel))

                for next_api, next_rel in subfolders_to_visit:
                    if self._is_cancelled:
                        return
                    collect_recursive(next_api, next_rel)

            collect_recursive("", "")

            if self._is_cancelled:
                return

            root_name = sanitize_filename(root_name) or "DropboxFolder"
            tree = build_tree_hierarchy(entries, root_name)
            self.finished.emit(tree, root_name, entries)

        except Exception as exc:
            if not self._is_cancelled:
                self.failed.emit(str(exc))


# ==============================================================================
# Download Worker (Granular Selective Dropbox API Downloads)
# ==============================================================================
@dataclass
class DownloadFileItem:
    name: str
    size: int
    rel_path: str
    api_path: str
    metadata: Any = None

    @property
    def _custom_rel_path(self) -> str:
        return self.rel_path

    @property
    def _custom_api_path(self) -> str:
        return self.api_path


class DownloadWorker(QObject):
    log = Signal(str)
    folder_changed = Signal(str)
    file_changed = Signal(str)
    current_progress = Signal(int)
    overall_progress = Signal(int)
    stats_changed = Signal(dict)
    finished = Signal(str)
    failed = Signal(str)
    paused_signal = Signal(bool)

    def __init__(
        self,
        url: str,
        destination: str,
        token: str = "",
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_key: str | None = None,
        link_password: str | None = None,
        skip_existing: bool = True,
        selected_files: set[str] | None = None,
        deselected_files: set[str] | None = None,
        selected_folders: set[str] | None = None,
        deselected_folders: set[str] | None = None,
        has_tree_filter: bool = False,
    ):
        super().__init__()
        self.url = url.strip()
        self.access_token = (access_token or token or "").strip()
        self.refresh_token = (refresh_token or "").strip()
        self.app_key = (app_key or "").strip()
        self.token = self.access_token
        self.destination = Path(destination)
        self.link_password = link_password.strip() if link_password else None
        self.skip_existing = skip_existing
        self.selected_files = selected_files or set()
        self.deselected_files = deselected_files or set()
        self.selected_folders = selected_folders or set()
        self.deselected_folders = deselected_folders or set()
        self.has_tree_filter = has_tree_filter
        self.stop_requested = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._is_paused = False
        self.pause_start_time: float = 0.0
        self.paused_duration: float = 0.0
        self.files: list[DownloadFileItem] = []
        self.folders = 0
        self.done = 0
        self.skipped = 0
        self.errors = 0
        self.bytes_done = 0
        self.started: float = 0.0

    def is_selected(self, rel_path: str) -> bool:
        return is_path_selected(
            rel_path,
            self.selected_files,
            self.deselected_files,
            self.selected_folders,
            self.deselected_folders,
            self.has_tree_filter,
        )

    def pause(self):
        if not self._is_paused and not self.stop_requested:
            self._is_paused = True
            self.pause_start_time = time.time()
            self._pause_event.clear()
            self.paused_signal.emit(True)
            self.log.emit("⏸ Download paused.")

    def resume(self):
        if self._is_paused:
            if self.pause_start_time > 0:
                self.paused_duration += max(time.time() - self.pause_start_time, 0.0)
                self.pause_start_time = 0.0
            self._is_paused = False
            self._pause_event.set()
            self.paused_signal.emit(False)
            self.log.emit("▶ Download resumed.")

    def toggle_pause(self):
        if self._is_paused:
            self.resume()
        else:
            self.pause()

    def stop(self):
        self.stop_requested = True
        if self._is_paused:
            self._is_paused = False
            self._pause_event.set()

    def _check_pause(self):
        while not self._pause_event.is_set():
            if self.stop_requested:
                break
            time.sleep(0.1)

    def list_folder(self, dbx: dropbox.Dropbox, shared_link: SharedLink, path: str):
        result: Any = dbx.files_list_folder(
            path=path,
            recursive=False,
            shared_link=shared_link,
            include_non_downloadable_files=True,
        )
        if result and hasattr(result, "entries"):
            yield from result.entries

        while result and getattr(result, "has_more", False) and not self.stop_requested:
            result = dbx.files_list_folder_continue(result.cursor)
            if result and hasattr(result, "entries"):
                yield from result.entries

    def collect(self, dbx: dropbox.Dropbox, shared_link: SharedLink, api_path="", rel_dir=""):
        self._check_pause()
        if self.stop_requested:
            return

        self.folder_changed.emit(api_path if api_path else "/")

        try:
            entries = list(self.list_folder(dbx, shared_link, api_path))
        except ApiError as exc:
            self.errors += 1
            if "shared_link_access_denied" in str(exc) or "password" in str(exc).lower():
                self.log.emit(f"🔒 Access denied listing {api_path or '/'}: Password may be required.")
            else:
                self.log.emit(f"ERROR listing {api_path or '/'}: {exc}")
            return
        except Exception as exc:
            self.errors += 1
            self.log.emit(f"ERROR listing {api_path or '/'}: {exc}")
            return

        for entry in entries:
            self._check_pause()
            if self.stop_requested:
                return
            if isinstance(entry, FileMetadata):
                entry_rel = f"{rel_dir}/{entry.name}".strip("/") if rel_dir else entry.name
                entry_api = f"{api_path}/{entry.name}" if api_path else f"/{entry.name}"
                self.files.append(
                    DownloadFileItem(
                        name=entry.name,
                        size=getattr(entry, "size", 0) or 0,
                        rel_path=entry_rel,
                        api_path=entry_api,
                        metadata=entry,
                    )
                )

        for entry in entries:
            self._check_pause()
            if self.stop_requested:
                return
            if isinstance(entry, FolderMetadata):
                self.folders += 1
                sub_rel = f"{rel_dir}/{entry.name}".strip("/") if rel_dir else entry.name
                sub_api = f"{api_path}/{entry.name}" if api_path else f"/{entry.name}"
                self.collect(dbx, shared_link, api_path=sub_api, rel_dir=sub_rel)

    def download_one(self, dbx: dropbox.Dropbox, entry: Any, local_root: Path):
        if isinstance(entry, DownloadFileItem):
            rel = entry.rel_path
            api_path = entry.api_path
            file_size = entry.size
            file_name = entry.name
        elif isinstance(entry, dict):
            rel = entry.get("rel_path") or entry.get("path") or ""
            api_path = entry.get("api_path") or (f"/{rel}" if not rel.startswith("/") else rel)
            file_size = int(entry.get("size", 0) or 0)
            file_name = entry.get("name") or Path(rel).name
        else:
            rel = getattr(entry, "rel_path", None) or getattr(entry, "_custom_rel_path", None) or relative_path(entry)
            api_path = getattr(entry, "api_path", None) or getattr(entry, "_custom_api_path", None) or (f"/{rel}" if not rel.startswith("/") else rel)
            file_size = getattr(entry, "size", 0)
            file_name = getattr(entry, "name", Path(rel).name)

        local_file = safe_local_path(local_root, rel)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        rel_clean = rel.replace("\\", "/").strip("/")
        if "/" in rel_clean:
            folder_display = Path(rel_clean).parent.as_posix()
        else:
            folder_display = "/ (Root)"
        file_display = file_name or Path(rel_clean).name

        self.folder_changed.emit(folder_display)
        self.file_changed.emit(f"{file_display}  ({format_bytes(file_size)})")

        if self.skip_existing and local_file.exists():
            if local_file.stat().st_size == file_size:
                self.skipped += 1
                self.bytes_done += file_size
                self.current_progress.emit(100)
                self.log.emit(f"SKIP  [{folder_display}] {file_display} (already exists)")
                return

        temp_file = local_file.with_name(f"{local_file.name}.tmp_{int(time.time())}")
        self.log.emit(f"GET   [{folder_display}] {file_display} ({format_bytes(file_size)})")

        try:
            download_kwargs: dict[str, Any] = {"url": self.url, "path": api_path}
            if self.link_password:
                download_kwargs["link_password"] = self.link_password

            res: Any = dbx.sharing_get_shared_link_file(**download_kwargs)
            metadata, response = res
            downloaded = 0
            start_time = time.time()

            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 128):
                    self._check_pause()
                    if self.stop_requested:
                        f.close()
                        temp_file.unlink(missing_ok=True)
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if file_size > 0:
                            pct = int(downloaded * 100 / file_size)
                            self.current_progress.emit(pct)

                    if self._is_paused:
                        speed_str = "Paused"
                    else:
                        elapsed = max(time.time() - start_time, 0.001)
                        speed = downloaded / elapsed
                        speed_str = f"{format_bytes(int(speed))}/s"

                    active_elapsed = max(time.time() - self.started - self.paused_duration, 0)
                    self.stats_changed.emit({
                        "speed": speed_str,
                        "data": f"{format_bytes(self.bytes_done + downloaded)}",
                        "files": f"{self.done + 1}/{len(self.files)} files",
                        "elapsed": f"{int(active_elapsed // 60):02d}:{int(active_elapsed % 60):02d}",
                    })

            actual = temp_file.stat().st_size
            if actual != file_size:
                temp_file.unlink(missing_ok=True)
                raise IOError(f"size mismatch: expected {file_size}, got {actual}")

            os.replace(temp_file, local_file)
            self.done += 1
            self.bytes_done += actual
            self.current_progress.emit(100)
            self.log.emit(f"DONE  [{folder_display}] {file_display}")

        except Exception as exc:
            temp_file.unlink(missing_ok=True)
            self.errors += 1
            if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                self.log.emit(f"🔒 ERROR [{folder_display}] {file_display}: Password protected. Verify link password.")
            else:
                err_title, err_desc = parse_friendly_error(exc)
                self.log.emit(f"❌ ERROR [{folder_display}] {file_display}: {err_title} ({err_desc.splitlines()[0]})")

    @Slot()
    def run(self):
        try:
            self.started = time.time()
            parsed = urlparse(self.url)
            if parsed.scheme not in ("http", "https") or "dropbox.com" not in parsed.netloc:
                raise ValueError("Please enter a valid Dropbox shared URL.")

            if not self.access_token and not self.refresh_token:
                raise ValueError("Please sign in with your Dropbox account to download files.")

            self.destination.mkdir(parents=True, exist_ok=True)
            dbx = create_dropbox_client(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                app_key=self.app_key,
            )

            try:
                account: Any = dbx.users_get_current_account()
                if account and hasattr(account, "name") and account.name:
                    self.log.emit(f"🔑 Authenticated as: {account.name.display_name} ({account.email})")
            except AuthError:
                raise ValueError("Invalid or expired Dropbox session. Please sign in again.")

            try:
                metadata_kwargs: dict[str, Any] = {"url": self.url}
                if self.link_password:
                    metadata_kwargs["link_password"] = self.link_password
                metadata = dbx.sharing_get_shared_link_metadata(**metadata_kwargs)
                root_name = getattr(metadata, "name", None) or "DropboxFolder"
            except ApiError as exc:
                if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                    raise ValueError(
                        "Access Denied: This link is password-protected or restricted.\n"
                        "Please verify the folder password entered in the credentials section."
                    )
                raise

            root_name = sanitize_filename(root_name) or "DropboxFolder"
            local_root = safe_local_path(self.destination, root_name)
            local_root.mkdir(parents=True, exist_ok=True)

            self.log.emit(f"📁 Destination folder: {local_root}")
            self.log.emit("🔍 Querying Dropbox hierarchy...")

            shared_link = SharedLink(
                url=self.url,
                password=self.link_password if self.link_password else None,
            )

            self.collect(dbx, shared_link, api_path="", rel_dir="")

            if self.stop_requested:
                self.finished.emit("Download stopped.")
                return

            # Filter files by user selection in tree
            all_discovered = list(self.files)
            filtered_files: list[DownloadFileItem] = []
            for entry in all_discovered:
                rel = getattr(entry, "rel_path", None) or getattr(entry, "_custom_rel_path", None) or relative_path(entry)
                if self.is_selected(rel):
                    filtered_files.append(entry)
                else:
                    self.skipped += 1
                    self.log.emit(f"SKIP  {rel} (deselected in tree)")

            self.files = filtered_files
            self.log.emit(f"✓ Selected {len(self.files)} of {len(all_discovered)} file(s) to download.")
            self.log.emit("🚀 Starting direct selective download...")

            for index, entry in enumerate(self.files, start=1):
                self._check_pause()
                if self.stop_requested:
                    break

                self.overall_progress.emit(
                    int((index - 1) * 100 / max(len(self.files), 1))
                )

                self.download_one(dbx, entry, local_root)

                self.overall_progress.emit(
                    int(index * 100 / max(len(self.files), 1))
                )

            elapsed = max(time.time() - self.started - self.paused_duration, 0.1)

            if self.stop_requested:
                message = "Download cancelled by user."
            else:
                message = (
                    f"✓ Download Finished Successfully!\n\n"
                    f"Files Selected: {len(self.files)}\n"
                    f"Completed: {self.done}\n"
                    f"Skipped: {self.skipped}\n"
                    f"Errors: {self.errors}\n"
                    f"Data Transferred: {format_bytes(self.bytes_done)}\n"
                    f"Time Elapsed: {elapsed:.1f}s\n"
                    f"Output Directory: {local_root}"
                )

            self.finished.emit(message)

        except Exception as exc:
            self.failed.emit(str(exc))


# ==============================================================================
# Modern Dark Styled Popups & Dialogs
# ==============================================================================
class ModernMessageBox(QDialog):
    """A sleek, modern dark-themed modal dialog replacing native QMessageBox."""

    ICON_INFO = "info"
    ICON_WARNING = "warning"
    ICON_ERROR = "error"
    ICON_QUESTION = "question"
    ICON_SUCCESS = "success"

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        message: str,
        icon_type: str = "info",
        buttons: list[tuple[str, str, bool]] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setMaximumWidth(560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c1322;
                border: 1px solid #1f2e45;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(16)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        badge_configs = {
            self.ICON_INFO: ("ℹ", "#0c2646", "#38bdf8", "#0284c7"),
            self.ICON_SUCCESS: ("✓", "#064e3b", "#34d399", "#059669"),
            self.ICON_WARNING: ("⚠", "#451a03", "#fbbf24", "#d97706"),
            self.ICON_ERROR: ("✕", "#450a0a", "#f87171", "#b91c1c"),
            self.ICON_QUESTION: ("?", "#172554", "#60a5fa", "#2563eb"),
        }
        symbol, bg_col, text_col, border_col = badge_configs.get(
            icon_type, ("ℹ", "#0c2646", "#38bdf8", "#0284c7")
        )

        icon_label = QLabel(symbol)
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(
            f"background-color: {bg_col}; color: {text_col}; border: 1px solid {border_col}; "
            f"border-radius: 20px; font-size: 18px; font-weight: 700;"
        )
        content_row.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 700;")
        text_layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.45;")
        text_layout.addWidget(msg_lbl)

        content_row.addLayout(text_layout, stretch=1)
        layout.addLayout(content_row)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.selected_button_index = -1
        self._buttons = buttons or [("OK", "primary", True)]

        for idx, (btn_text, btn_role, is_default) in enumerate(self._buttons):
            btn = QPushButton(btn_text)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if btn_role == "primary":
                btn.setProperty("class", "btn-primary")
            elif btn_role == "danger":
                btn.setProperty("class", "btn-stop")
            else:
                btn.setProperty("class", "btn-secondary")

            if is_default:
                btn.setDefault(True)

            btn.clicked.connect(lambda checked=False, i=idx: self._on_btn_clicked(i))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _on_btn_clicked(self, index: int):
        self.selected_button_index = index
        self.accept()

    @classmethod
    def information(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_INFO, buttons=[("OK", "primary", True)])
        dlg.exec()

    @classmethod
    def warning(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_WARNING, buttons=[("OK", "primary", True)])
        dlg.exec()

    @classmethod
    def error(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_ERROR, buttons=[("Close", "primary", True)])
        dlg.exec()

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        yes_text: str = "Yes",
        no_text: str = "No",
        is_destructive: bool = False,
    ) -> bool:
        role = "danger" if is_destructive else "primary"
        dlg = cls(
            parent,
            title=title,
            message=message,
            icon_type=cls.ICON_QUESTION if not is_destructive else cls.ICON_WARNING,
            buttons=[(no_text, "secondary", False), (yes_text, role, True)],
        )
        dlg.exec()
        return dlg.selected_button_index == 1


class ModernInputDialog(QDialog):
    """A sleek, modern dark-themed modal input dialog replacing QInputDialog."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        heading: str,
        message: str = "",
        placeholder: str = "",
        default_text: str = "",
        is_password: bool = False,
        confirm_text: str = "Continue",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(640)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c1322;
                border: 1px solid #1f2e45;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon_char = "🔑" if "key" in title.lower() else "🌐"
        icon_badge = QLabel(icon_char)
        icon_badge.setFixedSize(38, 38)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            "background-color: #0c2646; color: #38bdf8; border: 1px solid #0284c7; "
            "border-radius: 19px; font-size: 17px;"
        )
        header_row.addWidget(icon_badge)

        title_lbl = QLabel(heading)
        title_lbl.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 700;")
        header_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(header_row)

        if message:
            msg_frame = QFrame()
            msg_frame.setStyleSheet(
                "background-color: #111a2e; border: 1px solid #1e2d4a; border-radius: 8px; padding: 12px 14px;"
            )
            msg_layout = QVBoxLayout(msg_frame)
            msg_layout.setContentsMargins(0, 0, 0, 0)
            msg_layout.setSpacing(6)

            msg_lbl = QLabel(message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.5;")
            msg_layout.addWidget(msg_lbl)
            layout.addWidget(msg_frame)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setText(default_text)
        if is_password:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_field.returnPressed.connect(self.accept)
        layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setProperty("class", "btn-primary")
        btn_confirm.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)

    @classmethod
    def get_text(
        cls,
        parent: QWidget | None,
        title: str,
        heading: str,
        message: str = "",
        placeholder: str = "",
        default_text: str = "",
        is_password: bool = False,
        confirm_text: str = "Continue",
    ) -> tuple[str, bool]:
        dlg = cls(
            parent,
            title=title,
            heading=heading,
            message=message,
            placeholder=placeholder,
            default_text=default_text,
            is_password=is_password,
            confirm_text=confirm_text,
        )
        result = dlg.exec()
        return (dlg.input_field.text().strip(), result == QDialog.DialogCode.Accepted)


class ModernLoadingDialog(QDialog):
    """A sleek, modern dark-themed modal loader dialog with an animated progress bar and spinner."""
    cancelled = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Signing In",
        heading: str = "Signing into Dropbox...",
        status: str = "Authenticating with Dropbox...",
        cancelable: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setMaximumWidth(540)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c1322;
                border: 1px solid #1f2e45;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(18)

        # Header with animated badge icon and heading
        header_row = QHBoxLayout()
        header_row.setSpacing(16)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.icon_badge = QLabel("⠋")
        self.icon_badge.setFixedSize(48, 48)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setStyleSheet(
            "background-color: #0c2646; color: #38bdf8; border: 1.5px solid #0284c7; "
            "border-radius: 24px; font-size: 22px; font-weight: bold;"
        )
        header_row.addWidget(self.icon_badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.heading_label = QLabel(heading)
        self.heading_label.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 700;")
        text_col.addWidget(self.heading_label)

        self.status_label = QLabel(status)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        text_col.addWidget(self.status_label)

        header_row.addLayout(text_col, stretch=1)
        layout.addLayout(header_row)

        # Animated gradient progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #090e1a;
                border: 1px solid #1e293b;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:0.5 #38bdf8, stop:1 #6366f1);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Cancel button row
        if cancelable:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            self.btn_cancel = QPushButton("Cancel")
            self.btn_cancel.setProperty("class", "btn-secondary")
            self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_cancel.setFixedHeight(32)
            self.btn_cancel.setMinimumWidth(88)
            self.btn_cancel.clicked.connect(self.on_cancel_clicked)
            btn_row.addWidget(self.btn_cancel)
            layout.addLayout(btn_row)

        # Spinner & progress animation
        self.auth_success: bool = False
        self.auth_data: dict[str, str] = {}
        self.auth_error: str = ""
        self.is_cancelled: bool = False

        self._current_val: float = 10.0
        self._target_val: float = 20.0
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_idx = 0
        self._tick_count = 0

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(25)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start()

    @Slot()
    def _on_anim_tick(self):
        self._tick_count += 1

        # Smooth forward-only advance towards target, never backwards
        if self._current_val < self._target_val:
            step = max(0.5, (self._target_val - self._current_val) * 0.15)
            self._current_val = min(self._current_val + step, self._target_val)
        elif self._current_val < 94.0:
            # Gentle forward crawl while awaiting network so the loader feels alive
            self._current_val += 0.08
            self._target_val = max(self._target_val, self._current_val)

        self.progress_bar.setValue(int(self._current_val))

        # Advance spinner frame every 4 ticks (~100ms)
        if self._tick_count % 4 == 0:
            self._frame_idx = (self._frame_idx + 1) % len(self._spinner_frames)
            self.icon_badge.setText(self._spinner_frames[self._frame_idx])

    @Slot(int)
    def set_progress(self, val: int):
        target = float(max(0, min(val, 100)))
        if target > self._target_val:
            self._target_val = target

    @Slot(str)
    def set_heading(self, text: str):
        self.heading_label.setText(text)

    @Slot(str)
    def set_status(self, text: str):
        self.status_label.setText(text)
        lower = text.lower()
        if "authoriz" in lower or "exchanging" in lower:
            self.set_progress(25)
        elif "connect" in lower or "api" in lower:
            self.set_progress(55)
        elif "profile" in lower or "account" in lower:
            self.set_progress(80)
        elif "complet" in lower or "finish" in lower:
            self.set_progress(95)

    @Slot(str, str, str, str)
    def on_auth_finished(self, access_token: str, refresh_token: str, user_name: str, user_email: str):
        self.auth_success = True
        self.auth_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_name": user_name,
            "user_email": user_email,
        }
        self._current_val = 100.0
        self._target_val = 100.0
        self.progress_bar.setValue(100)
        self.icon_badge.setText("✓")
        self.icon_badge.setStyleSheet(
            "background-color: #064e3b; color: #34d399; border: 1.5px solid #059669; "
            "border-radius: 24px; font-size: 22px; font-weight: bold;"
        )
        self.heading_label.setText("Signed in successfully!")
        self.status_label.setText(f"Connected as {user_name}")
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setEnabled(False)
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        QTimer.singleShot(350, self.accept)

    @Slot(str)
    def on_auth_failed(self, err_msg: str):
        self.auth_error = err_msg
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.reject()

    @Slot()
    def on_cancel_clicked(self):
        self.is_cancelled = True
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.cancelled.emit()
        self.reject()

    def closeEvent(self, event):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().closeEvent(event)

    def accept(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().accept()

    def reject(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().reject()


# ==============================================================================
# Main GUI Window
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dropbox Recursive Downloader Pro")
        self.resize(940, 860)
        self.setMinimumSize(840, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        self.settings = QSettings("DropboxDownloader", "RecursiveGUI")
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
        self.check_skip_existing = QCheckBox("Skip files that already exist locally (matching exact size)")
        self.check_skip_existing.setChecked(True)
        dest_opts_row.addWidget(self.check_skip_existing)
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

        self.tree_widget = QTreeWidget()
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
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        tree_layout.addWidget(self.tree_widget)
        self.show_empty_tree_placeholder()

        self.tree_hint = QLabel("💡 Tip: Click or check any file to select it for download. Right-click any item for more options.")
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

        self.pause_button = QPushButton("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        self.pause_button.setVisible(False)
        self.pause_button.clicked.connect(self.toggle_pause_download)

        self.stop_button = QPushButton("⏹  Stop Download")
        self.stop_button.setProperty("class", "btn-stop")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self.stop_download)

        actions_row.addWidget(self.start_button, 1)
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
        is_running = self._is_running or (self.download_thread is not None and self.download_thread.isRunning())
        is_scanning = self.scan_thread is not None and self.scan_thread.isRunning()

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
            self.tree_widget.setEnabled(not is_running)
            self.btn_select_all.setEnabled(not active)
            self.btn_deselect_all.setEnabled(not active)
            self.btn_expand_all.setEnabled(not active)
            self.btn_collapse_all.setEnabled(not active)
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
        is_running = self._is_running or (self.download_thread is not None and self.download_thread.isRunning())
        is_scanning = self.scan_thread is not None and self.scan_thread.isRunning()

        if is_running:
            self.start_button.setVisible(False)
            self.pause_button.setVisible(True)
            self.stop_button.setVisible(True)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            return

        # Not running -> Hide pause and stop, show start button
        self.pause_button.setVisible(False)
        self.stop_button.setVisible(False)
        self.start_button.setVisible(True)

        if not logged_in:
            self.start_button.setEnabled(False)
            self.start_button.setText("🔒  Log In to Start")
            self.start_button.setToolTip("Please sign in to Dropbox to enable downloading.")
            return

        if is_scanning:
            self.start_button.setEnabled(False)
            self.start_button.setText("⏳  Loading Folders...")
            self.start_button.setToolTip("Scanning Dropbox shared link hierarchy...")
            return

        url = self.url_input.text().strip()
        has_link = bool(url and ("dropbox.com" in url) and ("http://" in url or "https://" in url))

        info = self.get_tree_selection_info()
        has_tree = info.get("has_tree_items", False)
        selected_count = info.get("selected_file_count", 0)

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
        if self.auth_thread:
            if self.auth_thread.isRunning():
                self.auth_thread.quit()
                self.auth_thread.wait(3000)
            self.auth_thread = None
        self.auth_worker = None

    def cleanup_verify_thread(self):
        if self.verify_thread:
            if self.verify_thread.isRunning():
                self.verify_thread.quit()
                self.verify_thread.wait(3000)
            self.verify_thread = None
        self.verify_worker = None

    def cleanup_download_thread(self):
        if self.download_thread is not None:
            if self.worker:
                self.worker.stop()
            if self.download_thread.isRunning():
                self.download_thread.quit()
                self.download_thread.wait(3000)
            self.download_thread = None
        self.worker = None

    def cleanup_scan_thread(self):
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            self.auto_scan_timer.stop()
        if hasattr(self, "scan_worker") and self.scan_worker is not None:
            self.scan_worker.cancel()
        if hasattr(self, "scan_thread") and self.scan_thread is not None:
            if self.scan_thread.isRunning():
                self.scan_thread.quit()
                self.scan_thread.wait(2000)
            self.scan_thread = None
        self.scan_worker = None

    @Slot(str, str)
    def on_verify_finished(self, name: str, email: str):
        self.cleanup_verify_thread()
        if name:
            self.current_user_name = name
        if email:
            self.current_user_email = email
        self.save_settings()
        self.update_account_ui()
        self.add_log(f"🔑 Restored session: {self.current_user_name} <{self.current_user_email}>")

    @Slot(str)
    def on_verify_expired(self, exc_msg: str):
        self.cleanup_verify_thread()
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
        self.cleanup_verify_thread()
        title, msg = parse_friendly_error(exc_msg)
        self.add_log(f"⚠ Session check: {msg.splitlines()[0]} Please sign in again if needed.")

    @Slot(str)
    def on_auth_status(self, msg: str):
        self.add_log(f"ℹ {msg}")

    def verify_saved_session(self):
        if not self.is_logged_in():
            return

        self.cleanup_verify_thread()
        self.verify_thread = QThread()
        self.verify_worker = SessionVerifyWorker(
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
        )
        self.verify_worker.moveToThread(self.verify_thread)

        self.verify_worker.finished.connect(self.on_verify_finished)
        self.verify_worker.expired.connect(self.on_verify_expired)
        self.verify_worker.failed.connect(self.on_verify_failed)

        self.verify_thread.started.connect(self.verify_worker.run)
        self.verify_thread.start()

    def save_settings(self):
        self.settings.setValue("destination", self.destination_input.text().strip())
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
            self.auth_thread = QThread()
            self.auth_worker = AuthWorker(flow=flow, code=code, app_key=app_key)
            self.auth_worker.moveToThread(self.auth_thread)

            self.auth_worker.status.connect(loading_dialog.set_status)
            self.auth_worker.status.connect(self.on_auth_status)
            self.auth_worker.progress.connect(loading_dialog.set_progress)
            self.auth_worker.finished.connect(loading_dialog.on_auth_finished)
            self.auth_worker.failed.connect(loading_dialog.on_auth_failed)
            loading_dialog.cancelled.connect(self.auth_worker.cancel)

            self.auth_thread.started.connect(self.auth_worker.run)
            QTimer.singleShot(20, self.auth_thread.start)

            loading_dialog.exec()

            self.cleanup_auth_thread()

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
                    if self.is_logged_in() and not (self.download_thread and self.download_thread.isRunning())
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
        if dest and os.path.exists(dest):
            os.startfile(dest)
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

        self.update_download_button_state()

        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(
            url=url,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            password=password,
        )
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.status.connect(self.on_scan_status)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.failed.connect(self.on_scan_failed)

        self.scan_thread.start()

    @Slot(str)
    def on_scan_status(self, text: str):
        self.set_selection_summary(f"⏳ {text}", "active")

    def on_scan_finished(self, tree_dict: dict, root_name: str, entries: list):
        self.cleanup_scan_thread()
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
        self.update_download_button_state()

    def on_scan_failed(self, error: str):
        self.cleanup_scan_thread()
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("🔍 Load Folders")

        title, friendly_msg = parse_friendly_error(error)
        self.show_empty_tree_placeholder()
        self.set_selection_summary(f"⚠️ {title}", "error")
        self.add_log(f"⚠️ {title}: {friendly_msg.splitlines()[0]}")
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
                key=lambda x: (not x[1]["is_dir"], x[0].lower())
            ):
                add_item_recursive(item, child_data)

        if tree_dict["children"]:
            for child_name, child_data in sorted(
                tree_dict["children"].items(),
                key=lambda x: (not x[1]["is_dir"], x[0].lower())
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
        self._updating_tree = False
        self.update_selection_summary()

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
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
            if action == act_only:
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
            act_select_folder = menu.addAction(f"☑ Select All in '{raw_name}'")
            act_deselect_folder = menu.addAction(f"☐ Deselect All in '{raw_name}'")
            menu.addSeparator()
            act_expand = menu.addAction("📂 Expand Folder")
            act_collapse = menu.addAction("📁 Collapse Folder")
            menu.addSeparator()
            act_select_all = menu.addAction("☑ Select All")
            act_deselect_all = menu.addAction("☐ Deselect All")

            action = menu.exec(self.tree_widget.viewport().mapToGlobal(point))
            if action == act_select_folder:
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
        total_items = 0
        selected_items = 0
        selected_bytes = 0

        def count_recursive(item: QTreeWidgetItem | None):
            nonlocal total_items, selected_items, selected_bytes
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            total_items += 1
            state = item.checkState(0)
            is_dir = item.data(1, Qt.ItemDataRole.UserRole)
            size = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)

            if state == Qt.CheckState.Checked:
                selected_items += 1
                if not is_dir:
                    selected_bytes += size
            elif state == Qt.CheckState.PartiallyChecked:
                selected_items += 1

            for i in range(item.childCount()):
                count_recursive(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            count_recursive(self.tree_widget.topLevelItem(i))

        if total_items == 0:
            self.selection_summary_label.setText("(No items scanned yet)")
            self.selection_summary_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        else:
            summary_txt = f"{selected_items} of {total_items} items selected"
            if selected_bytes > 0:
                summary_txt += f" • {format_bytes(selected_bytes)}"
            self.selection_summary_label.setText(summary_txt)
            self.selection_summary_label.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600;")

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

        return {
            "selected_files": selected_files,
            "deselected_files": deselected_files,
            "selected_folders": selected_folders,
            "deselected_folders": deselected_folders,
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
        self.update_feature_enabled_state()

        if running:
            self.set_status_badge("● Downloading...", "running")
        else:
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if "completed" not in curr.lower():
                if self.is_logged_in():
                    self.set_status_badge("● Ready", "ready")
                else:
                    self.set_status_badge("○ Login Required", "neutral")

    def start_download(self):
        if not self.is_logged_in():
            self.prompt_login_required("download files")
            return

        self.cleanup_download_thread()

        url = self.url_input.text().strip()
        destination = self.destination_input.text().strip()
        skip_existing = self.check_skip_existing.isChecked()
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

        self.download_thread = QThread()
        self.worker = DownloadWorker(
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
            has_tree_filter=info["has_tree_items"],
        )

        self.worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.worker.run)

        self.worker.log.connect(self.add_log)
        self.worker.folder_changed.connect(self.folder_label.setText)
        self.worker.file_changed.connect(self.file_label.setText)
        self.worker.current_progress.connect(self.update_file_progress)
        self.worker.overall_progress.connect(self.update_overall_progress)
        self.worker.stats_changed.connect(self.update_stats)
        self.worker.paused_signal.connect(self.on_download_paused_changed)

        self.worker.finished.connect(self.download_finished)
        self.worker.failed.connect(self.download_failed)

        self.download_thread.start()

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
        self.cleanup_download_thread()
        self.set_running(False)
        self.add_log(f"\n{message}")
        if "stopped" in message.lower() or "cancelled" in message.lower():
            self.set_status_badge("⏹ Stopped", "neutral")
            self.folder_label.setText("Stopped")
            self.file_label.setText("Download operation stopped")
            self.val_speed.setText("0 B/s")
            ModernMessageBox.information(self, "Download Stopped", message)
        else:
            self.set_status_badge("● Completed", "success")
            self.folder_label.setText("Completed")
            self.file_label.setText("Download completed successfully")
            self.overall_pct_label.setText("100%")
            self.file_pct_label.setText("100%")
            self.file_progress.setValue(100)
            self.overall_progress.setValue(100)
            self.val_speed.setText("0 B/s")
            ModernMessageBox.information(self, "Download Completed", message)

        self.update_feature_enabled_state()
        self.update_download_button_state()

    def download_failed(self, error: str):
        self.cleanup_download_thread()
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
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
