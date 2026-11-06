import os
import sys
import time
import json
import threading
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import dropbox
from dropbox.files import FileMetadata, FolderMetadata, SharedLink
from dropbox.exceptions import ApiError, AuthError

try:
    import shiboken6
except ImportError:
    shiboken6 = None

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .utils import (
    create_dropbox_client,
    parse_friendly_error,
    format_bytes,
    sanitize_filename,
    compute_dropbox_content_hash,
    natural_sort_path_key,
    safe_local_path,
    strip_folder_prefix,
    check_single_folder_destination_match,
    resolve_download_root,
    relative_path,
    is_thread_running,
    build_tree_hierarchy,
    is_path_selected,
)



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
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass


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
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass


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

                # Fast path: Single file shared link
                if isinstance(meta, FileMetadata):
                    file_name = getattr(meta, "name", "file")
                    file_size = getattr(meta, "size", 0)
                    file_hash = getattr(meta, "content_hash", None)
                    entries = [{
                        "name": file_name,
                        "path": file_name,
                        "is_dir": False,
                        "size": file_size,
                        "content_hash": file_hash,
                    }]
                    root_name = sanitize_filename(root_name) or "DropboxFolder"
                    tree = build_tree_hierarchy(entries, root_name)
                    self.finished.emit(tree, root_name, entries)
                    return
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

            rec_success = False
            try:
                res: Any = dbx.files_list_folder(
                    path="",
                    shared_link=shared_link,
                    recursive=True,
                    include_non_downloadable_files=True,
                )
                while res:
                    if self._is_cancelled:
                        break
                    if hasattr(res, "entries"):
                        for e in res.entries:
                            if self._is_cancelled:
                                break
                            is_dir = isinstance(e, FolderMetadata)
                            name = getattr(e, "name", "")
                            if not name:
                                continue
                            path_display = getattr(e, "path_display", None) or getattr(e, "path_lower", None)
                            if path_display:
                                rel = path_display.lstrip("/")
                            else:
                                rel = name
                            size = getattr(e, "size", 0) if not is_dir else 0
                            item_hash = getattr(e, "content_hash", None) if not is_dir else None
                            entries.append({
                                "name": name,
                                "path": rel,
                                "is_dir": is_dir,
                                "size": size,
                                "content_hash": item_hash,
                            })
                    if getattr(res, "has_more", False) and not self._is_cancelled:
                        res = dbx.files_list_folder_continue(res.cursor)
                    else:
                        break
                rec_success = True
            except Exception:
                entries = []
                rec_success = False

            if not rec_success and not self._is_cancelled:
                def fetch_folder_entries(api_path: str, rel_dir: str) -> tuple[list[dict], list[tuple[str, str]]]:
                    if self._is_cancelled:
                        return [], []
                    local_entries = []
                    local_subfolders = []
                    max_retries = 3
                    res: Any = None
                    for attempt in range(max_retries):
                        if self._is_cancelled:
                            break
                        try:
                            res = dbx.files_list_folder(path=api_path, shared_link=shared_link, recursive=False)
                            break
                        except Exception:
                            if attempt < max_retries - 1 and not self._is_cancelled:
                                time.sleep(1.0 * (attempt + 1))
                            else:
                                break
                    while res:
                        if self._is_cancelled:
                            break
                        if hasattr(res, "entries"):
                            for e in res.entries:
                                if self._is_cancelled:
                                    break
                                is_dir = isinstance(e, FolderMetadata)
                                name = e.name
                                if not name:
                                    continue
                                rel = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                                size = getattr(e, "size", 0) if not is_dir else 0
                                item_hash = getattr(e, "content_hash", None) if not is_dir else None
                                local_entries.append({"name": name, "path": rel, "is_dir": is_dir, "size": size, "content_hash": item_hash})
                                if is_dir:
                                    next_api = f"{api_path}/{name}" if api_path else f"/{name}"
                                    local_subfolders.append((next_api, rel))
                        if getattr(res, "has_more", False) and not self._is_cancelled:
                            for attempt in range(max_retries):
                                try:
                                    res = dbx.files_list_folder_continue(res.cursor)
                                    break
                                except Exception:
                                    if attempt < max_retries - 1 and not self._is_cancelled:
                                        time.sleep(1.0 * (attempt + 1))
                                    else:
                                        res = None
                                        break
                        else:
                            break
                    return local_entries, local_subfolders

                root_items, pending_subfolders = fetch_folder_entries("", "")
                entries.extend(root_items)

                if pending_subfolders and not self._is_cancelled:
                    max_workers = min(4, max(2, len(pending_subfolders)))
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        while pending_subfolders and not self._is_cancelled:
                            current_batch = pending_subfolders
                            pending_subfolders = []

                            futures = [
                                executor.submit(fetch_folder_entries, api_path, rel_dir)
                                for api_path, rel_dir in current_batch
                            ]

                            for future in as_completed(futures):
                                if self._is_cancelled:
                                    break
                                try:
                                    sub_items, sub_folders = future.result()
                                    entries.extend(sub_items)
                                    pending_subfolders.extend(sub_folders)
                                except Exception:
                                    pass

            if self._is_cancelled:
                return

            root_name = sanitize_filename(root_name) or "DropboxFolder"
            tree = build_tree_hierarchy(entries, root_name)
            self.finished.emit(tree, root_name, entries)

        except Exception as exc:
            if not self._is_cancelled:
                self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass


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
    content_hash: str | None = None

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
        single_selected_folder: str = "",
        has_tree_filter: bool = False,
        verify_integrity: bool = True,
        auto_repair: bool = True,
        verify_only: bool = False,
        scanned_entries: list[dict] | None = None,
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
        self.single_selected_folder = (single_selected_folder or "").strip()
        self.has_tree_filter = has_tree_filter
        self.verify_integrity = verify_integrity
        self.auto_repair = auto_repair
        self.verify_only = verify_only
        self.scanned_entries = scanned_entries
        self.verified_ok = 0
        self.corrupted = 0
        self.repaired = 0
        self.missing = 0
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
        self.current_downloading_bytes: int = 0
        self.is_currently_downloading: bool = False
        self.is_verifying: bool = False
        self.is_inline_verifying: bool = False
        self.instant_speed: float = 0.0
        self._last_chunk_time: float = 0.0
        self._last_stats_emit_time: float = 0.0
        self._speed_window: list[tuple[float, int]] = []

    def update_speed_tracker(self, bytes_chunk: int):
        now = time.time()
        self._last_chunk_time = now
        self._speed_window.append((now, bytes_chunk))
        cutoff = now - 2.0
        self._speed_window = [(t, b) for t, b in self._speed_window if t >= cutoff]
        if len(self._speed_window) >= 2:
            duration = now - self._speed_window[0][0]
            if duration >= 0.05:
                window_bytes = sum(b for t, b in self._speed_window)
                raw_speed = window_bytes / duration
                if self.instant_speed <= 0:
                    self.instant_speed = raw_speed
                else:
                    self.instant_speed = (self.instant_speed * 0.75) + (raw_speed * 0.25)
        elif not self._speed_window:
            self.instant_speed = 0.0

    def emit_stats(self, custom_speed: str | None = None, force: bool = False):
        now = time.time()
        if not force and custom_speed is None and (now - self._last_stats_emit_time < 0.08):
            return
        self._last_stats_emit_time = now

        if self._is_paused:
            speed_str = "Paused"
        elif custom_speed:
            speed_str = custom_speed
        else:
            if now - self._last_chunk_time > 1.5:
                self.instant_speed = 0.0
                self._speed_window.clear()
            if self.is_verifying or self.is_inline_verifying:
                speed_str = f"{format_bytes(int(self.instant_speed))}/s (Verify)" if self.instant_speed > 0 else "0 B/s (Verify)"
            else:
                speed_str = f"{format_bytes(int(self.instant_speed))}/s"

        active_elapsed = 0.0
        if self.started > 0:
            active_elapsed = now - self.started - self.paused_duration
            if self._is_paused and self.pause_start_time > 0:
                active_elapsed -= (now - self.pause_start_time)
            active_elapsed = max(active_elapsed, 0.0)

        total_count = max(len(self.files), 1)
        if self.is_verifying or self.verify_only:
            files_str = f"{self.verified_ok}/{total_count} verified"
        else:
            processed = min(self.done + self.skipped + (1 if self.is_currently_downloading else 0), total_count)
            files_str = f"{processed}/{total_count} files"

        current_bytes = self.bytes_done + self.current_downloading_bytes

        self.stats_changed.emit({
            "speed": speed_str,
            "data": format_bytes(current_bytes),
            "files": files_str,
            "elapsed": f"{int(active_elapsed // 60):02d}:{int(active_elapsed % 60):02d}",
        })

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
                entry_hash = getattr(entry, "content_hash", None)
                self.files.append(
                    DownloadFileItem(
                        name=entry.name,
                        size=getattr(entry, "size", 0) or 0,
                        rel_path=entry_rel,
                        api_path=entry_api,
                        metadata=entry,
                        content_hash=entry_hash,
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

    def collect_parallel(self, dbx: dropbox.Dropbox, shared_link: SharedLink):
        self._check_pause()
        if self.stop_requested:
            return

        rec_success = False
        try:
            res: Any = dbx.files_list_folder(
                path="",
                shared_link=shared_link,
                recursive=True,
                include_non_downloadable_files=True,
            )
            while res and not self.stop_requested:
                if hasattr(res, "entries"):
                    for e in res.entries:
                        if self.stop_requested:
                            break
                        if isinstance(e, FileMetadata):
                            path_display = getattr(e, "path_display", None) or getattr(e, "path_lower", None)
                            rel = path_display.lstrip("/") if path_display else e.name
                            api_path = path_display if (path_display and path_display.startswith("/")) else f"/{rel}"
                            entry_hash = getattr(e, "content_hash", None)
                            self.files.append(
                                DownloadFileItem(
                                    name=e.name,
                                    size=getattr(e, "size", 0) or 0,
                                    rel_path=rel,
                                    api_path=api_path,
                                    metadata=e,
                                    content_hash=entry_hash,
                                )
                            )
                        elif isinstance(e, FolderMetadata):
                            self.folders += 1
                if getattr(res, "has_more", False) and not self.stop_requested:
                    res = dbx.files_list_folder_continue(res.cursor)
                else:
                    break
            if self.files or self.folders:
                return
        except Exception:
            self.files = []
            self.folders = 0

        def fetch_folder_entries(api_path: str, rel_dir: str) -> tuple[list[DownloadFileItem], list[tuple[str, str]], int]:
            if self.stop_requested:
                return [], [], 0
            local_files: list[DownloadFileItem] = []
            local_subfolders: list[tuple[str, str]] = []
            folder_count = 0
            max_retries = 3
            res: Any = None
            try:
                for attempt in range(max_retries):
                    if self.stop_requested:
                        break
                    try:
                        res = dbx.files_list_folder(
                            path=api_path,
                            shared_link=shared_link,
                            recursive=False,
                            include_non_downloadable_files=True,
                        )
                        break
                    except Exception as exc:
                        if attempt < max_retries - 1 and not self.stop_requested:
                            time.sleep(1.0 * (attempt + 1))
                        else:
                            if "shared_link_access_denied" in str(exc) or "password" in str(exc).lower():
                                self.log.emit(f"🔒 Access denied listing {api_path or '/'}: Password may be required.")
                            else:
                                self.log.emit(f"ERROR listing {api_path or '/'}: {exc}")
                            break
                while res:
                    if self.stop_requested:
                        break
                    if hasattr(res, "entries"):
                        for e in res.entries:
                            if self.stop_requested:
                                break
                            if isinstance(e, FileMetadata):
                                entry_rel = f"{rel_dir}/{e.name}".strip("/") if rel_dir else e.name
                                entry_api = f"{api_path}/{e.name}" if api_path else f"/{e.name}"
                                entry_hash = getattr(e, "content_hash", None)
                                local_files.append(
                                    DownloadFileItem(
                                        name=e.name,
                                        size=getattr(e, "size", 0) or 0,
                                        rel_path=entry_rel,
                                        api_path=entry_api,
                                        metadata=e,
                                        content_hash=entry_hash,
                                    )
                                )
                            elif isinstance(e, FolderMetadata):
                                folder_count += 1
                                sub_rel = f"{rel_dir}/{e.name}".strip("/") if rel_dir else e.name
                                sub_api = f"{api_path}/{e.name}" if api_path else f"/{e.name}"
                                local_subfolders.append((sub_api, sub_rel))
                    if getattr(res, "has_more", False) and not self.stop_requested:
                        for attempt in range(max_retries):
                            try:
                                res = dbx.files_list_folder_continue(res.cursor)
                                break
                            except Exception:
                                if attempt < max_retries - 1 and not self.stop_requested:
                                    time.sleep(1.0 * (attempt + 1))
                                else:
                                    res = None
                                    break
                    else:
                        break
            except Exception as exc:
                if "shared_link_access_denied" in str(exc) or "password" in str(exc).lower():
                    self.log.emit(f"🔒 Access denied listing {api_path or '/'}: Password may be required.")
                else:
                    self.log.emit(f"ERROR listing {api_path or '/'}: {exc}")
            return local_files, local_subfolders, folder_count

        root_files, pending_subfolders, root_folders_count = fetch_folder_entries("", "")
        self.files.extend(root_files)
        self.folders += root_folders_count

        if pending_subfolders and not self.stop_requested:
            max_workers = min(4, max(2, len(pending_subfolders)))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                while pending_subfolders and not self.stop_requested:
                    current_batch = pending_subfolders
                    pending_subfolders = []

                    futures = [
                        executor.submit(fetch_folder_entries, api_path, rel_dir)
                        for api_path, rel_dir in current_batch
                    ]

                    for future in as_completed(futures):
                        if self.stop_requested:
                            break
                        try:
                            sub_files, sub_folders, f_count = future.result()
                            self.files.extend(sub_files)
                            self.folders += f_count
                            pending_subfolders.extend(sub_folders)
                        except Exception:
                            pass

    def download_one(
        self,
        dbx: dropbox.Dropbox,
        entry: Any,
        local_root: Path,
        total_files: int | None = None,
        allow_requeue: bool = True,
    ) -> str | None:
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
                return None

        max_retries = 3
        self.is_currently_downloading = True
        self.current_downloading_bytes = 0
        self.emit_stats()

        consecutive_stalls = 0
        needs_rewind = True

        for attempt in range(1, max_retries + 1):
            self._check_pause()
            if self.stop_requested:
                self.is_currently_downloading = False
                self.current_downloading_bytes = 0
                return None

            # Re-create client session on consecutive connection stalls to refresh stale TCP connection pools
            if attempt >= 2 and consecutive_stalls >= 1:
                try:
                    dbx = create_dropbox_client(
                        access_token=self.access_token,
                        refresh_token=self.refresh_token,
                        app_key=self.app_key,
                    )
                except Exception:
                    pass

            # Keep OAuth access token fresh for long-running sessions (e.g. 4+ hours)
            try:
                if hasattr(dbx, "check_and_refresh_access_token"):
                    dbx.check_and_refresh_access_token()
            except Exception:
                pass

            temp_file = local_file.with_name(f"{local_file.name}.tmp")
            use_range = False
            attempt_start_bytes = 0

            try:
                existing_bytes = temp_file.stat().st_size if temp_file.exists() else 0

                if file_size > 0 and existing_bytes == file_size:
                    exp_hash = getattr(entry, "content_hash", None)
                    if exp_hash:
                        self.file_changed.emit(f"🔍 Verifying file (0%): {file_display}")
                        self.is_inline_verifying = True
                        self._speed_window.clear()
                        self.instant_speed = 0.0
                        def _on_existing_hash_prog(pct: int, chunk_len: int = 0):
                            self.current_progress.emit(pct)
                            self.file_changed.emit(f"🔍 Verifying file ({pct}%): {file_display}")
                            if chunk_len > 0:
                                self.update_speed_tracker(chunk_len)
                            self.emit_stats()

                        try:
                            calc = compute_dropbox_content_hash(
                                temp_file,
                                check_pause_func=self._check_pause,
                                progress_cb=_on_existing_hash_prog,
                                stop_check_func=lambda: self.stop_requested,
                            )
                        finally:
                            self.is_inline_verifying = False
                            self._speed_window.clear()
                            self.instant_speed = 0.0
                        if self.stop_requested:
                            self.is_currently_downloading = False
                            self.current_downloading_bytes = 0
                            return None
                    else:
                        calc = None

                    if not exp_hash or (calc and calc.lower() == exp_hash.lower()):
                        self.file_changed.emit(f"💾 Finalizing file: {file_display}")
                        os.replace(temp_file, local_file)
                        self.done += 1
                        self.bytes_done += existing_bytes
                        self.is_currently_downloading = False
                        self.current_downloading_bytes = 0
                        self.current_progress.emit(100)
                        self.log.emit(f"DONE  [{folder_display}] {file_display} (resumed complete)")
                        self.emit_stats(force=True)
                        return None

                if existing_bytes >= file_size or existing_bytes < 0:
                    existing_bytes = 0
                    temp_file.unlink(missing_ok=True)
                    needs_rewind = False

                # Safety rewind by up to 4KB to discard partial/dirty tail chunk from a previous connection crash.
                # Only rewind if bytes were added or on initial file resume (prevents cumulative byte loss across zero-progress retries).
                if file_size > 0 and 0 < existing_bytes < file_size and needs_rewind:
                    rewind_bytes = min(4096, existing_bytes)
                    existing_bytes -= rewind_bytes
                    try:
                        with open(temp_file, "r+b") as pf:
                            pf.seek(existing_bytes)
                            pf.truncate()
                    except Exception:
                        pass
                    needs_rewind = False

                attempt_start_bytes = existing_bytes

                download_kwargs: dict[str, Any] = {"url": self.url, "path": api_path}
                if self.link_password:
                    download_kwargs["link_password"] = self.link_password

                use_range = (existing_bytes > 0 and file_size > 0)
                if use_range:
                    if not hasattr(dbx, "_headers") or dbx._headers is None:
                        dbx._headers = {}
                    dbx._headers["Range"] = f"bytes={existing_bytes}-"
                    pct_already = int(existing_bytes * 100 / file_size)
                    self.log.emit(
                        f"🔄 RESUME [{folder_display}] {file_display}: Continuing from {format_bytes(existing_bytes)} / {format_bytes(file_size)} ({pct_already}%) [Attempt {attempt}/{max_retries}]"
                    )
                elif attempt > 1:
                    self.log.emit(
                        f"🔄 RESTART [{folder_display}] {file_display}: Downloading from 0% [Attempt {attempt}/{max_retries}]"
                    )
                else:
                    self.log.emit(
                        f"GET   [{folder_display}] {file_display} ({format_bytes(file_size)}) [Attempt {attempt}/{max_retries}]"
                    )

                try:
                    res: Any = dbx.sharing_get_shared_link_file(**download_kwargs)
                finally:
                    if hasattr(dbx, "_headers") and isinstance(dbx._headers, dict):
                        dbx._headers.pop("Range", None)

                metadata, response = res
                try:
                    status_code = getattr(response, "status_code", None)
                    is_partial = (status_code == 206) or ("Content-Range" in getattr(response, "headers", {}))

                    if is_partial and use_range:
                        downloaded = existing_bytes
                        open_mode = "ab"
                    else:
                        if use_range and not is_partial:
                            if allow_requeue:
                                raise IOError(f"Server returned HTTP {status_code} instead of 206 Partial Content for range resume")
                            self.log.emit(
                                f"⚠️ RESTART [{folder_display}] {file_display}: Range request not supported by server (HTTP {status_code}). Restarting download from 0%..."
                            )
                            attempt_start_bytes = 0
                        downloaded = 0
                        open_mode = "wb"

                    self.current_downloading_bytes = downloaded
                    if file_size > 0:
                        self.current_progress.emit(int(downloaded * 100 / file_size))
                    self.emit_stats()

                    start_time = time.time()
                    last_chunk_time = time.time()

                    with open(temp_file, open_mode) as f:
                        for chunk in response.iter_content(chunk_size=1024 * 128):
                            now = time.time()
                            if not self._is_paused and (now - last_chunk_time > 30.0):
                                raise TimeoutError("Socket stream stalled: no data received for 30 seconds.")

                            if not self._pause_event.is_set():
                                self._check_pause()
                                last_chunk_time = time.time()
                            else:
                                last_chunk_time = now

                            if self.stop_requested:
                                f.close()
                                self.is_currently_downloading = False
                                self.current_downloading_bytes = 0
                                return None
                            if chunk:
                                f.write(chunk)
                                f.flush()
                                chunk_len = len(chunk)
                                downloaded += chunk_len
                                self.current_downloading_bytes = downloaded
                                self.update_speed_tracker(chunk_len)
                                self.emit_stats()
                                if file_size > 0:
                                    pct = int(downloaded * 100 / file_size)
                                    self.current_progress.emit(pct)
                finally:
                    try:
                        response.close()
                    except Exception:
                        pass

                actual_size = temp_file.stat().st_size
                if file_size > 0 and actual_size != file_size:
                    raise IOError(f"size mismatch: expected {file_size}, got {actual_size}")

                exp_hash = getattr(entry, "content_hash", None) or getattr(metadata, "content_hash", None)
                if exp_hash:
                    self.file_changed.emit(f"🔍 Verifying file (0%): {file_display}")
                    self.is_inline_verifying = True
                    self._speed_window.clear()
                    self.instant_speed = 0.0
                    def _on_hash_prog(pct: int, chunk_len: int = 0):
                        self.current_progress.emit(pct)
                        self.file_changed.emit(f"🔍 Verifying file ({pct}%): {file_display}")
                        if chunk_len > 0:
                            self.update_speed_tracker(chunk_len)
                        self.emit_stats()

                    try:
                        calc = compute_dropbox_content_hash(
                            temp_file,
                            check_pause_func=self._check_pause,
                            progress_cb=_on_hash_prog,
                            stop_check_func=lambda: self.stop_requested,
                        )
                    finally:
                        self.is_inline_verifying = False
                        self._speed_window.clear()
                        self.instant_speed = 0.0
                    if self.stop_requested:
                        self.is_currently_downloading = False
                        self.current_downloading_bytes = 0
                        return None
                    if calc and calc.lower() != exp_hash.lower():
                        temp_file.unlink(missing_ok=True)
                        raise IOError(f"checksum mismatch: expected {exp_hash}, got {calc}")
                elif self.stop_requested:
                    self.is_currently_downloading = False
                    self.current_downloading_bytes = 0
                    return None

                if hasattr(entry, "content_hash") and not getattr(entry, "content_hash", None) and exp_hash:
                    entry.content_hash = exp_hash

                self.file_changed.emit(f"💾 Finalizing file: {file_display}")
                os.replace(temp_file, local_file)
                self.done += 1
                self.bytes_done += actual_size
                self.is_currently_downloading = False
                self.current_downloading_bytes = 0
                self.current_progress.emit(100)
                self.log.emit(f"DONE  [{folder_display}] {file_display}")
                self.emit_stats(force=True)
                return None

            except Exception as exc:
                curr_saved = temp_file.stat().st_size if temp_file.exists() else 0
                if curr_saved > attempt_start_bytes:
                    consecutive_stalls = 0
                    needs_rewind = True
                else:
                    consecutive_stalls += 1

                if "416" in str(exc):
                    temp_file.unlink(missing_ok=True)
                    curr_saved = 0
                    needs_rewind = False

                if use_range and allow_requeue and ("416" in str(exc) or "range" in str(exc).lower()):
                    self.log.emit(
                        f"⏳ QUEUE [{folder_display}] {file_display}: Server Range error ({parse_friendly_error(exc)[0]}). Re-queuing file to try again later..."
                    )
                    self.is_currently_downloading = False
                    self.current_downloading_bytes = 0
                    return "requeue"

                # If connection stalls continuously with 0 progress on a range request, requeue or fallback to downloading from 0
                if consecutive_stalls >= 2 and use_range:
                    if allow_requeue:
                        self.log.emit(
                            f"⏳ QUEUE [{folder_display}] {file_display}: Connection stalled ({consecutive_stalls} consecutive timeouts). Moving to end of download queue to allow CDN rate limits to reset..."
                        )
                        self.is_currently_downloading = False
                        self.current_downloading_bytes = 0
                        return "requeue"
                    elif attempt < max_retries:
                        self.log.emit(
                            f"⚠️ RESTART [{folder_display}] {file_display}: Range resume stalled ({consecutive_stalls} consecutive timeouts). Resetting partial download and restarting from 0%..."
                        )
                        temp_file.unlink(missing_ok=True)
                        consecutive_stalls = 0
                        needs_rewind = False
                        curr_saved = 0

                if "checksum mismatch" in str(exc).lower() or "size mismatch" in str(exc).lower():
                    temp_file.unlink(missing_ok=True)
                    curr_saved = 0
                    needs_rewind = False

                if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                    temp_file.unlink(missing_ok=True)
                    curr_saved = 0
                    self.errors += 1
                    self.is_currently_downloading = False
                    self.current_downloading_bytes = 0
                    self.emit_stats(force=True)
                    self.log.emit(f"🔒 ERROR [{folder_display}] {file_display}: Password protected. Verify link password.")
                    return None

                if attempt < max_retries and not self.stop_requested:
                    err_title, _ = parse_friendly_error(exc)
                    progress_info = f" ({format_bytes(curr_saved)} saved)" if curr_saved > 0 else ""
                    wait_sec = min(consecutive_stalls * 3 + attempt * 2, 15)
                    self.log.emit(
                        f"⚠️ RETRY [{folder_display}] {file_display} (Attempt {attempt}/{max_retries}){progress_info}: {err_title} - Retrying in {wait_sec}s..."
                    )
                    for _ in range(wait_sec * 10):
                        if self.stop_requested:
                            self.is_currently_downloading = False
                            self.current_downloading_bytes = 0
                            return None
                        self._check_pause()
                        time.sleep(0.1)
                else:
                    self.errors += 1
                    self.is_currently_downloading = False
                    self.current_downloading_bytes = 0
                    self.emit_stats(force=True)
                    err_title, err_desc = parse_friendly_error(exc)
                    self.log.emit(
                        f"❌ ERROR [{folder_display}] {file_display}: {err_title} ({err_desc.splitlines()[0]}) after {max_retries} attempts"
                    )
                    return None

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

            raw_root_name = getattr(metadata, "name", None) or "DropboxFolder"
            root_name = sanitize_filename(raw_root_name) or "DropboxFolder"
            local_root = self.destination
            local_root.mkdir(parents=True, exist_ok=True)
            self.log.emit(f"📁 Destination folder: {local_root}")

            if self.scanned_entries:
                self.log.emit("⚡ Using pre-scanned folder hierarchy (instant start)...")
                for e in self.scanned_entries:
                    if not e.get("is_dir"):
                        rel = e.get("path") or e.get("rel_path") or ""
                        api_path = f"/{rel}" if not rel.startswith("/") else rel
                        self.files.append(
                            DownloadFileItem(
                                name=e.get("name") or Path(rel).name,
                                size=int(e.get("size", 0) or 0),
                                rel_path=rel,
                                api_path=api_path,
                                content_hash=e.get("content_hash"),
                            )
                        )
            else:
                self.log.emit("🔍 Querying Dropbox hierarchy...")
                shared_link = SharedLink(
                    url=self.url,
                    password=self.link_password if self.link_password else None,
                )
                self.collect_parallel(dbx, shared_link)

            if self.stop_requested:
                self.finished.emit("Download stopped.")
                return

            # Filter files by user selection in tree
            all_discovered = list(self.files)
            filtered_files: list[DownloadFileItem] = []
            deselected_count = 0
            for entry in all_discovered:
                rel = getattr(entry, "rel_path", None) or getattr(entry, "_custom_rel_path", None) or relative_path(entry)
                if self.is_selected(rel):
                    filtered_files.append(entry)
                else:
                    deselected_count += 1

            if deselected_count > 0:
                self.log.emit(f"ℹ Excluded {deselected_count} unselected file(s) from download.")

            # Sort all selected files strictly in natural hierarchical order
            filtered_files.sort(key=natural_sort_path_key)
            self.files = filtered_files
            total_selected = len(self.files)

            self.log.emit(f"✓ Selected {total_selected} of {len(all_discovered)} file(s) to download.")

            # Check if exactly 1 folder was selected and destination folder name matches
            matched_folder, stripped_prefix = check_single_folder_destination_match(
                filtered_files,
                self.destination,
                self.single_selected_folder,
            )
            if matched_folder and stripped_prefix:
                dest_display_name = self.destination.resolve().name if self.destination.is_absolute() else self.destination.name
                self.log.emit(
                    f"📁 Destination folder '{dest_display_name}' matches selected folder '{matched_folder}'.\n"
                    f"   Downloading contents directly into: {local_root} (no duplicate nested folder created)"
                )
                for entry in filtered_files:
                    entry.rel_path = strip_folder_prefix(entry.rel_path, stripped_prefix)

            files_to_download: list[DownloadFileItem] = list(self.files)

            if self.skip_existing and total_selected > 0:
                # Check if the system finds at least one already existing file
                first_existing: DownloadFileItem | None = None
                for entry in self.files:
                    loc = safe_local_path(local_root, entry.rel_path)
                    if loc.exists() and loc.is_file() and loc.stat().st_size == entry.size:
                        first_existing = entry
                        break

                if first_existing is not None:
                    first_clean = first_existing.rel_path.replace("\\", "/").strip("/")
                    first_folder = Path(first_clean).parent.as_posix() if "/" in first_clean else "/ (Root)"
                    self.log.emit(
                        f"🔍 Existing file detected: [{first_folder}] {first_existing.name}\n"
                        f"⚡ Scanning all {total_selected} file(s) to check for more existing files..."
                    )

                    existing_items: list[DownloadFileItem] = []
                    remaining_items: list[DownloadFileItem] = []

                    for s_idx, entry in enumerate(self.files, start=1):
                        self._check_pause()
                        if self.stop_requested:
                            self.finished.emit("Download stopped.")
                            return

                        loc = safe_local_path(local_root, entry.rel_path)
                        if loc.exists() and loc.is_file() and loc.stat().st_size == entry.size:
                            existing_items.append(entry)
                            self.skipped += 1
                            self.bytes_done += entry.size
                            rel_clean = entry.rel_path.replace("\\", "/").strip("/")
                            folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
                            self.log.emit(f"SKIP  [{folder_display}] {entry.name} (already exists)")
                            self.overall_progress.emit(int(s_idx * 100 / total_selected))
                            self.emit_stats()
                        else:
                            remaining_items.append(entry)

                    existing_bytes = sum(it.size for it in existing_items)
                    self.log.emit(
                        f"✓ Local scan completed: Found {len(existing_items)} existing file(s) ({format_bytes(existing_bytes)}).\n"
                        f"🚀 Downloading remaining {len(remaining_items)} file(s) in sequential order..."
                    )

                    # Update UI progress and stats with scanned existing items
                    if total_selected > 0:
                        self.overall_progress.emit(int(len(existing_items) * 100 / total_selected))

                    self.emit_stats()

                    files_to_download = remaining_items
                else:
                    self.log.emit("🚀 Starting direct selective download in sequential order...")
            else:
                self.log.emit("🚀 Starting direct selective download in sequential order...")

            if not files_to_download and total_selected > 0:
                if not self.verify_integrity:
                    elapsed = max(time.time() - self.started - self.paused_duration, 0.1)
                    self.overall_progress.emit(100)
                    self.current_progress.emit(100)
                    message = (
                        f"✓ Download Finished: All files already exist locally!\n\n"
                        f"Files Selected: {total_selected}\n"
                        f"Completed: 0 (Already downloaded)\n"
                        f"Skipped: {self.skipped}\n"
                        f"Errors: {self.errors}\n"
                        f"Data Transferred: {format_bytes(self.bytes_done)}\n"
                        f"Time Elapsed: {elapsed:.1f}s\n"
                        f"Output Directory: {local_root}"
                    )
                    self.finished.emit(message)
                    return
                else:
                    self.log.emit("✓ All files detected locally. Proceeding to file integrity verification...")

            if not self.verify_only:
                initial_offset = total_selected - len(files_to_download)
                download_queue: list[DownloadFileItem] = list(files_to_download)
                state_file = local_root / ".download_state.json"
                requeue_counts: dict[str, int] = {}
                if state_file.exists():
                    try:
                        with open(state_file, "r", encoding="utf-8") as sf:
                            saved_state = json.load(sf)
                            if isinstance(saved_state, dict) and "requeue_counts" in saved_state:
                                requeue_counts = saved_state.get("requeue_counts", {})
                    except Exception:
                        pass

                processed_count = 0

                while download_queue and not self.stop_requested:
                    self._check_pause()
                    if self.stop_requested:
                        break

                    entry = download_queue.pop(0)
                    entry_key = getattr(entry, "rel_path", None) or getattr(entry, "name", str(entry))

                    processed_count += 1
                    current_index = initial_offset + processed_count
                    self.overall_progress.emit(
                        int((current_index - 1) * 100 / max(total_selected, 1))
                    )

                    times_requeued = requeue_counts.get(entry_key, 0)
                    can_requeue = (times_requeued < 3) and bool(download_queue)

                    res_status = self.download_one(
                        dbx,
                        entry,
                        local_root,
                        total_files=total_selected,
                        allow_requeue=can_requeue,
                    )

                    if res_status == "requeue":
                        new_count = times_requeued + 1
                        requeue_counts[entry_key] = new_count
                        try:
                            with open(state_file, "w", encoding="utf-8") as sf:
                                json.dump({"requeue_counts": requeue_counts}, sf, indent=2)
                        except Exception:
                            pass
                        download_queue.append(entry)
                        processed_count -= 1
                        file_disp = getattr(entry, "name", "file")
                        self.log.emit(
                            f"⏳ REQUEUED [{file_disp}] -> Moved to end of download queue (Queue Pass {new_count}/3)"
                        )
                    else:
                        self.overall_progress.emit(
                            int(current_index * 100 / max(total_selected, 1))
                        )

                if not download_queue and not self.stop_requested:
                    try:
                        state_file.unlink(missing_ok=True)
                    except Exception:
                        pass

            # Verification Phase: Checks integrity of all selected files
            if self.verify_integrity and not self.stop_requested and total_selected > 0:
                self.is_verifying = True
                self.log.emit("\n" + "=" * 60)
                if self.verify_only:
                    self.log.emit(f"🔍 Starting File Integrity Verification ({total_selected} file(s))...")
                else:
                    self.log.emit(f"🔍 Post-Download Verification: Checking {total_selected} file(s) for corruption...")
                self.log.emit("🔍 Verifying exact file sizes and Dropbox SHA-256 block hashes...")
                self.log.emit("=" * 60)
                self.folder_changed.emit("Verifying Files...")
                self.overall_progress.emit(0)

                corrupted_items: list[tuple[DownloadFileItem, str]] = []

                for v_idx, entry in enumerate(self.files, start=1):
                    self._check_pause()
                    if self.stop_requested:
                        break

                    rel_clean = entry.rel_path.replace("\\", "/").strip("/")
                    folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
                    file_display = entry.name or Path(rel_clean).name

                    self.folder_changed.emit(f"Verifying ({v_idx}/{total_selected}): [{folder_display}]")
                    self.file_changed.emit(f"{file_display}  ({format_bytes(entry.size)})")
                    self.current_progress.emit(0)

                    local_file = safe_local_path(local_root, entry.rel_path)

                    if not local_file.exists() or not local_file.is_file():
                        self.missing += 1
                        self.log.emit(f"❌ MISSING [{folder_display}] {file_display}: File not found on disk.")
                        corrupted_items.append((entry, "file missing on disk"))
                        continue

                    actual_size = local_file.stat().st_size
                    if actual_size != entry.size:
                        self.corrupted += 1
                        self.log.emit(
                            f"❌ CORRUPTED [{folder_display}] {file_display}: Size mismatch! "
                            f"(Expected {format_bytes(entry.size)}, got {format_bytes(actual_size)})"
                        )
                        corrupted_items.append((entry, f"size mismatch (expected {entry.size}, got {actual_size})"))
                        continue

                    # Hash check
                    expected_hash = entry.content_hash or (getattr(entry.metadata, "content_hash", None) if entry.metadata else None)
                    try:
                        self.file_changed.emit(f"🔍 Verifying file (0%): {file_display}")
                        def on_v_prog(pct: int, chunk_len: int = 0):
                            self.current_progress.emit(pct)
                            self.file_changed.emit(f"🔍 Verifying file ({pct}%): {file_display}")
                            if chunk_len > 0:
                                self.update_speed_tracker(chunk_len)
                            self.emit_stats()

                        calc_hash = compute_dropbox_content_hash(
                            local_file,
                            check_pause_func=self._check_pause,
                            progress_cb=on_v_prog,
                            stop_check_func=lambda: self.stop_requested,
                        )
                        if self.stop_requested:
                            break

                        if expected_hash and calc_hash.lower() != expected_hash.lower():
                            self.corrupted += 1
                            self.log.emit(
                                f"❌ CORRUPTED [{folder_display}] {file_display}: Checksum mismatch! "
                                f"(Expected {expected_hash[:10]}..., got {calc_hash[:10]}...)"
                            )
                            corrupted_items.append((entry, "checksum mismatch"))
                            continue

                        self.verified_ok += 1
                        self.current_progress.emit(100)
                        hash_note = f" [Hash: {calc_hash[:8]}...]" if expected_hash else ""
                        self.log.emit(f"✓ VERIFIED [{folder_display}] {file_display}{hash_note}")

                    except Exception as err:
                        self.corrupted += 1
                        self.log.emit(f"❌ UNREADABLE [{folder_display}] {file_display}: {err}")
                        corrupted_items.append((entry, f"unreadable: {err}"))

                    self.overall_progress.emit(int(v_idx * 100 / total_selected))
                    self.emit_stats()


                # Auto-Repair Phase
                if self.auto_repair and corrupted_items and not self.stop_requested and not self.verify_only:
                    self.log.emit(f"\n🔧 Auto-Repair: Re-downloading {len(corrupted_items)} corrupted/missing file(s)...")
                    for bad_entry, reason in corrupted_items:
                        self._check_pause()
                        if self.stop_requested:
                            break

                        rel_clean = bad_entry.rel_path.replace("\\", "/").strip("/")
                        folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
                        file_display = bad_entry.name or Path(rel_clean).name

                        self.log.emit(f"🔄 REPAIRING [{folder_display}] {file_display} ({reason})...")
                        bad_path = safe_local_path(local_root, bad_entry.rel_path)
                        bad_path.unlink(missing_ok=True)

                        # Re-download
                        self.download_one(dbx, bad_entry, local_root, total_files=total_selected, allow_requeue=False)
                        if self.stop_requested:
                            break

                        # Re-verify repaired file
                        if bad_path.exists() and bad_path.is_file():
                            try:
                                repaired_size = bad_path.stat().st_size
                                if repaired_size == bad_entry.size:
                                    self.file_changed.emit(f"🔍 Verifying repaired file (0%): {file_display}")
                                    def on_repair_v_prog(pct: int, chunk_len: int = 0):
                                        self.current_progress.emit(pct)
                                        self.file_changed.emit(f"🔍 Verifying repaired file ({pct}%): {file_display}")
                                        if chunk_len > 0:
                                            self.update_speed_tracker(chunk_len)
                                        self.emit_stats()

                                    calc_h = compute_dropbox_content_hash(
                                        bad_path,
                                        check_pause_func=self._check_pause,
                                        progress_cb=on_repair_v_prog,
                                        stop_check_func=lambda: self.stop_requested,
                                    )
                                    if self.stop_requested:
                                        break
                                    exp_h = bad_entry.content_hash or (getattr(bad_entry.metadata, "content_hash", None) if bad_entry.metadata else None)
                                    if not exp_h or calc_h.lower() == exp_h.lower():
                                        self.repaired += 1
                                        if self.corrupted > 0:
                                            self.corrupted -= 1
                                        self.verified_ok += 1
                                        self.log.emit(f"✓ REPAIRED [{folder_display}] {file_display}: Re-downloaded and verified intact!")
                                        continue
                            except Exception:
                                pass
                        self.log.emit(f"❌ REPAIR FAILED [{folder_display}] {file_display}: Still invalid after re-download.")

            elapsed = max(time.time() - self.started - self.paused_duration, 0.1)

            if self.stop_requested:
                message = "Download cancelled by user."
            else:
                lines = []
                if self.verify_only:
                    if self.corrupted > 0 or self.missing > 0:
                        lines.append("⚠️ Verification Completed with Warnings!")
                    else:
                        lines.append("✓ Verification Completed Successfully!")
                elif self.verify_integrity:
                    if self.corrupted > 0 or self.missing > 0 or self.errors > 0:
                        lines.append("⚠️ Download Finished with Verification Warnings!")
                    else:
                        lines.append("✓ Download & Verification Finished Successfully!")
                else:
                    lines.append("✓ Download Finished Successfully!")

                lines.append("")
                lines.append(f"Files Selected: {total_selected}")
                if not self.verify_only:
                    lines.append(f"Completed: {self.done}")
                    lines.append(f"Skipped: {self.skipped}")
                if self.verify_integrity:
                    lines.append(f"Verified Intact: {self.verified_ok} of {total_selected}")
                    if self.repaired > 0:
                        lines.append(f"Auto-Repaired: {self.repaired}")
                    if self.corrupted > 0:
                        lines.append(f"Corrupted: {self.corrupted}")
                    if self.missing > 0:
                        lines.append(f"Missing: {self.missing}")
                if self.errors > 0:
                    lines.append(f"Errors: {self.errors}")
                if not self.verify_only:
                    lines.append(f"Data Transferred: {format_bytes(self.bytes_done)}")
                lines.append(f"Time Elapsed: {elapsed:.1f}s")
                lines.append(f"Output Directory: {local_root}")
                message = "\n".join(lines)

            self.finished.emit(message)

        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass

