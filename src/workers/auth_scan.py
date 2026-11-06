import time
from urllib.parse import urlparse
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from dropbox.files import FileMetadata, FolderMetadata, SharedLink
from dropbox.exceptions import ApiError, AuthError
from PySide6.QtCore import QObject, QThread, Signal, Slot

from ..utils import sanitize_filename, build_tree_hierarchy
import src.workers as _workers_pkg


# ==============================================================================
# Auth Worker (Authenticates via OAuth PKCE in background thread)
# ==============================================================================
class AuthWorker(QObject):
    finished = Signal(str, str, str, str)  # access_token, refresh_token, user_name, user_email
    failed = Signal(str)
    status = Signal(str)
    progress = Signal(int)

    def __init__(self, flow: Any, code: str, app_key: str):
        super().__init__()
        self.flow = flow
        self.code = code.strip()
        self.app_key = app_key.strip()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    @Slot()
    def run(self):
        try:
            self.status.emit("Exchanging authorization code with Dropbox...")
            self.progress.emit(25)
            oauth_res: Any = self.flow.finish(self.code)
            if self._is_cancelled:
                return

            access_token = getattr(oauth_res, "access_token", None) or ""
            refresh_token = getattr(oauth_res, "refresh_token", None) or ""

            self.status.emit("Connecting to Dropbox API...")
            self.progress.emit(55)
            dbx = _workers_pkg.create_dropbox_client(
                access_token=access_token,
                refresh_token=refresh_token,
                app_key=self.app_key,
            )
            if self._is_cancelled:
                return

            self.status.emit("Retrieving account profile...")
            self.progress.emit(80)
            account: Any = dbx.users_get_current_account()
            if self._is_cancelled:
                return

            user_name = (
                account.name.display_name
                if account and hasattr(account, "name") and account.name
                else "Dropbox User"
            )
            user_email = account.email if account and hasattr(account, "email") else ""

            self.status.emit("Completing sign in...")
            self.progress.emit(95)
            self.finished.emit(access_token, refresh_token, user_name, user_email)
        except Exception as exc:
            if not self._is_cancelled:
                self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass


class SessionVerifyWorker(QObject):
    finished = Signal(str, str)  # user_name, user_email
    expired = Signal(str)
    failed = Signal(str)

    def __init__(self, access_token: str, refresh_token: str, app_key: str):
        super().__init__()
        self.access_token = access_token.strip()
        self.refresh_token = refresh_token.strip()
        self.app_key = app_key.strip()

    @Slot()
    def run(self):
        try:
            dbx = _workers_pkg.create_dropbox_client(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                app_key=self.app_key,
            )
            account: Any = dbx.users_get_current_account()
            user_name = (
                account.name.display_name
                if account and hasattr(account, "name") and account.name
                else "Dropbox User"
            )
            user_email = account.email if account and hasattr(account, "email") else ""
            self.finished.emit(user_name, user_email)
        except AuthError as exc:
            self.expired.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass


