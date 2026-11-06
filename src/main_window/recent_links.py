import os
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QTreeWidgetItem,
    QMenu,
)

import src.main_window as _mw
from ..utils import extract_folder_name_from_url


class _RecentLinksMixin:
    def add_recent_link(self, url: str, title: str = "", item_count: int = 0):
        url = url.strip()
        if not url or "dropbox.com" not in url:
            return

        junk_titles = {"h", "fo", "fi", "sh", "scl", "dl", "dropbox folder", "dropboxfolder", ""}
        clean_title = (title or "").strip()
        if clean_title.lower() in junk_titles:
            clean_title = ""

        existing = next((item for item in self.recent_links if item.get("url") == url), None)

        if not clean_title:
            if existing and existing.get("title") and existing.get("title").strip().lower() not in junk_titles:
                clean_title = existing.get("title").strip()
            elif hasattr(self, "current_root_name") and self.current_root_name and self.current_root_name.strip().lower() not in junk_titles:
                clean_title = self.current_root_name.strip()
            elif hasattr(self, "tree_widget") and self.tree_widget.topLevelItemCount() > 0:
                top = self.tree_widget.topLevelItem(0)
                if top and top.data(0, Qt.ItemDataRole.UserRole) is not None:
                    raw = top.data(3, Qt.ItemDataRole.UserRole) or ""
                    if raw and raw.strip().lower() not in junk_titles:
                        clean_title = raw.strip()
            if not clean_title:
                clean_title = extract_folder_name_from_url(url)
            if not clean_title:
                clean_title = "Dropbox Folder"

        if item_count == 0 and existing and existing.get("item_count", 0) > 0:
            item_count = existing.get("item_count", 0)

        now = time.time()
        date_str = time.strftime("%b %d, %H:%M", time.localtime(now))

        filtered = [item for item in self.recent_links if item.get("url") != url]
        new_item = {
            "url": url,
            "title": clean_title,
            "item_count": item_count,
            "timestamp": now,
            "date_str": date_str,
        }
        self.recent_links = [new_item] + filtered
        self.recent_links = self.recent_links[:15]
        self.save_settings()
        self.update_recent_links_ui()

    def _clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()

    def update_recent_links_ui(self):
        if not hasattr(self, "recent_chips_layout") or not hasattr(self, "recent_rows_layout"):
            return

        self._clear_layout(self.recent_chips_layout)
        self._clear_layout(self.recent_rows_layout)

        if not self.recent_links:
            self.recent_chips_container.setVisible(False)
            empty_lbl = QLabel("Your recently opened Dropbox folders will appear here for 1-click access.")
            empty_lbl.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent; padding: 6px 0px;")
            self.recent_rows_layout.addWidget(empty_lbl)
            return

        # 1. Quick Recent Chips Row
        for item in self.recent_links[:4]:
            title = item.get("title") or "Dropbox Folder"
            display_name = (title[:22] + "…") if len(title) > 24 else title
            safe_chip_text = display_name.replace("&", "&&")

            chip_btn = QPushButton(f"📁 {safe_chip_text}")
            chip_btn.setProperty("class", "recent-chip")
            chip_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tooltip_txt = f"📁 {title}\n🔗 {item.get('url', '')}\n📅 Saved: {item.get('date_str', '')}"
            if item.get("item_count"):
                tooltip_txt += f"\n📊 {item.get('item_count')} items"
            chip_btn.setToolTip(tooltip_txt)

            chip_url = item.get("url", "")
            chip_btn.clicked.connect(lambda _, u=chip_url: self.load_recent_link(u))
            self.recent_chips_layout.addWidget(chip_btn)

        self.recent_chips_layout.addStretch()
        self.recent_chips_container.setVisible(True)

        # 2. Detailed Recent Rows (top 3)
        for idx, item in enumerate(self.recent_links[:3]):
            title = item.get("title") or "Dropbox Folder"
            url = item.get("url", "")
            cnt = item.get("item_count")
            meta_parts = []
            if cnt:
                meta_parts.append(f"{cnt} items")
            if item.get("date_str"):
                meta_parts.append(item.get("date_str"))
            meta_suffix = f"  •  {' • '.join(meta_parts)}" if meta_parts else ""
            short_url = url if len(url) <= 72 else (url[:69] + "...")

            row_widget = _mw._RecentLinkRow(
                title_text=f"📂 {title}{meta_suffix}",
                url_text=short_url,
                show_top_border=(idx > 0),
            )
            row_widget.setToolTip(url)
            row_widget.clicked.connect(lambda u=url: self.load_recent_link(u))
            self.recent_rows_layout.addWidget(row_widget)

    def show_recent_links_menu(self):
        if not self.is_logged_in():
            self.prompt_login_required("view recent links")
            return

        menu = QMenu(self)
        if not self.recent_links:
            empty_act = menu.addAction("No recent links saved")
            empty_act.setEnabled(False)
        else:
            for item in self.recent_links:
                title = (item.get("title") or "Dropbox Folder").replace("&", "&&")
                url = item.get("url", "")
                cnt = item.get("item_count")
                cnt_txt = f"  ({cnt} items)" if cnt else ""
                date_txt = f"  •  {item.get('date_str', '')}" if item.get("date_str") else ""
                short_url = (url[:60] + ("..." if len(url) > 60 else "")).replace("&", "&&")
                action_text = f"📁 {title}{cnt_txt}{date_txt}\n    {short_url}"
                act = menu.addAction(action_text)
                act.triggered.connect(lambda _, u=url: self.load_recent_link(u))

            menu.addSeparator()
            clear_act = menu.addAction("🗑  Clear Recent Links History")
            clear_act.triggered.connect(self.clear_recent_links)

        if hasattr(self, "btn_recent_links") and self.btn_recent_links is not None:
            menu.exec(self.btn_recent_links.mapToGlobal(self.btn_recent_links.rect().bottomLeft()))
        else:
            menu.exec(QCursor.pos())

    def load_recent_link(self, url: str):
        if not self.is_logged_in():
            self.prompt_login_required("load this link")
            return
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            self.auto_scan_timer.stop()
        item = next((it for it in self.recent_links if it.get("url") == url), None)
        if item and item.get("title"):
            self.current_root_name = item.get("title")
        self.url_input.blockSignals(True)
        self.url_input.setText(url)
        self.url_input.blockSignals(False)
        self.start_scan()

    def clear_recent_links(self):
        self.recent_links = []
        self.save_settings()
        self.update_recent_links_ui()
        self.add_log("Recent links history cleared.")

    def prompt_login_required(self, action_desc: str = "use this feature"):
        confirmed = _mw.ModernMessageBox.question(
            self,
            "Dropbox Login Required",
            f"You must sign into your Dropbox account to {action_desc}.\n\n"
            "All folder scanning, selection, and download features are disabled until you sign in.\n\n"
            "Would you like to log in with Dropbox now?",
            yes_text="Log In with Dropbox",
            no_text="Cancel",
        )
        if confirmed:
            self.login_with_dropbox()

    def toggle_log_visibility(self):
        if not self.log_box.isHidden():
            self.log_box.setVisible(False)
            self.btn_toggle_log.setText("Show Log")
        else:
            self.log_box.setVisible(True)
            self.btn_toggle_log.setText("Hide Log")

    def show_empty_tree_placeholder(self):
        self._updating_tree = True
        self.tree_widget.clear()
        if not self.is_logged_in():
            placeholder = QTreeWidgetItem(
                self.tree_widget,
                ["🔒 Please log in to Dropbox to inspect and download folders", "—", "—"],
            )
        else:
            placeholder = QTreeWidgetItem(
                self.tree_widget,
                ["Paste a Dropbox link in Step 1 and click 'Load Folders →'", "—", "—"],
            )
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder.setForeground(0, QColor("#64748b"))
        placeholder.setForeground(1, QColor("#64748b"))
        placeholder.setForeground(2, QColor("#64748b"))
        self._updating_tree = False

    def on_url_text_changed(self, text: str):
        self.update_download_button_state()
        text = text.strip()
        if "dropbox.com" in text and ("http://" in text or "https://" in text):
            self.auto_scan_timer.start(700)

    def auto_scan_if_valid(self):
        url = self.url_input.text().strip()
        if "dropbox.com" in url and ("http://" in url or "https://" in url) and self.is_logged_in():
            self.start_scan()

    def paste_url(self):
        if not self.is_logged_in():
            self.prompt_login_required("paste and inspect shared links")
            return
        if hasattr(self, "auto_scan_timer") and self.auto_scan_timer is not None:
            self.auto_scan_timer.stop()
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.blockSignals(True)
            self.url_input.setText(text)
            self.url_input.blockSignals(False)
            self.start_scan()

    def clear_url_and_tree(self):
        self.url_input.clear()
        self.link_password = ""
        self.current_root_name = ""
        self._tree_items_data = []
        self._scanned_url = ""
        self.step2_folder_label.setText("📂 Shared Folder")
        self.btn_step_2.setText("2. Select Files")
        self.hide_transfer_notice()
        self.show_empty_tree_placeholder()
        self.rebuild_queue_from_selection()
        if self.is_logged_in():
            self.set_selection_summary("(Paste link in Step 1 to inspect folders)", "neutral")
        else:
            self.set_selection_summary("(Sign in required)", "neutral")
        self.update_download_button_state()
        self.go_to_step(0)

    def browse_destination(self):
        folder = _mw.QFileDialog.getExistingDirectory(
            self,
            "Select Local Download Destination",
            self.destination_input.text().strip() or str(Path.home()),
        )
        if folder:
            self.destination_input.setText(folder)
            self.save_settings()
            if not self._is_running:
                self.rebuild_queue_from_selection()

    def open_destination_folder(self):
        dest = self.destination_input.text().strip()
        if not dest:
            _mw.ModernMessageBox.information(self, "Notice", "Download destination folder does not exist yet.")
            return

        target_path = Path(dest)
        if target_path.exists():
            os.startfile(str(target_path))
        else:
            _mw.ModernMessageBox.information(self, "Notice", "Download destination folder does not exist yet.")

