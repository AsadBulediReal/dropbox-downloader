from PySide6.QtCore import QThread, Qt, QTimer

import src.main_window as _mw
from ..utils import parse_friendly_error, is_thread_running


class _OAuthMixin:
    def login_with_dropbox(self):
        app_key = self.get_app_key()
        entered_custom_key = ""

        if not app_key:
            key, ok = _mw.ModernInputDialog.get_text(
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
            app_key = key.strip()
            entered_custom_key = app_key

        try:
            flow = _mw.dropbox.DropboxOAuth2FlowNoRedirect(
                consumer_key=app_key,
                consumer_secret=None,
                use_pkce=True,
                token_access_type="offline",
            )
            authorize_url = flow.start()
            _mw.webbrowser.open(authorize_url)

            code, ok = _mw.ModernInputDialog.get_text(
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

            loading_dialog = _mw.ModernLoadingDialog(
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
            t = QThread()
            w = _mw.AuthWorker(flow=flow, code=code, app_key=app_key)
            w.moveToThread(t)

            w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
            w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
            t.finished.connect(w.deleteLater)
            t.finished.connect(t.deleteLater)

            def _on_auth_thread_finished(thread_ref=t):
                if getattr(self, "auth_thread", None) is thread_ref:
                    self.auth_thread = None
                    self.auth_worker = None
                self._active_workers.pop(thread_ref, None)

            t.finished.connect(_on_auth_thread_finished)

            self.auth_thread = t
            self.auth_worker = w
            self._active_workers[t] = w

            w.status.connect(loading_dialog.set_status)
            w.status.connect(self.on_auth_status)
            w.progress.connect(loading_dialog.set_progress)
            w.finished.connect(loading_dialog.on_auth_finished)
            w.failed.connect(loading_dialog.on_auth_failed)
            loading_dialog.cancelled.connect(w.cancel)

            t.started.connect(w.run)
            QTimer.singleShot(20, t.start)

            loading_dialog.exec()

            self.btn_oauth_login.setEnabled(True)
            self.btn_banner_login.setEnabled(True)
            self.btn_banner_login.setText("🌐  Log In to Dropbox")

            if loading_dialog.auth_success:
                if entered_custom_key:
                    self.custom_app_key = entered_custom_key
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
                    if self.is_logged_in() and not is_thread_running(self.download_thread)
                    else None,
                )

                if self.url_input.text().strip():
                    self.start_scan()
            elif loading_dialog.auth_error:
                self.update_account_ui()
                title, friendly = parse_friendly_error(loading_dialog.auth_error)
                self.add_log(f"✕ Login failed: {title} ({friendly.splitlines()[0]})")
                _mw.ModernMessageBox.error(
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
            self.btn_oauth_login.setEnabled(True)
            self.btn_banner_login.setEnabled(True)
            self.btn_banner_login.setText("🌐  Log In to Dropbox")
            self.update_account_ui()
            title, friendly = parse_friendly_error(exc)
            _mw.ModernMessageBox.error(
                self,
                f"Login Failed: {title}",
                f"Could not initialize Dropbox authorization:\n\n{friendly}",
            )

    def logout_dropbox(self):
        confirmed = _mw.ModernMessageBox.question(
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
            self.settings.sync()
            self.clear_url_and_tree()
            self.update_account_ui()
            self.close_settings_drawer()
            self.go_to_step(0)
            self.add_log("🔒 Logged out of Dropbox account. All features are now disabled.")

