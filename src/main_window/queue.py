import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidgetItem

from ..utils import (
    format_bytes,
    is_thread_running,
    get_file_type_and_icon,
)


class _QueueMixin:
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
        selected_entries = self._collect_selected_entries_for_queue()

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

