import time
from typing import Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import dropbox
from dropbox.files import FileMetadata, FolderMetadata, SharedLink
from dropbox.exceptions import ApiError

from .utils import format_bytes, is_path_selected


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


class _DownloadCollectMixin:
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
                speed_str = (
                    f"{format_bytes(int(self.instant_speed))}/s (Verify)"
                    if self.instant_speed > 0
                    else "0 B/s (Verify)"
                )
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
            processed = min(
                self.done + self.skipped + (1 if self.is_currently_downloading else 0),
                total_count,
            )
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

    def resume(self):
        if self._is_paused:
            if self.pause_start_time > 0:
                self.paused_duration += max(time.time() - self.pause_start_time, 0.0)
                self.pause_start_time = 0.0
            self._is_paused = False
            self._pause_event.set()
            self.paused_signal.emit(False)

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

