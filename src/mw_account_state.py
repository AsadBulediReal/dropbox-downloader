import os
from pathlib import Path

from PySide6.QtCore import Qt

from .utils import format_bytes, is_thread_running


class _AccountStateMixin:
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

    def _update_verify_integrity_badge(self):
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

    def _on_verify_setting_changed(self):
        self._update_verify_integrity_badge()
        self.save_settings()

    def get_app_key(self) -> str:
        return os.getenv("DROPBOX_APP_KEY", "").strip() or getattr(self, "custom_app_key", "").strip()

    def is_logged_in(self) -> bool:
        return bool(self.current_refresh_token or self.current_access_token)

    def update_account_ui(self):
        logged_in = self.is_logged_in()
        if logged_in:
            display_name = self.current_user_name or ""
            email = self.current_user_email or ""
            primary_acct = email or display_name or "Connected Account"
            self.account_name_label.setText(primary_acct)
            if display_name and email:
                self.account_name_label.setToolTip(f"{display_name} <{email}>")
            else:
                self.account_name_label.setToolTip(primary_acct)
            self.account_sub_label.setText("● Connected via PKCE OAuth")
            self.set_auth_badge("● Connected", "connected")
            self.btn_oauth_login.setText("Switch")
            self.btn_oauth_login.setProperty("class", "drawer-acct-btn")
            self._repolish(self.btn_oauth_login)
            self.btn_logout.setVisible(True)
            self.login_banner.setVisible(False)
        else:
            self.account_name_label.setText("No Dropbox account connected")
            self.account_name_label.setToolTip("")
            self.account_sub_label.setText("Sign in to your Dropbox account")
            self.set_auth_badge("○ Not Logged In", "neutral")
            self.btn_oauth_login.setText("Log In")
            self.btn_oauth_login.setProperty("class", "drawer-save-btn")
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

