import os
import sys
import re
import hashlib
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any

import dropbox
from dropbox.exceptions import ApiError, AuthError

try:
    from dropbox.content_hash import DropboxContentHasher
except ImportError:
    DropboxContentHasher = None

try:
    import shiboken6
except ImportError:
    shiboken6 = None

from PySide6.QtCore import QThread


def format_bytes(value: Any) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    try:
        size = float(value)
    except (ValueError, TypeError):
        return "0 B"
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    return sanitized or "DropboxDownload"


def extract_folder_name_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path).strip("/")
        parts = [p.strip() for p in path.split("/") if p.strip()]
        # /scl/fo/<id>/... paths contain an opaque internal ID, not the folder name
        if "scl" in parts and "fo" in parts:
            return ""
        ignore_parts = {"scl", "fo", "fi", "sh", "s", "h", "dl", "home", "personal", "work"}
        valid_parts = [p for p in parts if p.lower() not in ignore_parts and len(p) > 2]
        if valid_parts:
            candidate = valid_parts[-1]
            if candidate.lower() not in ignore_parts:
                if re.match(r'^[a-zA-Z0-9_-]{16,}$', candidate) and any(c.isdigit() for c in candidate) and any(c.isalpha() for c in candidate):
                    return ""
                return sanitize_filename(candidate)
    except Exception:
        pass
    return ""


def parse_friendly_error(error: Any) -> tuple[str, str]:
    err_str = str(error or "").strip()
    err_lower = err_str.lower()

    # 1. Broken / Not found / Expired link
    if any(k in err_lower for k in (
        "shared_link_not_found", "link_not_found", "not_found", "does not exist",
        "could not find", "endpoint_not_found", "path/not_found"
    )):
        return (
            "Link Not Working",
            "This Dropbox link is not working or could not be found.\n\n"
            "• The shared link may have been deleted, expired, or mistyped.\n"
            "• Please ensure you copied the full Dropbox shared link correctly."
        )

    # 2. Password protected / Access denied
    if any(k in err_lower for k in ("password", "requires_password")):
        return (
            "Password Required",
            "This Dropbox shared folder is protected with a password.\n\n"
            "Please enter the link password to view and download files."
        )

    if any(k in err_lower for k in ("shared_link_access_denied", "access_denied", "access denied", "permission_denied")):
        return (
            "Access Restricted",
            "Access to this Dropbox link is restricted.\n\n"
            "• You may not have permission to view or download this content.\n"
            "• If this folder requires a password, please provide it."
        )

    # 3. Invalid link / malformed URL
    if any(k in err_lower for k in (
        "invalid dropbox", "valid dropbox shared url", "invalid_shared_link",
        "malformed_path", "unsupported_link_type"
    )):
        return (
            "Invalid Dropbox Link",
            "The entered address is not a valid Dropbox link.\n\n"
            "Please paste a link starting with https://www.dropbox.com/scl/... or https://www.dropbox.com/sh/..."
        )

    # 4. Authentication / Session expired
    if any(k in err_lower for k in (
        "expired_access_token", "invalid_access_token", "autherror",
        "sign in with your dropbox account", "session expired", "invalid or expired"
    )):
        return (
            "Sign-In Required",
            "Your Dropbox sign-in session is missing or has expired.\n\n"
            "Please click 'Disconnect' (or 'Sign in with Dropbox') above to reconnect your account."
        )

    # 5. Network / Offline / Connection errors
    if any(k in err_lower for k in (
        "connectionerror", "max retries exceeded", "failed to establish a new connection",
        "getaddrinfo failed", "nodename nor servname provided", "network is unreachable",
        "name or service not known", "dns_probe"
    )):
        return (
            "Network Connection Error",
            "Could not connect to Dropbox servers.\n\n"
            "Please check your internet connection and verify that you are online."
        )

    # 6. Timeout
    if "timeout" in err_lower or "timed out" in err_lower:
        return (
            "Connection Timed Out",
            "The request to Dropbox took too long to complete.\n\n"
            "Please check your network speed and try again."
        )

    # 7. SSL / Firewall
    if "sslerror" in err_lower or "certificate verify failed" in err_lower:
        return (
            "Secure Connection Failed",
            "Could not establish a secure SSL connection to Dropbox.\n\n"
            "Please check if a VPN, proxy, or antivirus firewall is blocking Dropbox."
        )

    # 8. Rate Limiting / 429
    if any(k in err_lower for k in ("ratelimit", "too_many_requests", "too_many_write_operations", "429")):
        return (
            "Dropbox Busy",
            "Dropbox is temporarily rate limiting requests due to high traffic.\n\n"
            "Please wait a minute or two and try again."
        )

    # 9. Local disk & file system
    if any(k in err_lower for k in ("permission denied", "access is denied", "winerror 5")):
        return (
            "Permission Denied",
            "Cannot write to the selected destination folder.\n\n"
            "Please choose a local folder with write permissions (e.g. your Downloads or Documents folder)."
        )

    if any(k in err_lower for k in ("no space left on device", "enospc", "disk full")):
        return (
            "Disk Full",
            "There is not enough free storage space on your hard drive.\n\n"
            "Please free up disk space or choose a different save drive."
        )

    if "unsafe dropbox path" in err_lower:
        return (
            "Invalid Destination Path",
            "The save destination path is invalid.\n\n"
            "Please choose a standard local folder on your computer."
        )

    # 10. File size mismatch
    if "size mismatch" in err_lower:
        return (
            "Download Interrupted",
            "A file download was interrupted before completing.\n\n"
            "Please click 'Start Download' again to resume downloading the remaining files."
        )

    # Clean fallback
    cleaned = err_str
    cleaned = re.sub(r'^[a-zA-Z0-9_.]+(?:Error|Exception)\s*:\s*', '', cleaned)
    cleaned = re.sub(r'^ApiError\([\'"][^\'"]*[\'"],\s*', '', cleaned).rstrip(')')
    if not cleaned or len(cleaned) < 3:
        cleaned = "An unexpected error occurred while communicating with Dropbox."

    return (
        "Dropbox Error",
        f"{cleaned}\n\nPlease verify your link and connection, then try again."
    )


def is_thread_running(thread: Any) -> bool:
    """Safely check if a QThread is running, guarding against deleted C++ wrapper objects."""
    if thread is None:
        return False
    if shiboken6 is not None:
        try:
            if not shiboken6.isValid(thread):
                return False
        except Exception:
            return False
    try:
        return bool(thread.isRunning())
    except (RuntimeError, Exception):
        return False


def safe_local_path(root: Path, relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").strip("/")
    parts = []
    for p in normalized.split("/"):
        p = p.strip()
        if not p or p in (".", ".."):
            continue
        clean_part = re.sub(r'[<>:"/\\|?*]', '_', p).strip('. ')
        if clean_part:
            parts.append(clean_part)
    destination = root.joinpath(*parts).resolve()
    root_resolved = root.resolve()
    try:
        destination.relative_to(root_resolved)
    except ValueError:
        raise ValueError(f"Unsafe Dropbox path: {relative_path}")
    return destination


def strip_folder_prefix(rel_path: str, prefix: str) -> str:
    """Strip a matched folder prefix from relative path for direct folder saving."""
    norm_rel = rel_path.replace("\\", "/").strip("/")
    norm_pre = prefix.replace("\\", "/").strip("/")
    if not norm_pre:
        return norm_rel
    if norm_rel.lower() == norm_pre.lower():
        return ""
    if norm_rel.lower().startswith(norm_pre.lower() + "/"):
        return norm_rel[len(norm_pre) + 1:]
    return norm_rel


def check_single_folder_destination_match(
    files: list,
    destination: Path | str,
    single_folder_hint: str = "",
) -> tuple[str | None, str | None]:
    """
    Check if exactly 1 folder was selected for download and if the destination folder's
    name matches that selected folder (case-insensitive and Windows-sanitized).
    
    Returns:
        (matched_folder_name, prefix_to_strip) or (None, None)
    """
    if not files:
        return None, None

    dest_path = Path(destination)
    dest_name = dest_path.resolve().name if dest_path.is_absolute() else dest_path.name
    dest_name = dest_name.strip()
    if not dest_name:
        return None, None

    dest_lower = dest_name.lower()
    dest_clean_lower = sanitize_filename(dest_name).lower()

    # Step 1: Collect normalized parts of all files
    all_parts = []
    for entry in files:
        rel = getattr(entry, "rel_path", "") if not isinstance(entry, dict) else entry.get("rel_path", "")
        rel_clean = rel.replace("\\", "/").strip("/")
        parts = [p for p in rel_clean.split("/") if p]
        if len(parts) <= 1:
            # File is at the root level, so files outside any subfolder are selected
            return None, None
        all_parts.append(parts)

    # Step 2: Check if all files share the exact same top-level folder
    top_folder = all_parts[0][0]
    if not all(p[0].lower() == top_folder.lower() for p in all_parts):
        return None, None

    # Step 3: Find common folder prefix across all files
    common_segments = [top_folder]
    min_depth = min(len(p) for p in all_parts)
    for idx in range(1, min_depth - 1):  # leave last item (filename)
        seg = all_parts[0][idx]
        if all(p[idx].lower() == seg.lower() for p in all_parts):
            common_segments.append(seg)
        else:
            break

    # Check if dest_name matches any segment in common_segments (deepest to shallowest)
    for i in range(len(common_segments) - 1, -1, -1):
        seg = common_segments[i]
        seg_lower = seg.lower()
        seg_clean_lower = sanitize_filename(seg).lower()
        if (
            dest_lower == seg_lower
            or dest_lower == seg_clean_lower
            or dest_clean_lower == seg_lower
            or dest_clean_lower == seg_clean_lower
        ):
            matched_prefix = "/".join(common_segments[:i + 1])
            return seg, matched_prefix

    # Also check if single_folder_hint matches dest_name
    if single_folder_hint:
        hint_clean = single_folder_hint.replace("\\", "/").strip("/")
        hint_name = Path(hint_clean).name.strip()
        hint_lower = hint_name.lower()
        hint_clean_lower = sanitize_filename(hint_name).lower()
        if (
            dest_lower == hint_lower
            or dest_lower == hint_clean_lower
            or dest_clean_lower == hint_lower
            or dest_clean_lower == hint_clean_lower
        ):
            # Verify that all files start with hint_clean
            if all(
                getattr(e, "rel_path", "").replace("\\", "/").strip("/").lower().startswith(hint_clean.lower() + "/")
                for e in files
            ):
                return hint_name, hint_clean

    return None, None


def resolve_download_root(destination: Path | str, root_name: str = "", raw_root_name: str = "") -> tuple[Path, bool]:
    """
    Determine the local root directory for saving files.
    Downloads directly into the destination folder (does not create an unwanted root folder).

    Returns:
        (resolved_root_path, is_same_folder)
    """
    dest_path = Path(destination)
    clean_root = sanitize_filename(root_name) if root_name else ""
    dest_folder_name = dest_path.resolve().name if dest_path.is_absolute() else dest_path.name
    dest_folder_name = dest_folder_name.strip()

    clean_root_lower = clean_root.strip().lower()
    raw_root_lower = (raw_root_name.strip().lower() if raw_root_name else clean_root_lower)
    dest_lower = dest_folder_name.lower()
    dest_sanitized_lower = sanitize_filename(dest_folder_name).strip().lower()

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


