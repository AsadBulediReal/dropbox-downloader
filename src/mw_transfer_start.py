from PySide6.QtCore import QThread, Qt

from . import main_window as _mw


class _TransferStartMixin:
    def set_running(self, running: bool):
        self._is_running = running
        self.btn_oauth_login.setEnabled(not running)
        self.btn_logout.setEnabled(not running)
        self.btn_verify_files.setEnabled(not running)
        self.update_feature_enabled_state()

        if running:
            self.realtime_stats_timer.start()
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if "verifying" not in curr.lower():
                self.set_status_badge("● Downloading...", "running")
        else:
            self.realtime_stats_timer.stop()
            self.tick_realtime_stats()
            curr = self.status_badge.text() if hasattr(self, "status_badge") else ""
            if not any(k in curr.lower() for k in ("completed", "warning", "error", "stopped")):
                if self.is_logged_in():
                    self.set_status_badge("● Ready", "ready")
                else:
                    self.set_status_badge("○ Login Required", "neutral")

    def start_download(self):
        if not self.is_logged_in():
            self.prompt_login_required("download files")
            return

        url = self.url_input.text().strip()
        destination = self.destination_input.text().strip()
        skip_existing = self.check_skip_existing.isChecked()
        verify_integrity = self.check_verify_integrity.isChecked()
        auto_repair = self.check_auto_repair.isChecked()
        link_password = (self.link_password or "").strip()

        if not url:
            _mw.ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a Dropbox shared link before downloading."
            )
            self.go_to_step(0)
            self.url_input.setFocus()
            return

        if not destination:
            _mw.ModernMessageBox.warning(
                self, "Missing Destination", "Please choose a local save destination folder in ⚙️ Settings."
            )
            self.open_settings_drawer()
            return

        info = self.get_tree_selection_info()
        if info["has_tree_items"]:
            if info["total_files"] > 0 and info["selected_file_count"] == 0:
                _mw.ModernMessageBox.warning(
                    self,
                    "No Files Selected",
                    "All files in the folder are currently deselected.\n\n"
                    "Please check at least one folder or file to download.",
                )
                return
            if info["total_files"] == 0 and not info["selected_folders"]:
                _mw.ModernMessageBox.warning(
                    self,
                    "No Items Selected",
                    "All items in the folder are currently deselected.\n\n"
                    "Please check at least one item to download.",
                )
                return

        self.save_settings()
        self.close_settings_drawer()
        self.hide_transfer_notice()

        root_name = getattr(self, "current_root_name", "")
        if not root_name and self.tree_widget.topLevelItemCount() > 0:
            top = self.tree_widget.topLevelItem(0)
            if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                root_name = top.data(3, Qt.ItemDataRole.UserRole) or ""
        self.add_recent_link(url, title=root_name, item_count=info.get("selected_file_count", 0))

        self.rebuild_queue_from_selection()
        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Initializing...")
        self.file_label.setText("Connecting to Dropbox API...")
        self.val_speed.setText("0 B/s")
        self.val_time.setText("00:00")
        self.val_eta.setText("")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause Download")
        self.pause_button.setProperty("class", "btn-pause")
        self._repolish(self.pause_button)

        self.set_running(True)
        self.go_to_step(2)

        self.add_log("▶ Starting selective download via Dropbox API...")
        if info["has_tree_items"] and info["total_files"] > 0:
            self.add_log(
                f"📋 Selection: {info['selected_file_count']} of {info['total_files']} files selected for download."
            )

        scanned_entries = None
        if getattr(self, "_tree_items_data", None) and getattr(self, "_scanned_url", None) == url:
            scanned_entries = self._tree_items_data

        self.cleanup_download_thread()
        t = QThread()
        w = _mw.DownloadWorker(
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
            single_selected_folder=info.get("single_selected_folder", ""),
            has_tree_filter=info["has_tree_items"],
            verify_integrity=verify_integrity,
            auto_repair=auto_repair,
            verify_only=False,
            scanned_entries=scanned_entries,
        )

        w.moveToThread(t)
        t.started.connect(w.run)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_download_thread_finished(thread_ref=t):
            if getattr(self, "download_thread", None) is thread_ref:
                self.download_thread = None
                self.worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_download_thread_finished)

        self.download_thread = t
        self.worker = w
        self._active_workers[t] = w

        w.log.connect(self.add_log)
        w.folder_changed.connect(self.folder_label.setText)
        w.file_changed.connect(self._on_worker_file_changed)
        w.current_progress.connect(self.update_file_progress)
        w.overall_progress.connect(self.update_overall_progress)
        w.stats_changed.connect(self.update_stats)
        w.paused_signal.connect(self.on_download_paused_changed)

        w.finished.connect(self.download_finished)
        w.failed.connect(self.download_failed)

        t.start()

    def start_verification_only(self):
        if not self.is_logged_in():
            self.prompt_login_required("verify downloaded files")
            return

        url = self.url_input.text().strip()
        destination = self.destination_input.text().strip()
        link_password = (self.link_password or "").strip()

        if not url:
            _mw.ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a Dropbox shared link before verifying."
            )
            self.go_to_step(0)
            self.url_input.setFocus()
            return

        if not destination:
            _mw.ModernMessageBox.warning(
                self, "Missing Destination", "Please choose a local save destination folder in ⚙️ Settings."
            )
            self.open_settings_drawer()
            return

        info = self.get_tree_selection_info()
        if info["has_tree_items"] and info["selected_file_count"] == 0:
            _mw.ModernMessageBox.warning(
                self,
                "No Files Selected",
                "Please select at least one file or folder from the tree to verify.",
            )
            return

        self.close_settings_drawer()
        self.hide_transfer_notice()
        self.rebuild_queue_from_selection()

        self.file_progress.setValue(0)
        self.overall_progress.setValue(0)
        self.file_pct_label.setText("0%")
        self.overall_pct_label.setText("0%")
        self.folder_label.setText("Verifying Files...")
        self.file_label.setText("Connecting to Dropbox API to check metadata...")
        self.val_speed.setText("0 B/s")
        self.val_time.setText("00:00")
        self.val_eta.setText("")

        self.is_download_paused = False
        self.pause_button.setText("⏸  Pause")
        self.pause_button.setProperty("class", "btn-pause")
        self._repolish(self.pause_button)

        self.set_running(True)
        self.set_status_badge("● Verifying...", "verifying")
        self.go_to_step(2)
        self.add_log("🔍 Starting on-demand file integrity verification...")

        auto_repair = self.check_auto_repair.isChecked()

        scanned_entries = None
        if getattr(self, "_tree_items_data", None) and getattr(self, "_scanned_url", None) == url:
            scanned_entries = self._tree_items_data

        self.cleanup_download_thread()
        t = QThread()
        w = _mw.DownloadWorker(
            url=url,
            destination=destination,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            link_password=link_password,
            skip_existing=True,
            selected_files=info["selected_files"],
            deselected_files=info["deselected_files"],
            selected_folders=info["selected_folders"],
            deselected_folders=info["deselected_folders"],
            single_selected_folder=info.get("single_selected_folder", ""),
            has_tree_filter=info["has_tree_items"],
            verify_integrity=True,
            auto_repair=auto_repair,
            verify_only=True,
            scanned_entries=scanned_entries,
        )

        w.moveToThread(t)
        t.started.connect(w.run)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_verify_download_thread_finished(thread_ref=t):
            if getattr(self, "download_thread", None) is thread_ref:
                self.download_thread = None
                self.worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_verify_download_thread_finished)

        self.download_thread = t
        self.worker = w
        self._active_workers[t] = w

        w.log.connect(self.add_log)
        w.folder_changed.connect(self.folder_label.setText)
        w.file_changed.connect(self._on_worker_file_changed)
        w.current_progress.connect(self.update_file_progress)
        w.overall_progress.connect(self.update_overall_progress)
        w.stats_changed.connect(self.update_stats)
        w.paused_signal.connect(self.on_download_paused_changed)

        w.finished.connect(self.download_finished)
        w.failed.connect(self.download_failed)

        t.start()

    def stop_download(self):
        if self.worker:
            if hasattr(self, "stop_button") and self.stop_button is not None:
                self.stop_button.setEnabled(False)
            if hasattr(self, "pause_button") and self.pause_button is not None:
                self.pause_button.setEnabled(False)
            self.worker.stop()
            self.add_log("⏹ Stop requested. Terminating whole operation...")
            self.set_status_badge("● Stopping...", "warning")

