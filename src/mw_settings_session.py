import json
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QTimer

from . import main_window as _mw
from .utils import (
    extract_folder_name_from_url,
    parse_friendly_error,
    is_thread_running,
)


class _SettingsSessionMixin:
    def load_settings(self):
        self._loading_settings = True
        try:
            saved_theme = str(self.settings.value("theme_mode", "light")).strip().lower()
            self.apply_theme(saved_theme if saved_theme in ("light", "dark") else "light", save=False)

            saved_dest = str(self.settings.value("destination", str(Path.home() / "Downloads")))
            if saved_dest:
                self.destination_input.blockSignals(True)
                self.destination_input.setText(saved_dest)
                self.destination_input.blockSignals(False)
                self._on_destination_changed(saved_dest)

            skip_raw = self.settings.value("skip_existing", True)
            self.check_skip_existing.blockSignals(True)
            self.check_skip_existing.setChecked(str(skip_raw).strip().lower() in ("true", "1"))
            self.check_skip_existing.blockSignals(False)

            verify_raw = self.settings.value("verify_integrity", True)
            self.check_verify_integrity.blockSignals(True)
            self.check_verify_integrity.setChecked(str(verify_raw).strip().lower() in ("true", "1"))
            self.check_verify_integrity.blockSignals(False)
            self._update_verify_integrity_badge()

            repair_raw = self.settings.value("auto_repair", True)
            self.check_auto_repair.blockSignals(True)
            self.check_auto_repair.setChecked(str(repair_raw).strip().lower() in ("true", "1"))
            self.check_auto_repair.blockSignals(False)

            self.custom_app_key = str(self.settings.value("app_key", "")).strip()

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

            if self.settings.contains("token"):
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
        finally:
            self._loading_settings = False

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

    def _on_verify_finished_impl(self, name: str, email: str):
        if name:
            self.current_user_name = name
        if email:
            self.current_user_email = email
        self.save_settings()
        self.update_account_ui()
        self.add_log(f"🔑 Restored session: {self.current_user_name} <{self.current_user_email}>")

    def _on_verify_expired_impl(self, exc_msg: str):
        title, msg = parse_friendly_error(exc_msg)
        self.add_log(f"⚠ Session expired: {msg.splitlines()[0]} Signing out...")
        self.current_access_token = ""
        self.current_refresh_token = ""
        self.current_user_name = ""
        self.current_user_email = ""
        self.save_settings()
        self.update_account_ui()

    def _on_verify_failed_impl(self, exc_msg: str):
        title, msg = parse_friendly_error(exc_msg)
        self.add_log(f"⚠ Session check: {msg.splitlines()[0]} Please sign in again if needed.")

    def _on_auth_status_impl(self, msg: str):
        self.add_log(f"ℹ {msg}")

    def verify_saved_session(self):
        if not self.is_logged_in():
            return

        self.cleanup_verify_thread()
        t = QThread()
        w = _mw.SessionVerifyWorker(
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
        if getattr(self, "_loading_settings", False):
            return

        self.settings.setValue("theme_mode", self.theme_mode)
        self.settings.setValue("destination", self.destination_input.text().strip())
        self.settings.setValue("skip_existing", self.check_skip_existing.isChecked())
        self.settings.setValue("verify_integrity", self.check_verify_integrity.isChecked())
        self.settings.setValue("auto_repair", self.check_auto_repair.isChecked())

        if getattr(self, "custom_app_key", ""):
            self.settings.setValue("app_key", self.custom_app_key)
        else:
            self.settings.remove("app_key")

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

        self.settings.sync()

