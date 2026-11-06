from typing import Any

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QTreeWidgetItem

from . import main_window as _mw
from .utils import (
    format_bytes,
    parse_friendly_error,
    get_file_type_and_icon,
    natural_sort_key,
)


class _ScanTreeMixin:
    def start_scan(self):
        self.cleanup_scan_thread()

        if not self.is_logged_in():
            self.prompt_login_required("inspect folder contents")
            return

        url = self.url_input.text().strip()
        password = (self.link_password or "").strip()

        if not url:
            _mw.ModernMessageBox.warning(
                self, "Missing Link", "Please enter or paste a valid Dropbox shared link to inspect folders."
            )
            self.url_input.setFocus()
            return

        self.btn_scan_url.setEnabled(False)
        self.btn_scan_url.setText("⏳ Loading...")
        self.set_selection_summary("⏳ Scanning folder contents via Dropbox API...", "active")
        self.add_log(f"🔍 Inspecting folder hierarchy for: {url}")

        self.tree_widget.clear()
        loading_item = QTreeWidgetItem(self.tree_widget, ["⏳ Loading folders from Dropbox...", "", ""])
        loading_item.setFlags(loading_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        self.update_feature_enabled_state()
        self.update_download_button_state()

        t = QThread()
        w = _mw.ScanWorker(
            url=url,
            access_token=self.current_access_token,
            refresh_token=self.current_refresh_token,
            app_key=self.get_app_key(),
            password=password,
        )
        w.moveToThread(t)

        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        w.failed.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _on_scan_thread_finished(thread_ref=t):
            if getattr(self, "scan_thread", None) is thread_ref:
                self.scan_thread = None
                self.scan_worker = None
            self._active_workers.pop(thread_ref, None)

        t.finished.connect(_on_scan_thread_finished)

        self.scan_thread = t
        self.scan_worker = w
        self._active_workers[t] = w

        t.started.connect(w.run)
        w.status.connect(self.on_scan_status)
        w.finished.connect(self.on_scan_finished)
        w.failed.connect(self.on_scan_failed)

        t.start()

    def _on_scan_status_impl(self, text: str):
        self.set_selection_summary(f"⏳ {text}", "active")

    def on_scan_finished(self, tree_dict: dict, root_name: str, entries: list):
        self.scan_thread = None
        self.scan_worker = None
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("Load Folders →")

        self.current_root_name = root_name
        self.step2_folder_label.setText(f"📂 {root_name}")
        self._tree_items_data = entries
        url = self.url_input.text().strip()
        self._scanned_url = url
        self.populate_tree_widget(tree_dict, root_name)

        folders_count = sum(1 for e in entries if e.get("is_dir"))
        files_count = sum(1 for e in entries if not e.get("is_dir"))
        total_size = sum(e.get("size", 0) for e in entries if not e.get("is_dir"))

        self.add_log(
            f"✓ Found {len(entries)} items ({folders_count} folder(s), {files_count} file(s), {format_bytes(total_size)})"
        )
        self.update_selection_summary()
        self.add_recent_link(url, title=root_name, item_count=len(entries))
        self.update_feature_enabled_state()
        self.update_download_button_state()

        # Automatically advance to Step 2 (Select Files)
        self.go_to_step(1)

    def on_scan_failed(self, error: str):
        self.scan_thread = None
        self.scan_worker = None
        self.btn_scan_url.setEnabled(True)
        self.btn_scan_url.setText("Load Folders →")

        title, friendly_msg = parse_friendly_error(error)
        self.show_empty_tree_placeholder()
        self.set_selection_summary(f"⚠️ {title}", "error")
        self.add_log(f"⚠️ {title}: {friendly_msg.splitlines()[0]}")
        self.update_feature_enabled_state()
        self.update_download_button_state()

        if "password" in error.lower() or "access_denied" in error.lower():
            pwd, ok = _mw.ModernInputDialog.get_text(
                self,
                title="Password Protected Link",
                heading="Dropbox Link Password Required",
                message=(
                    "This Dropbox shared folder is protected with a password.\n\n"
                    "Please enter the password to inspect its contents:"
                ),
                placeholder="Enter folder link password...",
                is_password=True,
                confirm_text="Unlock & Load",
            )
            if ok and pwd:
                self.link_password = pwd.strip()
                self.start_scan()
                return
        else:
            _mw.ModernMessageBox.warning(self, title, friendly_msg)

    def populate_tree_widget(self, tree_dict: dict, root_name: str):
        self._updating_tree = True
        self.tree_widget.setUpdatesEnabled(False)
        try:
            self.tree_widget.clear()

            def add_item_recursive(parent_item: QTreeWidgetItem | None, node_data: dict[str, Any]):
                name = node_data["name"]
                is_dir = node_data["is_dir"]
                size: int = int(node_data.get("size") or 0)
                total_size: int = int(node_data.get("total_size") or size)

                if is_dir:
                    icon_str = "📁 "
                    file_cnt = int(node_data.get("file_count") or 0)
                    folder_cnt = len([c for c in node_data.get("children", {}).values() if c.get("is_dir")])
                    if file_cnt > 0 and folder_cnt > 0:
                        type_str = f"Folder ({file_cnt} {'file' if file_cnt == 1 else 'files'}, {folder_cnt} {'subfolder' if folder_cnt == 1 else 'subfolders'})"
                    elif file_cnt > 0:
                        type_str = f"Folder ({file_cnt} {'file' if file_cnt == 1 else 'files'})"
                    elif folder_cnt > 0:
                        type_str = f"Folder ({folder_cnt} {'subfolder' if folder_cnt == 1 else 'subfolders'})"
                    else:
                        type_str = "Folder (empty)"
                    size_str = format_bytes(total_size) if total_size > 0 else ""
                else:
                    type_str, icon_str = get_file_type_and_icon(name)
                    size_str = format_bytes(size) if size > 0 else "0 B"

                item = QTreeWidgetItem([f"{icon_str}{name}", type_str, size_str])
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setData(0, Qt.ItemDataRole.UserRole, node_data["path"])
                item.setData(1, Qt.ItemDataRole.UserRole, is_dir)
                item.setData(2, Qt.ItemDataRole.UserRole, size if not is_dir else total_size)
                item.setData(3, Qt.ItemDataRole.UserRole, name)
                item.setToolTip(0, f"{'Folder' if is_dir else 'File'}: {node_data['path'] or name}")

                if parent_item is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                for child_name, child_data in sorted(
                    node_data["children"].items(),
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0])),
                ):
                    add_item_recursive(item, child_data)

            if tree_dict["children"]:
                for child_name, child_data in sorted(
                    tree_dict["children"].items(),
                    key=lambda x: (not x[1]["is_dir"], natural_sort_key(x[0])),
                ):
                    add_item_recursive(None, child_data)
            else:
                single_item = QTreeWidgetItem([f"📁 {root_name}", "Folder", ""])
                single_item.setCheckState(0, Qt.CheckState.Checked)
                single_item.setFlags(single_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                single_item.setData(0, Qt.ItemDataRole.UserRole, root_name)
                single_item.setData(1, Qt.ItemDataRole.UserRole, True)
                single_item.setData(2, Qt.ItemDataRole.UserRole, 0)
                single_item.setData(3, Qt.ItemDataRole.UserRole, root_name)
                single_item.setToolTip(0, f"Folder: {root_name}")
                self.tree_widget.addTopLevelItem(single_item)

            self.tree_widget.collapseAll()
        finally:
            self.tree_widget.setUpdatesEnabled(True)
            self._updating_tree = False
            self.update_selection_summary()
            self.update_feature_enabled_state()

    def on_tree_item_expanded(self, item: QTreeWidgetItem):
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir:
            raw_name = item.data(3, Qt.ItemDataRole.UserRole)
            if raw_name:
                item.setText(0, f"📂 {raw_name}")
            self.on_tree_current_item_changed(item, None)

    def on_tree_item_collapsed(self, item: QTreeWidgetItem):
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir:
            raw_name = item.data(3, Qt.ItemDataRole.UserRole)
            if raw_name:
                item.setText(0, f"📁 {raw_name}")
            self.on_tree_current_item_changed(item, None)

    def on_tree_current_item_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None = None):
        if not current:
            return
        is_dir = bool(current.data(1, Qt.ItemDataRole.UserRole))
        raw_name = (
            current.data(3, Qt.ItemDataRole.UserRole)
            or current.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "")
        )
        if is_dir:
            child_count = current.childCount()
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            size_str = f" • {format_bytes(size)}" if size > 0 else ""
            status = "open — click to collapse" if current.isExpanded() else "closed — click to expand"
            self.tree_hint.setText(f"📁 Folder: {raw_name} ({child_count} items{size_str}) [{status}]")
        else:
            size = int(current.data(2, Qt.ItemDataRole.UserRole) or 0)
            self.tree_hint.setText(f"📄 File: {raw_name} ({format_bytes(size) if size > 0 else '0 B'})")

