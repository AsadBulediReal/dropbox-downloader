import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

import src.main_window as main_window_mod
from src.main_window import MainWindow
from src.utils import build_tree_hierarchy


class TestMainWindowGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        ini_file = str(Path(self._tmpdir.name) / "test_settings.ini")
        self._settings_patcher = patch.object(
            main_window_mod,
            "QSettings",
            side_effect=lambda *a, **kw: QSettings(ini_file, QSettings.Format.IniFormat),
        )
        self._settings_patcher.start()
        self.win = MainWindow()

    def tearDown(self):
        self.win.close()
        self._settings_patcher.stop()
        self._tmpdir.cleanup()

    def test_login_gated_workspace_unlocks_when_authenticated(self):
        self.assertFalse(self.win.is_logged_in())
        self.assertFalse(self.win.url_input.isEnabled())
        self.assertFalse(self.win.btn_scan_url.isEnabled())

        self.win.current_access_token = "test_access_token"
        self.win.update_feature_enabled_state()
        self.assertTrue(self.win.is_logged_in())
        self.assertTrue(self.win.url_input.isEnabled())
        self.assertTrue(self.win.btn_scan_url.isEnabled())

    def test_tree_controls_select_deselect_expand_collapse(self):
        self.win.current_access_token = "test_access_token"
        self.win.update_feature_enabled_state()

        entries = [
            {"name": "Photos", "path": "Photos", "is_dir": True, "size": 0},
            {"name": "1.jpg", "path": "Photos/1.jpg", "is_dir": False, "size": 1024, "content_hash": "a" * 64},
            {"name": "2.jpg", "path": "Photos/2.jpg", "is_dir": False, "size": 2048, "content_hash": "b" * 64},
            {"name": "notes.txt", "path": "notes.txt", "is_dir": False, "size": 512, "content_hash": "c" * 64},
        ]
        tree = build_tree_hierarchy(entries, "SharedRoot")
        self.win.on_scan_finished(tree, "SharedRoot", entries)

        self.assertTrue(self.win.btn_select_all.isEnabled())
        self.assertTrue(self.win.btn_deselect_all.isEnabled())
        self.assertTrue(self.win.btn_expand_all.isEnabled())
        self.assertTrue(self.win.btn_collapse_all.isEnabled())

        # Deselect all -> unchecked
        self.win.deselect_all_items()
        top_item = self.win.tree_widget.topLevelItem(0)
        self.assertIsNotNone(top_item)
        self.assertEqual(top_item.checkState(0), Qt.CheckState.Unchecked)

        # Select all -> checked
        self.win.select_all_items()
        self.assertEqual(top_item.checkState(0), Qt.CheckState.Checked)

        # Expand all & collapse all remain responsive
        self.win.btn_expand_all.click()
        self.assertTrue(top_item.isExpanded())
        self.win.btn_collapse_all.click()
        self.assertFalse(top_item.isExpanded())

    def test_pause_resume_logs_single_clean_message_and_log_filter_works(self):
        self.win.clear_log()
        self.win.on_download_paused_changed(True)
        self.win.on_download_paused_changed(False)

        self.assertEqual(len(self.win.all_log_lines), 2)
        self.assertTrue(self.win.all_log_lines[0].endswith("⏸ Download paused."))
        self.assertNotIn("by user", self.win.all_log_lines[0])
        self.assertTrue(self.win.all_log_lines[1].endswith("▶ Download resumed."))

        # Filter logs
        self.win.filter_logs("paused")
        self.assertIn("⏸ Download paused.", self.win.log_box.toPlainText())
        self.assertNotIn("▶ Download resumed.", self.win.log_box.toPlainText())

        self.win.filter_logs("")
        self.assertIn("▶ Download resumed.", self.win.log_box.toPlainText())


if __name__ == "__main__":
    unittest.main()
