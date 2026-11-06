from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QTreeWidget,
    QHeaderView,
)


def build_step3_page(win: Any) -> QWidget:
    step3_page = QWidget()
    step3_outer = QHBoxLayout(step3_page)
    step3_outer.setContentsMargins(0, 0, 0, 0)
    step3_outer.addStretch(1)

    win.progress_card = QWidget()
    win.progress_card.setMaximumWidth(920)
    win.progress_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    step3_layout = QVBoxLayout(win.progress_card)
    step3_layout.setContentsMargins(0, 4, 0, 4)
    step3_layout.setSpacing(12)

    # Inline Transfer Completion / Status Banner (replaces modal completion popup)
    win.transfer_notice_banner = QFrame()
    win.transfer_notice_banner.setObjectName("transferNoticeBanner")
    win.transfer_notice_banner.setVisible(False)
    notice_layout = QHBoxLayout(win.transfer_notice_banner)
    notice_layout.setContentsMargins(16, 12, 12, 12)
    notice_layout.setSpacing(12)

    win.transfer_notice_icon = QLabel("✓")
    win.transfer_notice_icon.setFixedSize(34, 34)
    win.transfer_notice_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    notice_layout.addWidget(win.transfer_notice_icon, 0, Qt.AlignmentFlag.AlignVCenter)

    notice_text_col = QVBoxLayout()
    notice_text_col.setContentsMargins(0, 0, 0, 0)
    notice_text_col.setSpacing(2)

    win.transfer_notice_title = QLabel("")
    win.transfer_notice_detail = QLabel("")
    win.transfer_notice_detail.setWordWrap(True)
    win.transfer_notice_detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    notice_text_col.addWidget(win.transfer_notice_title)
    notice_text_col.addWidget(win.transfer_notice_detail)
    notice_layout.addLayout(notice_text_col, 1)

    win.btn_dismiss_transfer_notice = QPushButton("✕")
    win.btn_dismiss_transfer_notice.setProperty("class", "btn-ghost")
    win.btn_dismiss_transfer_notice.setFixedSize(28, 28)
    win.btn_dismiss_transfer_notice.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_dismiss_transfer_notice.setToolTip("Dismiss message")
    win.btn_dismiss_transfer_notice.clicked.connect(win.hide_transfer_notice)
    notice_layout.addWidget(win.btn_dismiss_transfer_notice, 0, Qt.AlignmentFlag.AlignTop)

    step3_layout.addWidget(win.transfer_notice_banner)

    # Row 1: 3 Bold Summary Stat Cards (Downloaded / Remaining / Speed & Time)
    stats_row = QGridLayout()
    stats_row.setSpacing(12)
    stats_row.setColumnStretch(0, 1)
    stats_row.setColumnStretch(1, 1)
    stats_row.setColumnStretch(2, 1)

    # Card A: Downloaded
    card_done = QFrame()
    card_done.setProperty("class", "stat-card")
    done_h = QHBoxLayout(card_done)
    done_h.setContentsMargins(16, 12, 16, 12)
    done_v = QVBoxLayout()
    done_v.setSpacing(2)
    lbl_done_title = QLabel("✓ Downloaded")
    lbl_done_title.setProperty("class", "metric-title")
    win.val_files = QLabel("0 files")
    win.val_files.setStyleSheet(
        "font-size: 19px; font-weight: 700; color: #10b981; background-color: transparent;"
    )
    win.val_data = QLabel("0 B saved to disk")
    win.val_data.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    done_v.addWidget(lbl_done_title)
    done_v.addWidget(win.val_files)
    done_v.addWidget(win.val_data)
    done_icon = QLabel("✅")
    done_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
    done_h.addLayout(done_v, 1)
    done_h.addWidget(done_icon)
    stats_row.addWidget(card_done, 0, 0)

    # Card B: Remaining
    card_rem = QFrame()
    card_rem.setProperty("class", "stat-card")
    rem_h = QHBoxLayout(card_rem)
    rem_h.setContentsMargins(16, 12, 16, 12)
    rem_v = QVBoxLayout()
    rem_v.setSpacing(2)
    lbl_rem_title = QLabel("⏳ Remaining")
    lbl_rem_title.setProperty("class", "metric-title")
    win.val_remaining_files = QLabel("0 files left")
    win.val_remaining_files.setStyleSheet(
        "font-size: 19px; font-weight: 700; color: #f59e0b; background-color: transparent;"
    )
    win.val_remaining_bytes = QLabel("0 B remaining")
    win.val_remaining_bytes.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    rem_v.addWidget(lbl_rem_title)
    rem_v.addWidget(win.val_remaining_files)
    rem_v.addWidget(win.val_remaining_bytes)
    rem_icon = QLabel("⏳")
    rem_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
    rem_h.addLayout(rem_v, 1)
    rem_h.addWidget(rem_icon)
    stats_row.addWidget(card_rem, 0, 1)

    # Card C: Speed & Time
    card_speed = QFrame()
    card_speed.setProperty("class", "stat-card")
    spd_h = QHBoxLayout(card_speed)
    spd_h.setContentsMargins(16, 12, 16, 12)
    spd_v = QVBoxLayout()
    spd_v.setSpacing(2)
    lbl_spd_title = QLabel("⚡ Speed & Time")
    lbl_spd_title.setProperty("class", "metric-title")
    win.val_speed = QLabel("0 B/s")
    win.val_speed.setProperty("class", "metric-value")
    time_eta_row = QHBoxLayout()
    time_eta_row.setContentsMargins(0, 0, 0, 0)
    time_eta_row.setSpacing(4)
    lbl_elapsed_prefix = QLabel("Elapsed")
    lbl_elapsed_prefix.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    win.val_time = QLabel("00:00")
    win.val_time.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 600; background-color: transparent;")
    win.val_eta = QLabel("")
    win.val_eta.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    time_eta_row.addWidget(lbl_elapsed_prefix)
    time_eta_row.addWidget(win.val_time)
    time_eta_row.addWidget(win.val_eta)
    time_eta_row.addStretch()
    spd_v.addWidget(lbl_spd_title)
    spd_v.addWidget(win.val_speed)
    spd_v.addLayout(time_eta_row)
    spd_icon = QLabel("🚀")
    spd_icon.setStyleSheet("font-size: 22px; background-color: transparent;")
    spd_h.addLayout(spd_v, 1)
    spd_h.addWidget(spd_icon)
    stats_row.addWidget(card_speed, 0, 2)

    step3_layout.addLayout(stats_row)

    # Row 2: Dual Clean Progress Card + Transfer Controls
    prog_box = QFrame()
    prog_box.setProperty("class", "card")
    prog_box_layout = QVBoxLayout(prog_box)
    prog_box_layout.setContentsMargins(18, 14, 18, 14)
    prog_box_layout.setSpacing(8)

    file_prog_header = QHBoxLayout()
    lbl_cur = QLabel("Current File:")
    lbl_cur.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b; background-color: transparent;")
    win.file_label = QLabel("Idle")
    win.file_label.setStyleSheet("font-size: 12px; font-weight: 600; background-color: transparent;")
    file_prog_header.addWidget(lbl_cur)
    file_prog_header.addWidget(win.file_label, 1)
    win.file_pct_label = QLabel("0%")
    win.file_pct_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #0ea5e9; background-color: transparent;")
    file_prog_header.addWidget(win.file_pct_label)
    prog_box_layout.addLayout(file_prog_header)

    win.file_progress = QProgressBar()
    win.file_progress.setRange(0, 100)
    win.file_progress.setValue(0)
    prog_box_layout.addWidget(win.file_progress)

    overall_prog_header = QHBoxLayout()
    lbl_all = QLabel("Overall Batch Progress:")
    lbl_all.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748b; background-color: transparent;")
    win.folder_label = QLabel("Idle")
    win.folder_label.setStyleSheet("font-size: 12px; color: #64748b; background-color: transparent;")
    overall_prog_header.addWidget(lbl_all)
    overall_prog_header.addWidget(win.folder_label, 1)
    win.overall_pct_label = QLabel("0%")
    win.overall_pct_label.setStyleSheet("font-size: 12px; font-weight: 700; color: #10b981; background-color: transparent;")
    overall_prog_header.addWidget(win.overall_pct_label)
    prog_box_layout.addLayout(overall_prog_header)

    win.overall_progress = QProgressBar()
    win.overall_progress.setProperty("class", "overall")
    win.overall_progress.setRange(0, 100)
    win.overall_progress.setValue(0)
    prog_box_layout.addWidget(win.overall_progress)

    controls_row = QHBoxLayout()
    controls_row.setSpacing(8)
    win.btn_back_to_files = QPushButton("← Back to File Selection")
    win.btn_back_to_files.setProperty("class", "ad-cta")
    win.btn_back_to_files.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_back_to_files.clicked.connect(lambda: win.go_to_step(1))
    controls_row.addWidget(win.btn_back_to_files)

    controls_row.addStretch()

    win.btn_step3_open_folder = QPushButton("📂 Open Folder")
    win.btn_step3_open_folder.setProperty("class", "btn-secondary")
    win.btn_step3_open_folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_step3_open_folder.clicked.connect(win.open_destination_folder)
    controls_row.addWidget(win.btn_step3_open_folder)

    win.pause_button = QPushButton("⏸  Pause Download")
    win.pause_button.setProperty("class", "btn-pause")
    win.pause_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.pause_button.setVisible(False)
    win.pause_button.clicked.connect(win.toggle_pause_download)
    controls_row.addWidget(win.pause_button)

    win.stop_button = QPushButton("⏹  Stop Download")
    win.stop_button.setProperty("class", "btn-stop")
    win.stop_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.stop_button.setVisible(False)
    win.stop_button.clicked.connect(win.stop_download)
    controls_row.addWidget(win.stop_button)

    prog_box_layout.addLayout(controls_row)
    step3_layout.addWidget(prog_box)

    # Row 3: Interactive Queue Filter Tabs (All / ✓ Downloaded / ⏳ Remaining)
    queue_card = QFrame()
    queue_card.setProperty("class", "card")
    queue_layout = QVBoxLayout(queue_card)
    queue_layout.setContentsMargins(18, 14, 18, 14)
    queue_layout.setSpacing(10)

    qtab_header = QHBoxLayout()
    qtab_header.setSpacing(8)

    win.btn_qtab_all = QPushButton("All Selected (0)")
    win.btn_qtab_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_qtab_all.clicked.connect(lambda: win.set_queue_filter("all"))

    win.btn_qtab_done = QPushButton("✓ Downloaded (0)")
    win.btn_qtab_done.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_qtab_done.clicked.connect(lambda: win.set_queue_filter("done"))

    win.btn_qtab_rem = QPushButton("⏳ Remaining / Up Next (0)")
    win.btn_qtab_rem.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    win.btn_qtab_rem.clicked.connect(lambda: win.set_queue_filter("rem"))

    qtab_header.addWidget(win.btn_qtab_all)
    qtab_header.addWidget(win.btn_qtab_done)
    qtab_header.addWidget(win.btn_qtab_rem)
    qtab_header.addStretch()

    win.lbl_integrity_badge = QLabel("SHA-256 Checksum Verified ✓")
    win.lbl_integrity_badge.setStyleSheet("font-size: 11px; color: #10b981; font-weight: 600; background-color: transparent;")
    qtab_header.addWidget(win.lbl_integrity_badge)
    queue_layout.addLayout(qtab_header)

    qtab_divider = QFrame()
    qtab_divider.setProperty("class", "divider-line")
    queue_layout.addWidget(qtab_divider)

    win.queue_tree = QTreeWidget()
    win.queue_tree.setHeaderLabels(["File", "Folder", "Status • Size"])
    win.queue_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    win.queue_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    win.queue_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    win.queue_tree.setRootIsDecorated(False)
    win.queue_tree.setMinimumHeight(165)
    win.queue_tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
    queue_layout.addWidget(win.queue_tree, 1)

    step3_layout.addWidget(queue_card, 1)

    step3_outer.addWidget(win.progress_card, 100)
    step3_outer.addStretch(1)
    return step3_page

