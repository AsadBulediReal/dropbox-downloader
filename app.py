import sys
from PySide6.QtWidgets import QApplication

from src import (
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
    MainWindow,
    format_bytes,
    sanitize_filename,
    extract_folder_name_from_url,
    parse_friendly_error,
    is_thread_running,
    safe_local_path,
    strip_folder_prefix,
    check_single_folder_destination_match,
    resolve_download_root,
    relative_path,
    get_file_type_and_icon,
    natural_sort_key,
    natural_sort_path_key,
    compute_dropbox_content_hash,
    build_tree_hierarchy,
    is_path_selected,
    create_dropbox_client,
    AuthWorker,
    SessionVerifyWorker,
    ScanWorker,
    DownloadFileItem,
    DownloadWorker,
    ModernMessageBox,
    ModernInputDialog,
    ModernLoadingDialog,
    FileTreeWidget,
)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
