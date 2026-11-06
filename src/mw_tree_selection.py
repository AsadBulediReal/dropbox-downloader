from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from .utils import (
    format_bytes,
    strip_folder_prefix,
    check_single_folder_destination_match,
    natural_sort_path_key,
    is_path_selected,
)


class _TreeSelectionMixin:
    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != 0 or self._updating_tree:
            return

        self._updating_tree = True
        try:
            state = item.checkState(0)
            if state != Qt.CheckState.PartiallyChecked:
                self._propagate_check_down(item, state)

            self._update_ancestors(item)
        finally:
            self._updating_tree = False

        self.update_selection_summary()

    def _propagate_check_down(self, item: QTreeWidgetItem, state: Qt.CheckState):
        for i in range(item.childCount()):
            child = item.child(i)
            if child is not None:
                child.setCheckState(0, state)
                self._propagate_check_down(child, state)

    def _update_ancestors(self, item: QTreeWidgetItem):
        parent = item.parent()
        if not parent:
            return

        checked_count = 0
        partial_count = 0
        total = parent.childCount()

        for i in range(total):
            child = parent.child(i)
            if child is None:
                continue
            c_state = child.checkState(0)
            if c_state == Qt.CheckState.Checked:
                checked_count += 1
            elif c_state == Qt.CheckState.PartiallyChecked:
                partial_count += 1

        if checked_count == total:
            parent.setCheckState(0, Qt.CheckState.Checked)
        elif checked_count == 0 and partial_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        self._update_ancestors(parent)

    def select_all_items(self):
        self._updating_tree = True
        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            if top is not None:
                top.setCheckState(0, Qt.CheckState.Checked)
                self._propagate_check_down(top, Qt.CheckState.Checked)
        self._updating_tree = False
        self.update_selection_summary()

    def deselect_all_items(self):
        self._updating_tree = True
        for i in range(self.tree_widget.topLevelItemCount()):
            top = self.tree_widget.topLevelItem(i)
            if top is not None:
                top.setCheckState(0, Qt.CheckState.Unchecked)
                self._propagate_check_down(top, Qt.CheckState.Unchecked)
        self._updating_tree = False
        self.update_selection_summary()

    def update_selection_summary(self):
        total_files = 0
        selected_files = 0
        total_folders = 0
        selected_folders = 0
        selected_bytes = 0

        def count_recursive(item: QTreeWidgetItem | None):
            nonlocal total_files, selected_files, total_folders, selected_folders, selected_bytes
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
            state = item.checkState(0)
            size = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)

            if is_dir:
                total_folders += 1
                if state in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                    selected_folders += 1
            else:
                total_files += 1
                if state == Qt.CheckState.Checked:
                    selected_files += 1
                    selected_bytes += size

            for i in range(item.childCount()):
                count_recursive(item.child(i))

        for i in range(self.tree_widget.topLevelItemCount()):
            count_recursive(self.tree_widget.topLevelItem(i))

        if total_files == 0 and total_folders == 0:
            self.set_selection_summary("(No items scanned yet)", "neutral")
            self.btn_step_2.setText("2. Select Files")
        elif total_files == 0:
            folder_str = f"{selected_folders} of {total_folders} folder{'s' if total_folders != 1 else ''} selected"
            self.set_selection_summary(folder_str, "success" if selected_folders > 0 else "neutral")
            self.btn_step_2.setText(f"2. Select Files ({selected_folders})")
        else:
            summary_txt = f"{selected_files} of {total_files} file{'s' if total_files != 1 else ''} selected"
            if selected_bytes > 0:
                summary_txt += f" • {format_bytes(selected_bytes)}"
            self.set_selection_summary(summary_txt, "success" if selected_files > 0 else "neutral")
            self.btn_step_2.setText(f"2. Select Files ({selected_files})")
        self._refresh_wizard_pill_geometry()

        if not self._is_running:
            self.rebuild_queue_from_selection()

        self.update_download_button_state()

    def get_tree_selection_info(self) -> dict[str, Any]:
        selected_files = set()
        deselected_files = set()
        selected_folders = set()
        deselected_folders = set()
        total_files = 0
        total_selected_files = 0
        selected_bytes = 0
        has_tree_items = False

        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            if top_item is not None and top_item.data(0, Qt.ItemDataRole.UserRole) is not None:
                has_tree_items = True
                break

        def traverse(item: QTreeWidgetItem | None, parent_path=""):
            nonlocal total_files, total_selected_files, selected_bytes
            if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                return
            is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
            raw_name = (
                item.data(3, Qt.ItemDataRole.UserRole)
                or item.text(0).replace("📁 ", "").replace("📂 ", "").replace("📄 ", "").strip()
            )
            item_path = item.data(0, Qt.ItemDataRole.UserRole) or ""
            size = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)

            current_path = f"{parent_path}/{raw_name}".strip("/") if parent_path else raw_name
            state = item.checkState(0)

            if is_dir:
                if state == Qt.CheckState.Checked:
                    if item_path:
                        selected_folders.add(item_path)
                    selected_folders.add(current_path)
                elif state == Qt.CheckState.Unchecked:
                    if item_path:
                        deselected_folders.add(item_path)
                    deselected_folders.add(current_path)

                for i in range(item.childCount()):
                    traverse(item.child(i), current_path)
            else:
                total_files += 1
                if state == Qt.CheckState.Checked:
                    total_selected_files += 1
                    selected_bytes += size
                    if item_path:
                        selected_files.add(item_path)
                    selected_files.add(current_path)
                else:
                    if item_path:
                        deselected_files.add(item_path)
                    deselected_files.add(current_path)

        for i in range(self.tree_widget.topLevelItemCount()):
            traverse(self.tree_widget.topLevelItem(i))

        checked_top_folders = []
        checked_top_files = []
        partially_checked_folders = []
        for i in range(self.tree_widget.topLevelItemCount()):
            top_item = self.tree_widget.topLevelItem(i)
            if top_item is None or top_item.data(0, Qt.ItemDataRole.UserRole) is None:
                continue
            is_dir = bool(top_item.data(1, Qt.ItemDataRole.UserRole))
            state = top_item.checkState(0)
            if state == Qt.CheckState.Checked:
                if is_dir:
                    checked_top_folders.append(top_item)
                else:
                    checked_top_files.append(top_item)
            elif state == Qt.CheckState.PartiallyChecked and is_dir:
                partially_checked_folders.append(top_item)

        single_selected_folder = ""
        if len(checked_top_files) == 0:
            if len(checked_top_folders) == 1 and len(partially_checked_folders) == 0:
                f_item = checked_top_folders[0]
                single_selected_folder = (
                    f_item.data(0, Qt.ItemDataRole.UserRole)
                    or f_item.data(3, Qt.ItemDataRole.UserRole)
                    or ""
                )
            elif len(checked_top_folders) == 0 and len(partially_checked_folders) == 1:
                curr = partially_checked_folders[0]
                while curr is not None:
                    c_checked_f = []
                    c_checked_files = []
                    c_partial = []
                    for c_idx in range(curr.childCount()):
                        ch = curr.child(c_idx)
                        if ch is None:
                            continue
                        ch_dir = bool(ch.data(1, Qt.ItemDataRole.UserRole))
                        ch_st = ch.checkState(0)
                        if ch_st == Qt.CheckState.Checked:
                            if ch_dir:
                                c_checked_f.append(ch)
                            else:
                                c_checked_files.append(ch)
                        elif ch_st == Qt.CheckState.PartiallyChecked and ch_dir:
                            c_partial.append(ch)
                    if len(c_checked_files) == 0 and len(c_checked_f) == 1 and len(c_partial) == 0:
                        single_selected_folder = (
                            c_checked_f[0].data(0, Qt.ItemDataRole.UserRole)
                            or c_checked_f[0].data(3, Qt.ItemDataRole.UserRole)
                            or ""
                        )
                        break
                    elif len(c_checked_files) == 0 and len(c_checked_f) == 0 and len(c_partial) == 1:
                        curr = c_partial[0]
                    else:
                        break

        return {
            "selected_files": selected_files,
            "deselected_files": deselected_files,
            "selected_folders": selected_folders,
            "deselected_folders": deselected_folders,
            "single_selected_folder": single_selected_folder,
            "total_files": total_files,
            "selected_file_count": total_selected_files,
            "selected_bytes": selected_bytes,
            "has_tree_items": has_tree_items,
        }

    def _collect_selected_entries_for_queue(self) -> list[dict[str, Any]]:
        info = self.get_tree_selection_info()
        selected_entries: list[dict[str, Any]] = []

        if self._tree_items_data and info.get("has_tree_items"):
            for e in self._tree_items_data:
                if e.get("is_dir"):
                    continue
                rel = e.get("path") or e.get("rel_path") or ""
                if is_path_selected(
                    rel,
                    info["selected_files"],
                    info["deselected_files"],
                    info["selected_folders"],
                    info["deselected_folders"],
                    True,
                ):
                    selected_entries.append(
                        {
                            "name": e.get("name") or Path(rel).name,
                            "rel_path": rel,
                            "size": int(e.get("size", 0) or 0),
                        }
                    )
        elif info.get("has_tree_items"):
            def _collect_checked(item: QTreeWidgetItem | None):
                if item is None or item.data(0, Qt.ItemDataRole.UserRole) is None:
                    return
                is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
                if is_dir:
                    for idx in range(item.childCount()):
                        _collect_checked(item.child(idx))
                elif item.checkState(0) == Qt.CheckState.Checked:
                    rel = item.data(0, Qt.ItemDataRole.UserRole) or ""
                    raw_name = item.data(3, Qt.ItemDataRole.UserRole) or Path(rel).name
                    sz = int(item.data(2, Qt.ItemDataRole.UserRole) or 0)
                    selected_entries.append({"name": raw_name, "rel_path": rel, "size": sz})

            for i in range(self.tree_widget.topLevelItemCount()):
                _collect_checked(self.tree_widget.topLevelItem(i))

        selected_entries.sort(key=lambda d: natural_sort_path_key(d["rel_path"]))

        # Match DownloadWorker's single-folder destination stripping so keys align 100%
        dest_str = self.destination_input.text().strip()
        if dest_str and selected_entries:
            matched_folder, stripped_prefix = check_single_folder_destination_match(
                selected_entries,
                Path(dest_str),
                info.get("single_selected_folder", ""),
            )
            if matched_folder and stripped_prefix:
                for d in selected_entries:
                    d["rel_path"] = strip_folder_prefix(d["rel_path"], stripped_prefix)

        return selected_entries

