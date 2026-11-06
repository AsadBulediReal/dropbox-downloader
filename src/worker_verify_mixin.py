from pathlib import Path

import dropbox

from .utils import format_bytes, compute_dropbox_content_hash, safe_local_path
from .worker_collect_mixin import DownloadFileItem


class _DownloadVerifyMixin:
    def _inline_verify_temp_file(self, temp_file: Path, exp_hash: str, file_display: str) -> str:
        self.file_changed.emit(f"🔍 Verifying file (0%): {file_display}")
        self.is_inline_verifying = True
        self._speed_window.clear()
        self.instant_speed = 0.0

        def _on_hash_prog(pct: int, chunk_len: int = 0):
            self.current_progress.emit(pct)
            self.file_changed.emit(f"🔍 Verifying file ({pct}%): {file_display}")
            if chunk_len > 0:
                self.update_speed_tracker(chunk_len)
            self.emit_stats()

        try:
            return compute_dropbox_content_hash(
                temp_file,
                check_pause_func=self._check_pause,
                progress_cb=_on_hash_prog,
                stop_check_func=lambda: self.stop_requested,
            )
        finally:
            self.is_inline_verifying = False
            self._speed_window.clear()
            self.instant_speed = 0.0

    def _run_verification_and_repair(
        self,
        dbx: dropbox.Dropbox,
        local_root: Path,
        total_selected: int,
    ):
        self.is_verifying = True
        self.log.emit("\n" + "=" * 60)
        if self.verify_only:
            self.log.emit(f"🔍 Starting File Integrity Verification ({total_selected} file(s))...")
        else:
            self.log.emit(f"🔍 Post-Download Verification: Checking {total_selected} file(s) for corruption...")
        self.log.emit("🔍 Verifying exact file sizes and Dropbox SHA-256 block hashes...")
        self.log.emit("=" * 60)
        self.folder_changed.emit("Verifying Files...")
        self.overall_progress.emit(0)

        corrupted_items: list[tuple[DownloadFileItem, str]] = []

        for v_idx, entry in enumerate(self.files, start=1):
            self._check_pause()
            if self.stop_requested:
                break

            rel_clean = entry.rel_path.replace("\\", "/").strip("/")
            folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
            file_display = entry.name or Path(rel_clean).name

            self.folder_changed.emit(f"Verifying ({v_idx}/{total_selected}): [{folder_display}]")
            self.file_changed.emit(f"{file_display}  ({format_bytes(entry.size)})")
            self.current_progress.emit(0)

            local_file = safe_local_path(local_root, entry.rel_path)

            if not local_file.exists() or not local_file.is_file():
                self.missing += 1
                self.log.emit(f"❌ MISSING [{folder_display}] {file_display}: File not found on disk.")
                corrupted_items.append((entry, "file missing on disk"))
                continue

            actual_size = local_file.stat().st_size
            if actual_size != entry.size:
                self.corrupted += 1
                self.log.emit(
                    f"❌ CORRUPTED [{folder_display}] {file_display}: Size mismatch! "
                    f"(Expected {format_bytes(entry.size)}, got {format_bytes(actual_size)})"
                )
                corrupted_items.append((entry, f"size mismatch (expected {entry.size}, got {actual_size})"))
                continue

            # Hash check
            expected_hash = entry.content_hash or (
                getattr(entry.metadata, "content_hash", None) if entry.metadata else None
            )
            try:
                self.file_changed.emit(f"🔍 Verifying file (0%): {file_display}")

                def on_v_prog(pct: int, chunk_len: int = 0, fd: str = file_display):
                    self.current_progress.emit(pct)
                    self.file_changed.emit(f"🔍 Verifying file ({pct}%): {fd}")
                    if chunk_len > 0:
                        self.update_speed_tracker(chunk_len)
                    self.emit_stats()

                calc_hash = compute_dropbox_content_hash(
                    local_file,
                    check_pause_func=self._check_pause,
                    progress_cb=on_v_prog,
                    stop_check_func=lambda: self.stop_requested,
                )
                if self.stop_requested:
                    break

                if expected_hash and calc_hash.lower() != expected_hash.lower():
                    self.corrupted += 1
                    self.log.emit(
                        f"❌ CORRUPTED [{folder_display}] {file_display}: Checksum mismatch! "
                        f"(Expected {expected_hash[:10]}..., got {calc_hash[:10]}...)"
                    )
                    corrupted_items.append((entry, "checksum mismatch"))
                    continue

                self.verified_ok += 1
                self.current_progress.emit(100)
                hash_note = f" [Hash: {calc_hash[:8]}...]" if expected_hash else ""
                self.log.emit(f"✓ VERIFIED [{folder_display}] {file_display}{hash_note}")

            except Exception as err:
                self.corrupted += 1
                self.log.emit(f"❌ UNREADABLE [{folder_display}] {file_display}: {err}")
                corrupted_items.append((entry, f"unreadable: {err}"))

            self.overall_progress.emit(int(v_idx * 100 / total_selected))
            self.emit_stats()

        # Auto-Repair Phase
        if self.auto_repair and corrupted_items and not self.stop_requested and not self.verify_only:
            self.log.emit(f"\n🔧 Auto-Repair: Re-downloading {len(corrupted_items)} corrupted/missing file(s)...")
            for bad_entry, reason in corrupted_items:
                self._check_pause()
                if self.stop_requested:
                    break

                rel_clean = bad_entry.rel_path.replace("\\", "/").strip("/")
                folder_display = Path(rel_clean).parent.as_posix() if "/" in rel_clean else "/ (Root)"
                file_display = bad_entry.name or Path(rel_clean).name

                self.log.emit(f"🔄 REPAIRING [{folder_display}] {file_display} ({reason})...")
                bad_path = safe_local_path(local_root, bad_entry.rel_path)
                bad_path.unlink(missing_ok=True)

                # Re-download
                self.download_one(dbx, bad_entry, local_root, total_files=total_selected, allow_requeue=False)
                if self.stop_requested:
                    break

                # Re-verify repaired file
                if bad_path.exists() and bad_path.is_file():
                    try:
                        repaired_size = bad_path.stat().st_size
                        if repaired_size == bad_entry.size:
                            self.file_changed.emit(f"🔍 Verifying repaired file (0%): {file_display}")

                            def on_repair_v_prog(pct: int, chunk_len: int = 0, fd: str = file_display):
                                self.current_progress.emit(pct)
                                self.file_changed.emit(f"🔍 Verifying repaired file ({pct}%): {fd}")
                                if chunk_len > 0:
                                    self.update_speed_tracker(chunk_len)
                                self.emit_stats()

                            calc_h = compute_dropbox_content_hash(
                                bad_path,
                                check_pause_func=self._check_pause,
                                progress_cb=on_repair_v_prog,
                                stop_check_func=lambda: self.stop_requested,
                            )
                            if self.stop_requested:
                                break
                            exp_h = bad_entry.content_hash or (
                                getattr(bad_entry.metadata, "content_hash", None) if bad_entry.metadata else None
                            )
                            if not exp_h or calc_h.lower() == exp_h.lower():
                                self.repaired += 1
                                if self.corrupted > 0:
                                    self.corrupted -= 1
                                self.verified_ok += 1
                                self.log.emit(
                                    f"✓ REPAIRED [{folder_display}] {file_display}: Re-downloaded and verified intact!"
                                )
                                continue
                    except Exception:
                        pass
                self.log.emit(f"❌ REPAIR FAILED [{folder_display}] {file_display}: Still invalid after re-download.")

    def _build_completion_message(self, local_root: Path, total_selected: int, elapsed: float) -> str:
        if self.stop_requested:
            return "Download cancelled by user."

        lines = []
        if self.verify_only:
            if self.corrupted > 0 or self.missing > 0:
                lines.append("⚠️ Verification Completed with Warnings!")
            else:
                lines.append("✓ Verification Completed Successfully!")
        elif self.verify_integrity:
            if self.corrupted > 0 or self.missing > 0 or self.errors > 0:
                lines.append("⚠️ Download Finished with Verification Warnings!")
            else:
                lines.append("✓ Download & Verification Finished Successfully!")
        else:
            lines.append("✓ Download Finished Successfully!")

        lines.append("")
        lines.append(f"Files Selected: {total_selected}")
        if not self.verify_only:
            lines.append(f"Completed: {self.done}")
            lines.append(f"Skipped: {self.skipped}")
        if self.verify_integrity:
            lines.append(f"Verified Intact: {self.verified_ok} of {total_selected}")
            if self.repaired > 0:
                lines.append(f"Auto-Repaired: {self.repaired}")
            if self.corrupted > 0:
                lines.append(f"Corrupted: {self.corrupted}")
            if self.missing > 0:
                lines.append(f"Missing: {self.missing}")
        if self.errors > 0:
            lines.append(f"Errors: {self.errors}")
        if not self.verify_only:
            lines.append(f"Data Transferred: {format_bytes(self.bytes_done)}")
        lines.append(f"Time Elapsed: {elapsed:.1f}s")
        lines.append(f"Output Directory: {local_root}")
        return "\n".join(lines)
