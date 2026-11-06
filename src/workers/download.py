import time
import json
import threading
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from dropbox.files import SharedLink
from dropbox.exceptions import ApiError, AuthError
from PySide6.QtCore import QObject, QThread, Signal, Slot

from ..utils import (
    format_bytes,
    sanitize_filename,
    natural_sort_path_key,
    safe_local_path,
    strip_folder_prefix,
    check_single_folder_destination_match,
    relative_path,
)
from .collect_mixin import DownloadFileItem, _DownloadCollectMixin
from .transfer_mixin import _DownloadTransferMixin
from .verify_mixin import _DownloadVerifyMixin
import src.workers as _workers_pkg


class DownloadWorker(QObject, _DownloadCollectMixin, _DownloadTransferMixin, _DownloadVerifyMixin):
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
            dbx = _workers_pkg.create_dropbox_client(
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
            except ApiError as exc:
                if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                    raise ValueError(
                        "Access Denied: This link is password-protected or restricted.\n"
                        "Please verify the folder password entered in the credentials section."
                    )
                raise

            raw_root_name = getattr(metadata, "name", None) or "DropboxFolder"
            _ = sanitize_filename(raw_root_name) or "DropboxFolder"
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

            filtered_files.sort(key=natural_sort_path_key)
            self.files = filtered_files
            total_selected = len(self.files)

            self.log.emit(f"✓ Selected {total_selected} of {len(all_discovered)} file(s) to download.")

            matched_folder, stripped_prefix = check_single_folder_destination_match(
                filtered_files,
                self.destination,
                self.single_selected_folder,
            )
            if matched_folder and stripped_prefix:
                dest_display_name = (
                    self.destination.resolve().name if self.destination.is_absolute() else self.destination.name
                )
                self.log.emit(
                    f"📁 Destination folder '{dest_display_name}' matches selected folder '{matched_folder}'.\n"
                    f"   Downloading contents directly into: {local_root} (no duplicate nested folder created)"
                )
                for entry in filtered_files:
                    entry.rel_path = strip_folder_prefix(entry.rel_path, stripped_prefix)

            files_to_download: list[DownloadFileItem] = list(self.files)

            if self.skip_existing and total_selected > 0:
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

            if self.verify_integrity and not self.stop_requested and total_selected > 0:
                self._run_verification_and_repair(dbx, local_root, total_selected)

            elapsed = max(time.time() - self.started - self.paused_duration, 0.1)
            message = self._build_completion_message(local_root, total_selected, elapsed)
            self.finished.emit(message)

        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass

