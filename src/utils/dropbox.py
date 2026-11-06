import re
import hashlib
from pathlib import Path
from typing import Any

import dropbox

try:
    from dropbox.content_hash import DropboxContentHasher
except ImportError:
    DropboxContentHasher = None


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    return sanitized or "DropboxDownload"


def resolve_download_root(destination: Path | str, root_name: str = "", raw_root_name: str = "") -> tuple[Path, bool]:
    """
    Determine the local root directory for saving files.
    Downloads directly into the destination folder (does not create an unwanted root folder).

    Returns:
        (resolved_root_path, is_same_folder)
    """
    dest_path = Path(destination)
    clean_root = _sanitize_name(root_name) if root_name else ""
    dest_folder_name = dest_path.resolve().name if dest_path.is_absolute() else dest_path.name
    dest_folder_name = dest_folder_name.strip()

    clean_root_lower = clean_root.strip().lower()
    raw_root_lower = (raw_root_name.strip().lower() if raw_root_name else clean_root_lower)
    dest_lower = dest_folder_name.lower()
    dest_sanitized_lower = _sanitize_name(dest_folder_name).strip().lower()

    # Check if selected destination folder name matches Dropbox folder name (case-insensitive)
    is_same = bool(
        dest_lower
        and clean_root_lower
        and (
            dest_lower == clean_root_lower
            or dest_lower == raw_root_lower
            or dest_sanitized_lower == clean_root_lower
            or dest_sanitized_lower == raw_root_lower
        )
    )

    return dest_path, is_same


def relative_path(entry: Any) -> str:
    if hasattr(entry, "rel_path"):
        return entry.rel_path
    path = getattr(entry, "path_display", None)
    return path.lstrip("/") if path else getattr(entry, "name", "")


def get_file_type_and_icon(filename: str) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico', '.tiff'):
        return f"{ext[1:].upper()} Image" if ext else "Image", "🖼️ "
    elif ext in ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'):
        return f"{ext[1:].upper()} Video" if ext else "Video", "🎬 "
    elif ext in ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'):
        return f"{ext[1:].upper()} Audio" if ext else "Audio", "🎵 "
    elif ext in ('.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.xz'):
        return f"{ext[1:].upper()} Archive" if ext else "Archive", "📦 "
    elif ext in ('.pdf',):
        return "PDF Document", "📕 "
    elif ext in ('.doc', '.docx', '.odt'):
        return "Word Document", "📘 "
    elif ext in ('.xls', '.xlsx', '.csv'):
        return "Spreadsheet", "📊 "
    elif ext in ('.ppt', '.pptx'):
        return "Presentation", "📙 "
    elif ext in ('.txt', '.md', '.rtf', '.log', '.json', '.xml', '.yaml', '.yml', '.py', '.js', '.ts', '.html', '.css'):
        return f"{ext[1:].upper()} Text" if ext else "Text File", "📝 "
    elif ext in ('.exe', '.msi', '.apk'):
        return "Executable", "⚙️ "
    else:
        return f"{ext[1:].upper()} File" if ext else "File", "📄 "


def natural_sort_key(s: str) -> list[int | str]:
    """Sort strings containing numbers in natural human order (e.g. 1, 2, 10 instead of 1, 10, 2)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def natural_sort_path_key(item: Any) -> list:
    """Extract and split relative path into natural sort tokens for hierarchical order."""
    rel = getattr(item, "rel_path", None) or getattr(item, "_custom_rel_path", None) or ""
    if not rel and isinstance(item, dict):
        rel = item.get("rel_path") or item.get("path") or ""
    elif not rel and hasattr(item, "path_display"):
        rel = getattr(item, "path_display") or ""
    clean = str(rel).replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p] if clean else [getattr(item, "name", "")]
    return [natural_sort_key(part) for part in parts]


def compute_dropbox_content_hash(
    path: Path,
    check_pause_func: Any = None,
    progress_cb: Any = None,
    stop_check_func: Any = None,
) -> str:
    """Compute the Dropbox-compatible SHA-256 block hash for a local file to verify integrity."""
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    block_size = 4 * 1024 * 1024  # 4 MB blocks
    file_size = path.stat().st_size
    read_bytes = 0

    if DropboxContentHasher is not None:
        hasher = DropboxContentHasher()
        with open(path, "rb") as f:
            while True:
                if stop_check_func and stop_check_func():
                    return ""
                if check_pause_func:
                    check_pause_func()
                chunk = f.read(block_size)
                if not chunk:
                    break
                hasher.update(chunk)
                read_bytes += len(chunk)
                if progress_cb and file_size > 0:
                    try:
                        progress_cb(int(read_bytes * 100 / file_size), len(chunk))
                    except TypeError:
                        progress_cb(int(read_bytes * 100 / file_size))
        return hasher.hexdigest()
    else:
        block_hashes = b""
        with open(path, "rb") as f:
            while True:
                if stop_check_func and stop_check_func():
                    return ""
                if check_pause_func:
                    check_pause_func()
                chunk = f.read(block_size)
                if not chunk:
                    break
                block_hashes += hashlib.sha256(chunk).digest()
                read_bytes += len(chunk)
                if progress_cb and file_size > 0:
                    try:
                        progress_cb(int(read_bytes * 100 / file_size), len(chunk))
                    except TypeError:
                        progress_cb(int(read_bytes * 100 / file_size))
        return hashlib.sha256(block_hashes).hexdigest()


def build_tree_hierarchy(entries: list, root_name: str = "DropboxFolder") -> dict[str, Any]:
    root: dict[str, Any] = {
        "name": root_name,
        "path": "",
        "is_dir": True,
        "size": 0,
        "total_size": 0,
        "file_count": 0,
        "folder_count": 0,
        "children": {},
    }
    for item in entries:
        raw_path = item.get("path", "").replace("\\", "/").strip("/")
        if not raw_path:
            continue
        parts = [p.strip() for p in raw_path.split("/") if p.strip()]
        if not parts:
            continue

        if len(parts) > 1 and parts[0].lower() == root_name.lower():
            parts = parts[1:]
        elif len(parts) == 1 and parts[0].lower() == root_name.lower() and item.get("is_dir"):
            continue

        curr: dict[str, Any] = root
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            children: dict[str, Any] = curr["children"]
            if part not in children:
                children[part] = {
                    "name": part,
                    "path": "/".join(parts[:i + 1]),
                    "is_dir": item["is_dir"] if is_last else True,
                    "size": item.get("size", 0) if is_last else 0,
                    "total_size": 0,
                    "file_count": 0,
                    "folder_count": 0,
                    "children": {},
                    "content_hash": item.get("content_hash") if is_last else None,
                }
            elif is_last:
                children[part]["is_dir"] = item["is_dir"]
                children[part]["size"] = item.get("size", 0)
                children[part]["content_hash"] = item.get("content_hash")
            curr = children[part]

    def compute_metrics(node: dict[str, Any]) -> tuple[int, int]:
        if not node["is_dir"]:
            return int(node.get("size", 0) or 0), 1
        total_sz = 0
        total_fl = 0
        total_fo = 0
        for child in node["children"].values():
            c_sz, c_fl = compute_metrics(child)
            total_sz += c_sz
            total_fl += c_fl
            if child["is_dir"]:
                total_fo += 1
        node["total_size"] = total_sz
        node["file_count"] = total_fl
        node["folder_count"] = total_fo
        return total_sz, total_fl

    compute_metrics(root)
    return root


def is_path_selected(
    candidate_path: str,
    selected_files: set,
    deselected_files: set,
    selected_folders: set,
    deselected_folders: set,
    has_tree_filter: bool = True,
) -> bool:
    if not has_tree_filter:
        return True

    norm = candidate_path.replace("\\", "/").strip("/")
    if not norm:
        return False

    parts = [p for p in norm.split("/") if p]
    if not parts:
        return False

    all_suffixes = ["/".join(parts[i:]) for i in range(len(parts))]

    for suffix in all_suffixes:
        if suffix in deselected_files:
            return False

    for suffix in all_suffixes:
        if suffix in selected_files:
            return True

    for suffix in all_suffixes:
        if suffix in deselected_folders:
            return False

    for suffix in all_suffixes:
        if suffix in selected_folders:
            return True

    for i in range(len(parts) - 1, 0, -1):
        ancestor = "/".join(parts[:i])
        for suffix in ["/".join(ancestor.split("/")[j:]) for j in range(len(ancestor.split("/")))]:
            if suffix in deselected_folders:
                return False
            if suffix in selected_folders:
                return True

    if selected_files or selected_folders:
        return False

    return True


def create_dropbox_client(
    access_token: str | None = None,
    refresh_token: str | None = None,
    app_key: str | None = None,
    timeout: float = 30.0,
) -> dropbox.Dropbox:
    """Create an authenticated Dropbox client, supporting OAuth PKCE refresh tokens and explicit network timeouts."""
    r_token = (refresh_token or "").strip()
    a_token = (access_token or "").strip()
    k = (app_key or "").strip()

    if r_token and k:
        return dropbox.Dropbox(
            oauth2_access_token=a_token or None,
            oauth2_refresh_token=r_token,
            app_key=k,
            timeout=timeout,
        )
    if a_token:
        return dropbox.Dropbox(oauth2_access_token=a_token, timeout=timeout)
    raise ValueError("Not authenticated. Please sign in with your Dropbox account first.")

