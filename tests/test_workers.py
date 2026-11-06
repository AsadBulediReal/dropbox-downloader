import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from dropbox.files import FileMetadata, FolderMetadata

import src.workers as workers_mod
from src.utils import compute_dropbox_content_hash
from src.workers import AuthWorker, DownloadFileItem, DownloadWorker, ScanWorker, SessionVerifyWorker


class FakeResponse:
    def __init__(
        self,
        data: bytes,
        status_code: int = 200,
        headers: dict | None = None,
        fail_after: int | None = None,
        on_chunk=None,
    ):
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
        self.fail_after = fail_after
        self.on_chunk = on_chunk
        self.closed = False

    def iter_content(self, chunk_size: int = 131072):
        offset = 0
        while offset < len(self.data):
            if self.fail_after is not None and offset >= self.fail_after:
                raise ConnectionError("simulated network drop")
            chunk = self.data[offset : offset + chunk_size]
            offset += len(chunk)
            if self.on_chunk:
                self.on_chunk(offset)
            yield chunk

    def close(self):
        self.closed = True


class FakeMetadata:
    def __init__(self, name: str = "SharedRoot", content_hash: str | None = None):
        self.name = name
        self.content_hash = content_hash


class FakeDbx:
    def __init__(self, handler=None):
        self._headers: dict[str, str] = {}
        self.handler = handler
        self.seen_ranges: list[str | None] = []
        self.responses: list[FakeResponse] = []

    def users_get_current_account(self):
        class _Name:
            display_name = "Test User"

        class _Acc:
            name = _Name()
            email = "test@example.com"

        return _Acc()

    def sharing_get_shared_link_metadata(self, **kwargs):
        return FakeMetadata("SharedRoot")

    def sharing_get_shared_link_file(self, **kwargs):
        rng = self._headers.get("Range")
        self.seen_ranges.append(rng)
        meta, resp = self.handler(rng, kwargs, len(self.seen_ranges))
        self.responses.append(resp)
        return meta, resp


def make_payload(size: int, seed: bytes = b"0123456789ABCDEF") -> tuple[bytes, str]:
    data = (seed * ((size // len(seed)) + 1))[:size]
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(data)
        p = Path(tf.name)
    try:
        content_hash = compute_dropbox_content_hash(p)
    finally:
        p.unlink(missing_ok=True)
    return data, content_hash


class TestWorkers(unittest.TestCase):
    def test_auth_and_session_verify_workers(self):
        class FakeFlow:
            def finish(self, code: str):
                class Res:
                    access_token = f"acc_{code}"
                    refresh_token = "ref_123"

                return Res()

        fake_dbx = FakeDbx()
        with patch.object(workers_mod, "create_dropbox_client", return_value=fake_dbx):
            auth_w = AuthWorker(FakeFlow(), "CODE99", "app_key")
            results = []
            auth_w.finished.connect(lambda a, r, n, e: results.append((a, r, n, e)))
            auth_w.run()
            self.assertEqual(results, [("acc_CODE99", "ref_123", "Test User", "test@example.com")])

            sess_w = SessionVerifyWorker("acc", "ref", "app_key")
            verified = []
            sess_w.finished.connect(lambda n, e: verified.append((n, e)))
            sess_w.run()
            self.assertEqual(verified, [("Test User", "test@example.com")])

    def test_scan_worker_parallel_folder_fallback(self):
        class ScanFakeDbx(FakeDbx):
            def files_list_folder(self, path="", shared_link=None, recursive=False, **kw):
                if recursive:
                    raise Exception("recursive unsupported on shared links")

                class Res:
                    has_more = False
                    entries = []

                r = Res()
                if path == "":
                    f_dir = FolderMetadata(name="Photos", id="id:1", path_lower="/photos", path_display="/Photos")
                    f_root = FileMetadata(
                        name="readme.txt",
                        id="id:2",
                        size=42,
                        path_lower="/readme.txt",
                        path_display="/readme.txt",
                        content_hash="a" * 64,
                    )
                    r.entries = [f_dir, f_root]
                elif path == "/Photos":
                    f_img = FileMetadata(
                        name="pic.jpg",
                        id="id:3",
                        size=1000,
                        path_lower="/photos/pic.jpg",
                        path_display="/Photos/pic.jpg",
                        content_hash="b" * 64,
                    )
                    r.entries = [f_img]
                return r

        with patch.object(workers_mod, "create_dropbox_client", return_value=ScanFakeDbx()):
            sw = ScanWorker("https://www.dropbox.com/sh/test/abc", access_token="tok")
            scanned = []
            sw.finished.connect(lambda tree, root, entries: scanned.append((tree, root, entries)))
            sw.run()
            self.assertEqual(len(scanned), 1)
            tree, root_name, entries = scanned[0]
            self.assertEqual(root_name, "SharedRoot")
            self.assertEqual(tree["file_count"], 2)
            self.assertEqual(tree["total_size"], 1042)

    def test_fresh_download_inline_verification_and_speed_isolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            data, content_hash = make_payload(300_000)

            dbx = FakeDbx(lambda rng, kw, idx: (FakeMetadata(content_hash=content_hash), FakeResponse(data, 200)))
            w = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")

            logs: list[str] = []
            file_labels: list[str] = []
            stats_seen: list[dict] = []

            def on_label(txt: str):
                file_labels.append(txt)
                if "🔍 Verifying file (100%)" in txt:
                    w.emit_stats(force=True)

            w.log.connect(logs.append)
            w.file_changed.connect(on_label)
            w.stats_changed.connect(stats_seen.append)

            item = DownloadFileItem("doc.pdf", len(data), "Docs/doc.pdf", "/Docs/doc.pdf", content_hash=content_hash)
            w.files = [item]
            res = w.download_one(dbx, item, dest, total_files=1)

            self.assertIsNone(res)
            self.assertEqual((dest / "Docs" / "doc.pdf").read_bytes(), data)
            self.assertTrue(dbx.responses[0].closed)
            self.assertTrue(any("GET   [Docs] doc.pdf" in l and "[Attempt 1/3]" in l for l in logs))
            self.assertTrue(any("🔍 Verifying file" in fl for fl in file_labels))
            self.assertTrue(any("💾 Finalizing file: doc.pdf" in fl for fl in file_labels))
            self.assertTrue(any("(Verify)" in s["speed"] for s in stats_seen))
            self.assertEqual(w.instant_speed, 0.0)
            self.assertFalse(w.is_currently_downloading)
            self.assertEqual(w.current_downloading_bytes, 0)

    def test_http_range_resume_4kb_rewind_and_stall_preservation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            data, content_hash = make_payload(500_000)

            def handler(rng, kw, call_idx):
                if call_idx == 1:
                    self.assertIsNone(rng)
                    return FakeMetadata(content_hash=content_hash), FakeResponse(data, 200, fail_after=262144)
                if call_idx == 2:
                    # Rewound by 4096 bytes: 262144 - 4096 = 258048
                    self.assertEqual(rng, "bytes=258048-")
                    raise TimeoutError("simulated transient stall")
                # Attempt 3 must keep exact same offset (no cumulative rewind, .tmp not deleted)
                self.assertEqual(rng, "bytes=258048-")
                return (
                    FakeMetadata(content_hash=content_hash),
                    FakeResponse(
                        data[258048:],
                        206,
                        headers={"Content-Range": f"bytes 258048-{len(data)-1}/{len(data)}"},
                    ),
                )

            dbx = FakeDbx(handler)
            w = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")
            logs: list[str] = []
            w.log.connect(logs.append)

            item = DownloadFileItem("clip.mp4", len(data), "clip.mp4", "/clip.mp4", content_hash=content_hash)
            w.files = [item]
            with (
                patch.object(workers_mod, "create_dropbox_client", return_value=dbx),
                patch.object(workers_mod.time, "sleep", return_value=None),
            ):
                res = w.download_one(dbx, item, dest, total_files=1, allow_requeue=False)

            self.assertIsNone(res)
            self.assertEqual((dest / "clip.mp4").read_bytes(), data)
            self.assertTrue(any("🔄 RESUME" in l and "[Attempt 2/3]" in l for l in logs))
            self.assertTrue(any("🔄 RESUME" in l and "[Attempt 3/3]" in l for l in logs))

    def test_pause_over_30s_does_not_trigger_false_stall_timeout_or_duplicate_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            data, content_hash = make_payload(300_000)
            w = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")

            worker_logs: list[str] = []
            paused_events: list[bool] = []
            w.log.connect(worker_logs.append)
            w.paused_signal.connect(paused_events.append)

            fake_clock = [1000.0]

            def on_chunk(offset):
                if offset <= 131072:
                    w.pause()
                    orig_check = w._check_pause

                    def resumed_check():
                        fake_clock[0] += 45.0
                        w.resume()
                        orig_check()

                    w._check_pause = resumed_check

            dbx = FakeDbx(
                lambda rng, kw, idx: (
                    FakeMetadata(content_hash=content_hash),
                    FakeResponse(data, 200, on_chunk=on_chunk),
                )
            )
            item = DownloadFileItem("paused.bin", len(data), "paused.bin", "/paused.bin", content_hash=content_hash)
            w.files = [item]
            with patch.object(workers_mod.time, "time", side_effect=lambda: fake_clock[0]):
                res = w.download_one(dbx, item, dest, total_files=1, allow_requeue=False)

            self.assertIsNone(res)
            self.assertEqual((dest / "paused.bin").read_bytes(), data)
            self.assertEqual(paused_events, [True, False])
            # Worker itself must not emit duplicate pause/resume log lines (handled solely by MainWindow)
            self.assertFalse(any("download paused" in l.lower() or "download resumed" in l.lower() for l in worker_logs))

    def test_stop_mid_verification_preserves_tmp_and_prevents_unverified_finalize(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            data, content_hash = make_payload(6 * 1024 * 1024)

            # Case 1: Existing complete .tmp stopped mid-hash
            tmp1 = dest / "f1.bin.tmp"
            tmp1.write_bytes(data)
            w1 = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")
            w1.current_progress.connect(lambda pct: w1.stop() if pct > 0 else None)
            item1 = DownloadFileItem("f1.bin", len(data), "f1.bin", "/f1.bin", content_hash=content_hash)
            w1.files = [item1]
            dbx_unused = FakeDbx(lambda *a: (_ for _ in ()).throw(AssertionError("Network should not be called")))
            self.assertIsNone(w1.download_one(dbx_unused, item1, dest, total_files=1))
            self.assertTrue(tmp1.exists())
            self.assertFalse((dest / "f1.bin").exists())

            # Case 2: Newly downloaded file stopped mid-hash
            w2 = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")
            w2.file_changed.connect(
                lambda txt: w2.stop() if ("🔍 Verifying file (" in txt and "0%" not in txt) else None
            )
            dbx2 = FakeDbx(lambda rng, kw, idx: (FakeMetadata(content_hash=content_hash), FakeResponse(data, 200)))
            item2 = DownloadFileItem("f2.bin", len(data), "f2.bin", "/f2.bin", content_hash=content_hash)
            w2.files = [item2]
            self.assertIsNone(w2.download_one(dbx2, item2, dest, total_files=1))
            self.assertTrue((dest / "f2.bin.tmp").exists())
            self.assertFalse((dest / "f2.bin").exists())

    def test_416_clears_tmp_and_200_fallback_and_restart_logging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            data, content_hash = make_payload(100_000)

            # 416 unlinks invalid .tmp before requeuing
            tmp_416 = dest / "bad_range.bin.tmp"
            tmp_416.write_bytes(data[:40_000])
            dbx_416 = FakeDbx(lambda *a: (_ for _ in ()).throw(Exception("HttpError 416 Range Not Satisfiable")))
            w_416 = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")
            item_416 = DownloadFileItem("bad_range.bin", len(data), "bad_range.bin", "/bad_range.bin", content_hash=content_hash)
            w_416.files = [item_416]
            self.assertEqual(w_416.download_one(dbx_416, item_416, dest, total_files=2, allow_requeue=True), "requeue")
            self.assertFalse(tmp_416.exists())

            # 0% retry logs structured 🔄 RESTART with [Attempt 2/3]
            calls = [0]

            def fail_once_handler(rng, kw, idx):
                calls[0] += 1
                if idx == 1:
                    raise ConnectionError("initial connection failed at 0 bytes")
                return FakeMetadata(content_hash=content_hash), FakeResponse(data, 200)

            dbx_restart = FakeDbx(fail_once_handler)
            w_restart = DownloadWorker("https://www.dropbox.com/sh/test/abc", str(dest), access_token="tok")
            restart_logs: list[str] = []
            w_restart.log.connect(restart_logs.append)
            item_r = DownloadFileItem("fresh.bin", len(data), "fresh.bin", "/fresh.bin", content_hash=content_hash)
            w_restart.files = [item_r]
            with (
                patch.object(workers_mod, "create_dropbox_client", return_value=dbx_restart),
                patch.object(workers_mod.time, "sleep", return_value=None),
            ):
                self.assertIsNone(w_restart.download_one(dbx_restart, item_r, dest, total_files=1, allow_requeue=False))
            self.assertTrue(any("🔄 RESTART" in l and "[Attempt 2/3]" in l for l in restart_logs))

    def test_queue_reordering_skip_existing_and_auto_repair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            d1, h1 = make_payload(80_000, b"FILE_ONE_DATA___")
            d2, h2 = make_payload(60_000, b"FILE_TWO_DATA___")
            d3, h3 = make_payload(50_000, b"FILE_THREE_DATA_")

            # Pre-seed:
            # - a.bin.tmp (partial -> tests Range rejection on Pass 1 -> requeue -> Pass 2 206 resume)
            # - b.bin (already exists with CORRUPTED bytes of same size -> tests Smart Skip + Post-Download Verification + Auto-Repair!)
            (dest / "a.bin.tmp").write_bytes(d1[:40_000])
            (dest / "b.bin").write_bytes(b"X" * len(d2))

            seen_calls: list[tuple[str | None, str | None]] = []

            def full_handler(rng, kw, idx):
                path = kw.get("path")
                seen_calls.append((path, rng))
                if path == "/a.bin":
                    a_calls = [c for c in seen_calls if c[0] == "/a.bin"]
                    if len(a_calls) == 1:
                        return FakeMetadata(content_hash=h1), FakeResponse(d1, 200)
                    offset = int((rng or "bytes=0-").split("=")[1].rstrip("-"))
                    return (
                        FakeMetadata(content_hash=h1),
                        FakeResponse(d1[offset:], 206, headers={"Content-Range": f"bytes {offset}-{len(d1)-1}/{len(d1)}"}),
                    )
                if path == "/b.bin":
                    return FakeMetadata(content_hash=h2), FakeResponse(d2, 200)
                return FakeMetadata(content_hash=h3), FakeResponse(d3, 200)

            fake_dbx = FakeDbx(full_handler)
            scanned = [
                {"name": "a.bin", "path": "a.bin", "is_dir": False, "size": len(d1), "content_hash": h1},
                {"name": "b.bin", "path": "b.bin", "is_dir": False, "size": len(d2), "content_hash": h2},
                {"name": "c.bin", "path": "c.bin", "is_dir": False, "size": len(d3), "content_hash": h3},
            ]

            w = DownloadWorker(
                "https://www.dropbox.com/sh/test/abc",
                str(dest),
                access_token="tok",
                skip_existing=True,
                verify_integrity=True,
                auto_repair=True,
                scanned_entries=scanned,
            )
            logs: list[str] = []
            finished_msgs: list[str] = []
            w.log.connect(logs.append)
            w.finished.connect(finished_msgs.append)

            with patch.object(workers_mod, "create_dropbox_client", return_value=fake_dbx):
                w.run()

            # Queue order: b.bin skipped initially -> a.bin requeued -> c.bin downloaded -> a.bin resumed -> b.bin auto-repaired!
            self.assertEqual([c[0] for c in seen_calls], ["/a.bin", "/c.bin", "/a.bin", "/b.bin"])
            self.assertEqual((dest / "a.bin").read_bytes(), d1)
            self.assertEqual((dest / "b.bin").read_bytes(), d2)
            self.assertEqual((dest / "c.bin").read_bytes(), d3)
            self.assertEqual(w.skipped, 1)
            self.assertEqual(w.repaired, 1)
            self.assertEqual(w.corrupted, 0)
            self.assertEqual(w.verified_ok, 3)
            self.assertFalse((dest / ".download_state.json").exists())
            self.assertTrue(finished_msgs and "✓ Download & Verification Finished Successfully!" in finished_msgs[0])


if __name__ == "__main__":
    unittest.main()
