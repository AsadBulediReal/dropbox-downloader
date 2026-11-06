import time

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

import src.main_window as _mw
from ..utils import parse_friendly_error, is_thread_running


class _TransferStatusMixin:
    def _add_log_impl(self, text: str):
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

    def _on_worker_file_changed_impl(self, text: str):
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
            self.show_transfer_notice("Operation Stopped", message, "neutral")
        elif has_corrupted or has_missing or has_errors or "warning" in message.lower():
            self.set_status_badge("⚠️ Warnings", "warning")
            self.folder_label.setText("Completed with Warnings")
            self.file_label.setText("Some files had verification or download issues")
            self.overall_pct_label.setText("100%")
            self.file_pct_label.setText("100%")
            self.file_progress.setValue(100)
            self.overall_progress.setValue(100)
            self.val_speed.setText("0 B/s")
            self.val_eta.setText("")
            self.show_transfer_notice("Completed with Warnings", message, "warning")
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
            self.show_transfer_notice("Completed Successfully", message, "success")

        self.update_feature_enabled_state()
        self.update_download_button_state()

    def download_failed(self, error: str):
        self.download_thread = None
        self.set_running(False)
        self.hide_transfer_notice()
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
            pwd, ok = _mw.ModernInputDialog.get_text(
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

        _mw.ModernMessageBox.error(self, title, friendly_msg)

