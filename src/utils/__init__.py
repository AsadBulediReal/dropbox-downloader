import re
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any

try:
    import shiboken6
except ImportError:
    shiboken6 = None

from .dropbox import (
    DropboxContentHasher,
    resolve_download_root,
    relative_path,
    get_file_type_and_icon,
    natural_sort_key,
    natural_sort_path_key,
    compute_dropbox_content_hash,
    build_tree_hierarchy,
    is_path_selected,
    create_dropbox_client,
)


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
                if (
                    re.match(r'^[a-zA-Z0-9_-]{16,}$', candidate)
                    and any(c.isdigit() for c in candidate)
                    and any(c.isalpha() for c in candidate)
                ):
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
