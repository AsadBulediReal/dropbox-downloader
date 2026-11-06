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
        self.assertFalse(hasattr(self.win, "btn_header_login"))
        self.assertFalse(hasattr(self.win, "auth_badge"))
        self.assertFalse(hasattr(self.win, "status_badge"))
        self.assertFalse(self.win.login_banner.isHidden())

        self.win.current_access_token = "test_access_token"
        self.win.update_account_ui()
        self.assertTrue(self.win.is_logged_in())
        self.assertTrue(self.win.login_banner.isHidden())
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

    def test_guided_wizard_steps_and_auto_advance_on_scan(self):
        self.assertEqual(self.win.current_step, 0)
        self.assertEqual(self.win.wizard_stack.currentIndex(), 0)

        self.win.current_access_token = "test_access_token"
        self.win.update_feature_enabled_state()
        self.win.url_input.setText("https://www.dropbox.com/scl/fo/abc/SharedRoot")

        entries = [
            {"name": "Photos", "path": "Photos", "is_dir": True, "size": 0},
            {"name": "1.jpg", "path": "Photos/1.jpg", "is_dir": False, "size": 1024, "content_hash": "a" * 64},
        ]
        tree = build_tree_hierarchy(entries, "SharedRoot")
        self.win.on_scan_finished(tree, "SharedRoot", entries)

        # Auto-advances to Step 2 (Select Files)
        self.assertEqual(self.win.current_step, 1)
        self.assertEqual(self.win.wizard_stack.currentIndex(), 1)
        self.assertIn("SharedRoot", self.win.step2_folder_label.text())

        # Step navigation buttons switch cleanly
        self.win.btn_step_3.click()
        self.assertEqual(self.win.current_step, 2)
        self.win.btn_step_1.click()
        self.assertEqual(self.win.current_step, 0)

    def test_recent_links_chips_and_rows_in_step1(self):
        self.win.current_access_token = "test_access_token"
        self.win.update_feature_enabled_state()

        self.win.add_recent_link("https://www.dropbox.com/scl/fo/111/Summer_Shoot", title="Summer_Shoot", item_count=12)
        self.win.add_recent_link("https://www.dropbox.com/scl/fo/222/Brand_Kit", title="Brand_Kit", item_count=5)

        self.assertEqual(len(self.win.recent_links), 2)
        self.assertFalse(self.win.recent_chips_container.isHidden())
        self.assertGreaterEqual(self.win.recent_rows_layout.count(), 2)

        self.win.clear_recent_links()
        self.assertEqual(len(self.win.recent_links), 0)
        self.assertTrue(self.win.recent_chips_container.isHidden())

    def test_queue_filter_tabs_and_downloaded_remaining_counters(self):
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

        self.assertEqual(self.win.btn_qtab_all.text(), "All Selected (3)")
        self.assertEqual(self.win.btn_qtab_done.text(), "✓ Downloaded (0)")
        self.assertEqual(self.win.btn_qtab_rem.text(), "⏳ Remaining / Up Next (3)")
        self.assertEqual(self.win.val_remaining_files.text(), "3 files left")

        # Simulate active download & completion logs
        self.win.add_log("GET   [Photos] 1.jpg (1.0 KB) [Attempt 1/3]")
        self.win.update_file_progress(55)
        k1 = self.win._make_queue_key("Photos", "1.jpg")
        self.assertIn("55%", self.win._queue_tree_items[k1].text(2))

        self.win.add_log("DONE  [Photos] 1.jpg")
        self.win.add_log("SKIP  [/ (Root)] notes.txt (already exists)")

        self.assertEqual(self.win.btn_qtab_done.text(), "✓ Downloaded (2)")
        self.assertEqual(self.win.btn_qtab_rem.text(), "⏳ Remaining / Up Next (1)")
        self.assertEqual(self.win.val_files.text(), "2 / 3 files")
        self.assertEqual(self.win.val_remaining_files.text(), "1 file left")

        # Filter: Downloaded only
        self.win.btn_qtab_done.click()
        k2 = self.win._make_queue_key("Photos", "2.jpg")
        self.assertFalse(self.win._queue_tree_items[k1].isHidden())
        self.assertTrue(self.win._queue_tree_items[k2].isHidden())

        # Filter: Remaining only
        self.win.btn_qtab_rem.click()
        self.assertTrue(self.win._queue_tree_items[k1].isHidden())
        self.assertFalse(self.win._queue_tree_items[k2].isHidden())

        # Filter: All
        self.win.btn_qtab_all.click()
        self.assertFalse(self.win._queue_tree_items[k1].isHidden())
        self.assertFalse(self.win._queue_tree_items[k2].isHidden())

    def test_corner_settings_drawer_and_theme_toggle(self):
        self.assertTrue(self.win.settings_overlay.isHidden())
        self.win.btn_settings.click()
        self.assertFalse(self.win.settings_overlay.isHidden())

        self.assertEqual(self.win.theme_mode, "light")
        self.win.btn_theme_toggle.click()
        self.assertEqual(self.win.theme_mode, "dark")
        self.win.btn_theme_toggle.click()
        self.assertEqual(self.win.theme_mode, "light")

        self.win.btn_close_settings.click()
        self.assertTrue(self.win.settings_overlay.isHidden())

    def test_ad_banner_rotation_and_url_safety(self):
        from src.ads import sanitize_ad_entries

        cleaned = sanitize_ad_entries(
            [
                {"title": "Bad Ad", "description": "XSS", "url": "javascript:alert(1)"},
                {"badge": "Partner", "title": "Cloud Pro", "description": "Fast backup", "cta": "Try →", "url": "https://example.com/deal"},
            ]
        )
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["title"], "Cloud Pro")

        first_title = self.win.ad_banner.current_ad["title"]
        self.win.ad_banner.next_ad()
        self.assertNotEqual(self.win.ad_banner.current_ad["title"], first_title)

        with patch("src.ads.webbrowser.open") as mock_open:
            self.win.ad_banner.cta_button.click()
            mock_open.assert_called_once()

    def test_ui_layout_widths_ampersands_and_recent_row_cleanup(self):
        # Ampersands escaped for Qt buttons so "&" is displayed rather than stripped
        self.assertEqual(self.win.btn_step_1.text(), "1. Link && Recent")

        self.win.resize(980, 780)
        self.win.show()
        self.app.processEvents()

        # Centered containers should expand toward their max-width rather than 1/3 width
        self.assertGreaterEqual(self.win.target_card.width(), 700)
        self.assertGreaterEqual(self.win.ad_banner.width(), 800)

        # Updating recent links repeatedly must immediately unparent old row widgets
        self.win.current_access_token = "test_access_token"
        self.win.update_account_ui()
        self.win.add_recent_link("https://www.dropbox.com/scl/fo/1/Photos_&_Videos", title="Photos & Videos", item_count=4)
        self.win.add_recent_link("https://www.dropbox.com/scl/fo/2/Client_Files", title="Client_Files", item_count=9)
        self.app.processEvents()
        self.assertEqual(self.win.recent_rows_layout.count(), 2)
        row_children = self.win.recent_rows_container.findChildren(main_window_mod._RecentLinkRow)
        self.assertEqual(len(row_children), 2)
        self.assertTrue(all(w.isVisible() for w in row_children))


if __name__ == "__main__":
    unittest.main()
