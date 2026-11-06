import os
import time
from pathlib import Path
from typing import Any

import dropbox

from ..utils import (
    parse_friendly_error,
    format_bytes,
    safe_local_path,
    relative_path,
)
from .collect_mixin import DownloadFileItem
import src.workers as _workers_pkg


class _DownloadTransferMixin:
    def _handle_transfer_attempt_error(
        self,
        exc: Exception,
        temp_file: Path,
        attempt_start_bytes: int,
        consecutive_stalls: int,
        needs_rewind: bool,
        use_range: bool,
        allow_requeue: bool,
        attempt: int,
        max_retries: int,
        folder_display: str,
        file_display: str,
    ) -> tuple[str | None, int, bool]:
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
            return "requeue", consecutive_stalls, needs_rewind

        # If connection stalls continuously with 0 progress on a range request, requeue or fallback to downloading from 0
        if consecutive_stalls >= 2 and use_range:
            if allow_requeue:
                self.log.emit(
                    f"⏳ QUEUE [{folder_display}] {file_display}: Connection stalled ({consecutive_stalls} consecutive timeouts). Moving to end of download queue to allow CDN rate limits to reset..."
                )
                self.is_currently_downloading = False
                self.current_downloading_bytes = 0
                return "requeue", consecutive_stalls, needs_rewind
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
            self.errors += 1
            self.is_currently_downloading = False
            self.current_downloading_bytes = 0
            self.emit_stats(force=True)
            self.log.emit(f"🔒 ERROR [{folder_display}] {file_display}: Password protected. Verify link password.")
            return "done", consecutive_stalls, needs_rewind

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
                    return "done", consecutive_stalls, needs_rewind
                self._check_pause()
                time.sleep(0.1)
            return None, consecutive_stalls, needs_rewind

        self.errors += 1
        self.is_currently_downloading = False
        self.current_downloading_bytes = 0
        self.emit_stats(force=True)
        err_title, err_desc = parse_friendly_error(exc)
        self.log.emit(
            f"❌ ERROR [{folder_display}] {file_display}: {err_title} ({err_desc.splitlines()[0]}) after {max_retries} attempts"
        )
        return "done", consecutive_stalls, needs_rewind

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
            api_path = (
                getattr(entry, "api_path", None)
                or getattr(entry, "_custom_api_path", None)
                or (f"/{rel}" if not rel.startswith("/") else rel)
            )
            file_size = getattr(entry, "size", 0)
            file_name = getattr(entry, "name", Path(rel).name)

        local_file = safe_local_path(local_root, rel)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        rel_clean = rel.replace("\\", "/").strip("/")
        folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
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
                    dbx = _workers_pkg.create_dropbox_client(
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
                        calc = self._inline_verify_temp_file(temp_file, exp_hash, file_display)
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
                                raise IOError(
                                    f"Server returned HTTP {status_code} instead of 206 Partial Content for range resume"
                                )
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
                    calc = self._inline_verify_temp_file(temp_file, exp_hash, file_display)
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
                outcome, consecutive_stalls, needs_rewind = self._handle_transfer_attempt_error(
                    exc=exc,
                    temp_file=temp_file,
                    attempt_start_bytes=attempt_start_bytes,
                    consecutive_stalls=consecutive_stalls,
                    needs_rewind=needs_rewind,
                    use_range=use_range,
                    allow_requeue=allow_requeue,
                    attempt=attempt,
                    max_retries=max_retries,
                    folder_display=folder_display,
                    file_display=file_display,
                )
                if outcome == "requeue":
                    return "requeue"
                if outcome == "done":
                    return None
        return None