# ==============================================================================
# Scan Worker (Inspects folders via Dropbox API)
# ==============================================================================
class ScanWorker(QObject):
    finished = Signal(dict, str, list)  # tree_dict, root_name, entries_list
    failed = Signal(str)
    status = Signal(str)

    def __init__(
        self,
        url: str,
        token: str = "",
        password: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        app_key: str | None = None,
    ):
        super().__init__()
        self.url = url.strip()
        self.access_token = (access_token or token or "").strip()
        self.refresh_token = (refresh_token or "").strip()
        self.app_key = (app_key or "").strip()
        self.token = self.access_token
        self.password = password.strip() if password else None
        self._is_cancelled: bool = False

    def cancel(self):
        self._is_cancelled = True

    @Slot()
    def run(self):
        try:
            if self._is_cancelled:
                return
            parsed = urlparse(self.url)
            if parsed.scheme not in ("http", "https") or "dropbox.com" not in parsed.netloc:
                raise ValueError("Please enter a valid Dropbox shared URL.")

            if not self.access_token and not self.refresh_token:
                raise ValueError("Please sign in with your Dropbox account to inspect folders.")

            entries = []
            root_name = "DropboxFolder"

            self.status.emit("Connecting to Dropbox API...")
            dbx = _workers_pkg.create_dropbox_client(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                app_key=self.app_key,
            )

            try:
                meta_kwargs: dict[str, Any] = {"url": self.url}
                if self.password:
                    meta_kwargs["link_password"] = self.password
                meta = dbx.sharing_get_shared_link_metadata(**meta_kwargs)
                root_name = getattr(meta, "name", None) or "DropboxFolder"

                # Fast path: Single file shared link
                if isinstance(meta, FileMetadata):
                    file_name = getattr(meta, "name", "file")
                    file_size = getattr(meta, "size", 0)
                    file_hash = getattr(meta, "content_hash", None)
                    entries = [{
                        "name": file_name,
                        "path": file_name,
                        "is_dir": False,
                        "size": file_size,
                        "content_hash": file_hash,
                    }]
                    root_name = sanitize_filename(root_name) or "DropboxFolder"
                    tree = build_tree_hierarchy(entries, root_name)
                    self.finished.emit(tree, root_name, entries)
                    return
            except ApiError as exc:
                if "shared_link_access_denied" in str(exc).lower() or "password" in str(exc).lower():
                    raise ValueError(
                        "Access Denied: This link is password-protected.\n"
                        "Please enter the link password in the credentials section."
                    )
                raise

            shared_link = SharedLink(
                url=self.url,
                password=self.password if self.password else None,
            )

            self.status.emit("Querying folder hierarchy...")

            rec_success = False
            try:
                res: Any = dbx.files_list_folder(
                    path="",
                    shared_link=shared_link,
                    recursive=True,
                    include_non_downloadable_files=True,
                )
                while res:
                    if self._is_cancelled:
                        break
                    if hasattr(res, "entries"):
                        for e in res.entries:
                            if self._is_cancelled:
                                break
                            is_dir = isinstance(e, FolderMetadata)
                            name = getattr(e, "name", "")
                            if not name:
                                continue
                            path_display = getattr(e, "path_display", None) or getattr(e, "path_lower", None)
                            rel = path_display.lstrip("/") if path_display else name
                            size = getattr(e, "size", 0) if not is_dir else 0
                            item_hash = getattr(e, "content_hash", None) if not is_dir else None
                            entries.append({
                                "name": name,
                                "path": rel,
                                "is_dir": is_dir,
                                "size": size,
                                "content_hash": item_hash,
                            })
                    if getattr(res, "has_more", False) and not self._is_cancelled:
                        res = dbx.files_list_folder_continue(res.cursor)
                    else:
                        break
                rec_success = True
            except Exception:
                entries = []
                rec_success = False

            if not rec_success and not self._is_cancelled:
                def fetch_folder_entries(api_path: str, rel_dir: str) -> tuple[list[dict], list[tuple[str, str]]]:
                    if self._is_cancelled:
                        return [], []
                    local_entries = []
                    local_subfolders = []
                    max_retries = 3
                    res: Any = None
                    for attempt in range(max_retries):
                        if self._is_cancelled:
                            break
                        try:
                            res = dbx.files_list_folder(path=api_path, shared_link=shared_link, recursive=False)
                            break
                        except Exception:
                            if attempt < max_retries - 1 and not self._is_cancelled:
                                time.sleep(1.0 * (attempt + 1))
                            else:
                                break
                    while res:
                        if self._is_cancelled:
                            break
                        if hasattr(res, "entries"):
                            for e in res.entries:
                                if self._is_cancelled:
                                    break
                                is_dir = isinstance(e, FolderMetadata)
                                name = e.name
                                if not name:
                                    continue
                                rel = f"{rel_dir}/{name}".strip("/") if rel_dir else name
                                size = getattr(e, "size", 0) if not is_dir else 0
                                item_hash = getattr(e, "content_hash", None) if not is_dir else None
                                local_entries.append({
                                    "name": name,
                                    "path": rel,
                                    "is_dir": is_dir,
                                    "size": size,
                                    "content_hash": item_hash,
                                })
                                if is_dir:
                                    next_api = f"{api_path}/{name}" if api_path else f"/{name}"
                                    local_subfolders.append((next_api, rel))
                        if getattr(res, "has_more", False) and not self._is_cancelled:
                            for attempt in range(max_retries):
                                try:
                                    res = dbx.files_list_folder_continue(res.cursor)
                                    break
                                except Exception:
                                    if attempt < max_retries - 1 and not self._is_cancelled:
                                        time.sleep(1.0 * (attempt + 1))
                                    else:
                                        res = None
                                        break
                        else:
                            break
                    return local_entries, local_subfolders

                root_items, pending_subfolders = fetch_folder_entries("", "")
                entries.extend(root_items)

                if pending_subfolders and not self._is_cancelled:
                    max_workers = min(4, max(2, len(pending_subfolders)))
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        while pending_subfolders and not self._is_cancelled:
                            current_batch = pending_subfolders
                            pending_subfolders = []

                            futures = [
                                executor.submit(fetch_folder_entries, api_path, rel_dir)
                                for api_path, rel_dir in current_batch
                            ]

                            for future in as_completed(futures):
                                if self._is_cancelled:
                                    break
                                try:
                                    sub_items, sub_folders = future.result()
                                    entries.extend(sub_items)
                                    pending_subfolders.extend(sub_folders)
                                except Exception:
                                    pass

            if self._is_cancelled:
                return

            root_name = sanitize_filename(root_name) or "DropboxFolder"
            tree = build_tree_hierarchy(entries, root_name)
            self.finished.emit(tree, root_name, entries)

        except Exception as exc:
            if not self._is_cancelled:
                self.failed.emit(str(exc))
        finally:
            try:
                QThread.currentThread().quit()
            except Exception:
                pass

