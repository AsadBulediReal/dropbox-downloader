import hashlib
import tempfile
import unittest
from pathlib import Path

from src.utils import (
    build_tree_hierarchy,
    check_single_folder_destination_match,
    compute_dropbox_content_hash,
    create_dropbox_client,
    extract_folder_name_from_url,
    format_bytes,
    get_file_type_and_icon,
    is_path_selected,
    natural_sort_key,
    natural_sort_path_key,
    parse_friendly_error,
    resolve_download_root,
    safe_local_path,
    sanitize_filename,
    strip_folder_prefix,
)


class TestUtils(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0.0 B")
        self.assertEqual(format_bytes(512), "512.0 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024 * 2.5), "2.5 MB")
        self.assertEqual(format_bytes("invalid"), "0 B")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename('my:folder*name?.txt'), "my_folder_name_.txt")
        self.assertEqual(sanitize_filename("   ...   "), "DropboxDownload")

    def test_extract_folder_name_from_url(self):
        self.assertEqual(
            extract_folder_name_from_url("https://www.dropbox.com/scl/fo/abc123xyz/ProjectFiles?rlkey=123"),
            "",
        )
        self.assertEqual(
            extract_folder_name_from_url("https://www.dropbox.com/sh/123/My%20Photos"),
            "My Photos",
        )

    def test_parse_friendly_error_categories(self):
        self.assertEqual(parse_friendly_error("shared_link_not_found")[0], "Link Not Working")
        self.assertEqual(parse_friendly_error("requires_password")[0], "Password Required")
        self.assertEqual(parse_friendly_error("shared_link_access_denied")[0], "Access Restricted")
        self.assertEqual(parse_friendly_error("Please enter a valid Dropbox shared URL")[0], "Invalid Dropbox Link")
        self.assertEqual(parse_friendly_error("expired_access_token")[0], "Sign-In Required")
        self.assertEqual(parse_friendly_error("ConnectionError: max retries exceeded")[0], "Network Connection Error")
        self.assertEqual(parse_friendly_error("Read timed out")[0], "Connection Timed Out")
        self.assertEqual(parse_friendly_error("SSLError: certificate verify failed")[0], "Secure Connection Failed")
        self.assertEqual(parse_friendly_error("HTTP 429 too_many_requests")[0], "Dropbox Busy")
        self.assertEqual(parse_friendly_error("WinError 5: Access is denied")[0], "Permission Denied")
        self.assertEqual(parse_friendly_error("No space left on device")[0], "Disk Full")
        self.assertEqual(parse_friendly_error("size mismatch: expected 10, got 5")[0], "Download Interrupted")

    def test_safe_local_path_sanitizes_and_prevents_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            resolved = safe_local_path(root, "../Sub:Folder/file*name?.txt")
            self.assertEqual(resolved, (root / "Sub_Folder" / "file_name_.txt").resolve())
            self.assertTrue(str(resolved).startswith(str(root.resolve())))

    def test_single_folder_destination_matching_and_prefix_strip(self):
        files = [
            {"rel_path": "Photos/2026/img1.jpg"},
            {"rel_path": "Photos/2026/img2.jpg"},
            {"rel_path": "Photos/cover.jpg"},
        ]
        matched, prefix = check_single_folder_destination_match(files, Path("D:/Downloads/Photos"))
        self.assertEqual(matched, "Photos")
        self.assertEqual(prefix, "Photos")
        self.assertEqual(strip_folder_prefix("Photos/2026/img1.jpg", prefix), "2026/img1.jpg")
        self.assertEqual(strip_folder_prefix("Photos/cover.jpg", prefix), "cover.jpg")

        # Multiple top-level folders should NOT strip
        mixed_files = [
            {"rel_path": "Photos/img1.jpg"},
            {"rel_path": "Videos/clip1.mp4"},
        ]
        self.assertEqual(check_single_folder_destination_match(mixed_files, Path("D:/Downloads/Photos")), (None, None))

        # Root-level file mixed in should NOT strip
        root_mixed = [
            {"rel_path": "Photos/img1.jpg"},
            {"rel_path": "readme.txt"},
        ]
        self.assertEqual(check_single_folder_destination_match(root_mixed, Path("D:/Downloads/Photos")), (None, None))

    def test_resolve_download_root(self):
        dest, is_same = resolve_download_root(Path("C:/Users/Test/Photos"), "Photos")
        self.assertEqual(dest, Path("C:/Users/Test/Photos"))
        self.assertTrue(is_same)

    def test_natural_sort_and_file_icons(self):
        items = [{"rel_path": "ep10.mp4"}, {"rel_path": "ep2.mp4"}, {"rel_path": "ep1.mp4"}]
        items.sort(key=natural_sort_path_key)
        self.assertEqual([i["rel_path"] for i in items], ["ep1.mp4", "ep2.mp4", "ep10.mp4"])
        self.assertEqual(natural_sort_key("Track 12"), ["track ", 12, ""])
        self.assertEqual(get_file_type_and_icon("video.mp4")[0], "MP4 Video")

    def test_compute_dropbox_content_hash_multiblock_and_callbacks(self):
        block1 = b"A" * (4 * 1024 * 1024)
        block2 = b"B" * 512_000
        payload = block1 + block2
        expected = hashlib.sha256(
            hashlib.sha256(block1).digest() + hashlib.sha256(block2).digest()
        ).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "multi.bin"
            fpath.write_bytes(payload)

            two_arg_calls: list[tuple[int, int]] = []
            calc = compute_dropbox_content_hash(
                fpath,
                progress_cb=lambda pct, chunk_len: two_arg_calls.append((pct, chunk_len)),
            )
            self.assertEqual(calc, expected)
            self.assertEqual(len(two_arg_calls), 2)
            self.assertEqual(two_arg_calls[-1][0], 100)
            self.assertEqual(sum(c[1] for c in two_arg_calls), len(payload))

            # 1-arg callback backward compatibility
            one_arg_calls: list[int] = []
            calc_1 = compute_dropbox_content_hash(fpath, progress_cb=lambda pct: one_arg_calls.append(pct))
            self.assertEqual(calc_1, expected)
            self.assertEqual(one_arg_calls[-1], 100)

            # Stop check aborts early returning empty string
            aborted = compute_dropbox_content_hash(fpath, stop_check_func=lambda: True)
            self.assertEqual(aborted, "")

    def test_build_tree_hierarchy_and_selection(self):
        entries = [
            {"name": "Docs", "path": "Docs", "is_dir": True, "size": 0},
            {"name": "a.pdf", "path": "Docs/a.pdf", "is_dir": False, "size": 100, "content_hash": "h1"},
            {"name": "b.pdf", "path": "Docs/Sub/b.pdf", "is_dir": False, "size": 250, "content_hash": "h2"},
            {"name": "root.txt", "path": "root.txt", "is_dir": False, "size": 50, "content_hash": "h3"},
        ]
        tree = build_tree_hierarchy(entries, "SharedRoot")
        self.assertEqual(tree["total_size"], 400)
        self.assertEqual(tree["file_count"], 3)
        self.assertEqual(tree["folder_count"], 1)
        self.assertEqual(tree["children"]["Docs"]["total_size"], 350)
        self.assertEqual(tree["children"]["Docs"]["file_count"], 2)

        # Selection filtering
        self.assertTrue(is_path_selected("Docs/a.pdf", set(), set(), {"Docs"}, set(), has_tree_filter=True))
        self.assertFalse(is_path_selected("Docs/a.pdf", set(), {"Docs/a.pdf"}, {"Docs"}, set(), has_tree_filter=True))
        self.assertFalse(is_path_selected("root.txt", set(), set(), {"Docs"}, set(), has_tree_filter=True))
        self.assertTrue(is_path_selected("root.txt", set(), set(), set(), set(), has_tree_filter=False))

    def test_create_dropbox_client_validation(self):
        with self.assertRaises(ValueError):
            create_dropbox_client(access_token="", refresh_token="", app_key="")

        dbx_tok = create_dropbox_client(access_token="sample_token", timeout=25.0)
        self.assertEqual(dbx_tok._timeout, 25.0)

        dbx_pkce = create_dropbox_client(refresh_token="ref_tok", app_key="app_k", timeout=40.0)
        self.assertEqual(dbx_pkce._timeout, 40.0)


if __name__ == "__main__":
    unittest.main()

