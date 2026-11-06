from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)


class _TreeInteractionsMixin:
    def _get_tree_items_between(self, item1: QTreeWidgetItem, item2: QTreeWidgetItem) -> list[QTreeWidgetItem]:
        """Return all visible tree items between item1 and item2 (inclusive) in top-to-bottom order."""
        all_visible: list[QTreeWidgetItem] = []
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            parent = item.parent()
            visible = not item.isHidden()
            while visible and parent:
                if not parent.isExpanded():
                    visible = False
                    break
                parent = parent.parent()
            if visible:
                all_visible.append(item)
            it += 1

        try:
            idx1 = all_visible.index(item1)
            idx2 = all_visible.index(item2)
        except ValueError:
            return [item2]

        start = min(idx1, idx2)
        end = max(idx1, idx2)
        return all_visible[start : end + 1]

    def set_items_checked(self, items: list[QTreeWidgetItem], state: Qt.CheckState):
        """Batch set check states on a list of items and propagate down/up properly."""
        if not items:
            return
        self._updating_tree = True
        try:
            for it in items:
                it.setCheckState(0, state)
                if bool(it.data(1, Qt.ItemDataRole.UserRole)):
                    self._propagate_check_down(it, state)
            for it in items:
                self._update_ancestors(it)
        finally:
            self._updating_tree = False
        self.update_selection_summary()

    def on_tree_shift_range_selected(self, anchor_item: QTreeWidgetItem, target_item: QTreeWidgetItem, is_checkbox: bool):
        """Handle Shift+Click range selection and update check states & row highlights."""
        items_range = self._get_tree_items_between(anchor_item, target_item)

        if is_checkbox:
            target_state = (
                Qt.CheckState.Unchecked
                if target_item.checkState(0) == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
        else:
            if anchor_item.checkState(0) == Qt.CheckState.Checked:
                target_state = Qt.CheckState.Checked
            else:
                target_state = (
                    Qt.CheckState.Checked
                    if target_item.checkState(0) == Qt.CheckState.Unchecked
                    else Qt.CheckState.Unchecked
                )

        self.tree_widget.clearSelection()
        for it in items_range:
            it.setSelected(True)
        self.tree_widget.setCurrentItem(target_item)

        self.set_items_checked(items_range, target_state)

    def on_tree_space_pressed(self):
        """Toggle check states for all currently selected items in the tree view."""
        selected = self.tree_widget.selectedItems()
        if not selected:
            curr = self.tree_widget.currentItem()
            if curr:
                selected = [curr]
        if not selected:
            return

        has_unchecked = any(it.checkState(0) != Qt.CheckState.Checked for it in selected)
        target_state = Qt.CheckState.Checked if has_unchecked else Qt.CheckState.Unchecked
        self.set_items_checked(selected, target_state)

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            return
        self.tree_widget._anchor_item = item
        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        if is_dir and item.childCount() > 0:
            pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
            rect = self.tree_widget.visualItemRect(item)
            if column != 0 or pos.x() > (rect.x() + 24):
                item.setExpanded(not item.isExpanded())
        elif not is_dir:
            pos = self.tree_widget.viewport().mapFromGlobal(QCursor.pos())
            rect = self.tree_widget.visualItemRect(item)
            if column != 0 or pos.x() > (rect.x() + 24):
                current_state = item.checkState(0)
                new_state = (
                    Qt.CheckState.Unchecked
                    if current_state == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
                item.setCheckState(0, new_state)

    def show_tree_context_menu(self, point):
        item = self.tree_widget.itemAt(point)
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        menu = QMenu(self)
        selected_items = self.tree_widget.selectedItems()
        is_multi = len(selected_items) > 1 and item in selected_items

        act_check_sel = None
        act_uncheck_sel = None
        act_only_sel = None

        if is_multi:
            act_check_sel = menu.addAction(f"☑ Check Selected ({len(selected_items)} items)")
            act_uncheck_sel = menu.addAction(f"☐ Deselect Selected ({len(selected_items)} items)")
            act_only_sel = menu.addAction(f"🎯 Select Only Selected ({len(selected_items)} items)")
            menu.addSeparator()

        is_dir = bool(item.data(1, Qt.ItemDataRole.UserRole))
        raw_name = item.data(3, Qt.ItemDataRole.UserRole) or item.text(0)

        if not is_dir:
            act_only = menu.addAction(f"🎯 Select Only '{raw_name}'")
            is_checked = item.checkState(0) == Qt.CheckState.Checked
            act_toggle = menu.addAction(f"☐ Deselect '{raw_name}'" if is_checked else f"☑ Select '{raw_name}'")
            menu.addSeparator()
            act_select_all = menu.addAction("☑ Select All")
            act_deselect_all = menu.addAction("☐ Deselect All")

            action = menu.exec(self.tree_widget.viewport().mapToGlobal(point))
            if is_multi and action == act_check_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif is_multi and action == act_uncheck_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Unchecked)
            elif is_multi and action == act_only_sel:
                self.deselect_all_items()
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif action == act_only:
                self.deselect_all_items()
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_toggle:
                new_state = Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked
                item.setCheckState(0, new_state)
            elif action == act_select_all:
                self.select_all_items()
            elif action == act_deselect_all:
                self.deselect_all_items()
        else:
            act_only_folder = menu.addAction(f"🎯 Select Only '{raw_name}'")
            act_select_folder = menu.addAction(f"☑ Select All in '{raw_name}'")
            act_deselect_folder = menu.addAction(f"☐ Deselect All in '{raw_name}'")
            menu.addSeparator()
            act_expand = menu.addAction("📂 Expand Folder")
            act_collapse = menu.addAction("📁 Collapse Folder")
            menu.addSeparator()
            act_select_all = menu.addAction("☑ Select All")
            act_deselect_all = menu.addAction("☐ Deselect All")

            action = menu.exec(self.tree_widget.viewport().mapToGlobal(point))
            if is_multi and action == act_check_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif is_multi and action == act_uncheck_sel:
                self.set_items_checked(selected_items, Qt.CheckState.Unchecked)
            elif is_multi and action == act_only_sel:
                self.deselect_all_items()
                self.set_items_checked(selected_items, Qt.CheckState.Checked)
            elif action == act_only_folder:
                self.deselect_all_items()
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_select_folder:
                item.setCheckState(0, Qt.CheckState.Checked)
            elif action == act_deselect_folder:
                item.setCheckState(0, Qt.CheckState.Unchecked)
            elif action == act_expand:
                item.setExpanded(True)
            elif action == act_collapse:
                item.setExpanded(False)
            elif action == act_select_all:
                self.select_all_items()
            elif action == act_deselect_all:
                self.deselect_all_items()

