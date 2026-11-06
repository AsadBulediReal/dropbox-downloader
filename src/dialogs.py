from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont, QCursor, QColor, QKeyEvent, QMouseEvent, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QWidget,
    QFrame,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QGraphicsOpacityEffect,
)

from .styles import DARK_STYLESHEET


def _is_light_parent(parent: QWidget | None) -> bool:
    if parent is not None and hasattr(parent, "theme_mode"):
        return str(getattr(parent, "theme_mode", "light")).lower() == "light"
    return False


class ModernMessageBox(QDialog):
    """A sleek, modern modal dialog replacing native QMessageBox."""

    ICON_INFO = "info"
    ICON_WARNING = "warning"
    ICON_ERROR = "error"
    ICON_QUESTION = "question"
    ICON_SUCCESS = "success"

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        message: str,
        icon_type: str = "info",
        buttons: list[tuple[str, str, bool]] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setMaximumWidth(560)
        is_light = _is_light_parent(parent)
        dlg_bg = "#ffffff" if is_light else "#0c1322"
        dlg_border = "#cbd5e1" if is_light else "#1f2e45"
        title_fg = "#0f172a" if is_light else "#f8fafc"
        msg_fg = "#475569" if is_light else "#cbd5e1"
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                border: 1px solid {dlg_border};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(16)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        if is_light:
            badge_configs = {
                self.ICON_INFO: ("ℹ", "#eff6ff", "#0061ff", "#93c5fd"),
                self.ICON_SUCCESS: ("✓", "#ecfdf5", "#059669", "#6ee7b7"),
                self.ICON_WARNING: ("⚠", "#fffbeb", "#d97706", "#fcd34d"),
                self.ICON_ERROR: ("✕", "#fef2f2", "#dc2626", "#fca5a5"),
                self.ICON_QUESTION: ("?", "#eff6ff", "#2563eb", "#93c5fd"),
            }
        else:
            badge_configs = {
                self.ICON_INFO: ("ℹ", "#0c2646", "#38bdf8", "#0284c7"),
                self.ICON_SUCCESS: ("✓", "#064e3b", "#34d399", "#059669"),
                self.ICON_WARNING: ("⚠", "#451a03", "#fbbf24", "#d97706"),
                self.ICON_ERROR: ("✕", "#450a0a", "#f87171", "#b91c1c"),
                self.ICON_QUESTION: ("?", "#172554", "#60a5fa", "#2563eb"),
            }
        symbol, bg_col, text_col, border_col = badge_configs.get(
            icon_type, badge_configs[self.ICON_INFO]
        )

        icon_label = QLabel(symbol)
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(
            f"background-color: {bg_col}; color: {text_col}; border: 1px solid {border_col}; "
            f"border-radius: 20px; font-size: 18px; font-weight: 700;"
        )
        content_row.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {title_fg}; font-size: 14px; font-weight: 700; background-color: transparent;")
        text_layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_lbl.setStyleSheet(f"color: {msg_fg}; font-size: 12px; line-height: 1.45; background-color: transparent;")
        text_layout.addWidget(msg_lbl)

        content_row.addLayout(text_layout, stretch=1)
        layout.addLayout(content_row)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.selected_button_index = -1
        self._buttons = buttons or [("OK", "primary", True)]

        for idx, (btn_text, btn_role, is_default) in enumerate(self._buttons):
            btn = QPushButton(btn_text)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if btn_role == "primary":
                btn.setProperty("class", "btn-primary")
            elif btn_role == "danger":
                btn.setProperty("class", "btn-stop")
            else:
                btn.setProperty("class", "btn-secondary")

            if is_default:
                btn.setDefault(True)

            btn.clicked.connect(lambda checked=False, i=idx: self._on_btn_clicked(i))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _on_btn_clicked(self, index: int):
        self.selected_button_index = index
        self.accept()

    @classmethod
    def information(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_INFO, buttons=[("OK", "primary", True)])
        dlg.exec()

    @classmethod
    def warning(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_WARNING, buttons=[("OK", "primary", True)])
        dlg.exec()

    @classmethod
    def error(cls, parent: QWidget | None, title: str, message: str):
        dlg = cls(parent, title=title, message=message, icon_type=cls.ICON_ERROR, buttons=[("Close", "primary", True)])
        dlg.exec()

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        message: str,
        yes_text: str = "Yes",
        no_text: str = "No",
        is_destructive: bool = False,
    ) -> bool:
        role = "danger" if is_destructive else "primary"
        dlg = cls(
            parent,
            title=title,
            message=message,
            icon_type=cls.ICON_QUESTION if not is_destructive else cls.ICON_WARNING,
            buttons=[(no_text, "secondary", False), (yes_text, role, True)],
        )
        dlg.exec()
        return dlg.selected_button_index == 1


class ModernInputDialog(QDialog):
    """A sleek, modern modal input dialog replacing QInputDialog."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        heading: str,
        message: str = "",
        placeholder: str = "",
        default_text: str = "",
        is_password: bool = False,
        confirm_text: str = "Continue",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(640)
        is_light = _is_light_parent(parent)
        dlg_bg = "#ffffff" if is_light else "#0c1322"
        dlg_border = "#cbd5e1" if is_light else "#1f2e45"
        title_fg = "#0f172a" if is_light else "#f8fafc"
        box_bg = "#f8fafc" if is_light else "#111a2e"
        box_border = "#e2e8f0" if is_light else "#1e2d4a"
        msg_fg = "#475569" if is_light else "#cbd5e1"
        badge_bg = "#eff6ff" if is_light else "#0c2646"
        badge_fg = "#0061ff" if is_light else "#38bdf8"
        badge_bd = "#93c5fd" if is_light else "#0284c7"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                border: 1px solid {dlg_border};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon_char = "🔑" if "key" in title.lower() else "🌐"
        icon_badge = QLabel(icon_char)
        icon_badge.setFixedSize(38, 38)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_bd}; "
            "border-radius: 19px; font-size: 17px;"
        )
        header_row.addWidget(icon_badge)

        title_lbl = QLabel(heading)
        title_lbl.setStyleSheet(f"color: {title_fg}; font-size: 14px; font-weight: 700; background-color: transparent;")
        header_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(header_row)

        if message:
            msg_frame = QFrame()
            msg_frame.setStyleSheet(
                f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 10px; padding: 12px 14px;"
            )
            msg_layout = QVBoxLayout(msg_frame)
            msg_layout.setContentsMargins(0, 0, 0, 0)
            msg_layout.setSpacing(6)

            msg_lbl = QLabel(message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            msg_lbl.setStyleSheet(f"color: {msg_fg}; font-size: 12px; line-height: 1.5; background-color: transparent;")
            msg_layout.addWidget(msg_lbl)
            layout.addWidget(msg_frame)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setText(default_text)
        if is_password:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_field.returnPressed.connect(self.accept)
        layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setProperty("class", "btn-primary")
        btn_confirm.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)

    @classmethod
    def get_text(
        cls,
        parent: QWidget | None,
        title: str,
        heading: str,
        message: str = "",
        placeholder: str = "",
        default_text: str = "",
        is_password: bool = False,
        confirm_text: str = "Continue",
    ) -> tuple[str, bool]:
        dlg = cls(
            parent,
            title=title,
            heading=heading,
            message=message,
            placeholder=placeholder,
            default_text=default_text,
            is_password=is_password,
            confirm_text=confirm_text,
        )
        result = dlg.exec()
        return (dlg.input_field.text().strip(), result == QDialog.DialogCode.Accepted)


class ModernLoadingDialog(QDialog):
    """A sleek, modern modal loader dialog with an animated progress bar and spinner."""
    cancelled = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Signing In",
        heading: str = "Signing into Dropbox...",
        status: str = "Authenticating with Dropbox...",
        cancelable: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setMaximumWidth(540)
        self._is_light = _is_light_parent(parent)
        dlg_bg = "#ffffff" if self._is_light else "#0c1322"
        dlg_border = "#cbd5e1" if self._is_light else "#1f2e45"
        heading_fg = "#0f172a" if self._is_light else "#f8fafc"
        status_fg = "#64748b" if self._is_light else "#94a3b8"
        badge_bg = "#eff6ff" if self._is_light else "#0c2646"
        badge_fg = "#0061ff" if self._is_light else "#38bdf8"
        badge_bd = "#93c5fd" if self._is_light else "#0284c7"
        pbar_bg = "#f1f5f9" if self._is_light else "#090e1a"
        pbar_bd = "#e2e8f0" if self._is_light else "#1e293b"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                border: 1px solid {dlg_border};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(18)

        # Header with animated badge icon and heading
        header_row = QHBoxLayout()
        header_row.setSpacing(16)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.icon_badge = QLabel("⠋")
        self.icon_badge.setFixedSize(48, 48)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setStyleSheet(
            f"background-color: {badge_bg}; color: {badge_fg}; border: 1.5px solid {badge_bd}; "
            "border-radius: 24px; font-size: 22px; font-weight: bold;"
        )
        header_row.addWidget(self.icon_badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.heading_label = QLabel(heading)
        self.heading_label.setStyleSheet(f"color: {heading_fg}; font-size: 15px; font-weight: 700; background-color: transparent;")
        text_col.addWidget(self.heading_label)

        self.status_label = QLabel(status)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {status_fg}; font-size: 12px; line-height: 1.4; background-color: transparent;")
        text_col.addWidget(self.status_label)

        header_row.addLayout(text_col, stretch=1)
        layout.addLayout(header_row)

        # Animated gradient progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {pbar_bg};
                border: 1px solid {pbar_bd};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0061ff, stop:0.5 #38bdf8, stop:1 #6366f1);
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Cancel button row
        if cancelable:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            self.btn_cancel = QPushButton("Cancel")
            self.btn_cancel.setProperty("class", "btn-secondary")
            self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_cancel.setFixedHeight(32)
            self.btn_cancel.setMinimumWidth(88)
            self.btn_cancel.clicked.connect(self.on_cancel_clicked)
            btn_row.addWidget(self.btn_cancel)
            layout.addLayout(btn_row)

        # Spinner & progress animation
        self.auth_success: bool = False
        self.auth_data: dict[str, str] = {}
        self.auth_error: str = ""
        self.is_cancelled: bool = False

        self._current_val: float = 10.0
        self._target_val: float = 20.0
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_idx = 0
        self._tick_count = 0

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(25)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start()

    @Slot()
    def _on_anim_tick(self):
        self._tick_count += 1

        # Smooth forward-only advance towards target, never backwards
        if self._current_val < self._target_val:
            step = max(0.5, (self._target_val - self._current_val) * 0.15)
            self._current_val = min(self._current_val + step, self._target_val)
        elif self._current_val < 94.0:
            # Gentle forward crawl while awaiting network so the loader feels alive
            self._current_val += 0.08
            self._target_val = max(self._target_val, self._current_val)

        self.progress_bar.setValue(int(self._current_val))

        # Advance spinner frame every 4 ticks (~100ms)
        if self._tick_count % 4 == 0:
            self._frame_idx = (self._frame_idx + 1) % len(self._spinner_frames)
            self.icon_badge.setText(self._spinner_frames[self._frame_idx])

    @Slot(int)
    def set_progress(self, val: int):
        target = float(max(0, min(val, 100)))
        if target > self._target_val:
            self._target_val = target

    @Slot(str)
    def set_heading(self, text: str):
        self.heading_label.setText(text)

    @Slot(str)
    def set_status(self, text: str):
        self.status_label.setText(text)
        lower = text.lower()
        if "authoriz" in lower or "exchanging" in lower:
            self.set_progress(25)
        elif "connect" in lower or "api" in lower:
            self.set_progress(55)
        elif "profile" in lower or "account" in lower:
            self.set_progress(80)
        elif "complet" in lower or "finish" in lower:
            self.set_progress(95)

    @Slot(str, str, str, str)
    def on_auth_finished(self, access_token: str, refresh_token: str, user_name: str, user_email: str):
        self.auth_success = True
        self.auth_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_name": user_name,
            "user_email": user_email,
        }
        self._current_val = 100.0
        self._target_val = 100.0
        self.progress_bar.setValue(100)
        self.icon_badge.setText("✓")
        ok_bg = "#ecfdf5" if self._is_light else "#064e3b"
        ok_fg = "#059669" if self._is_light else "#34d399"
        self.icon_badge.setStyleSheet(
            f"background-color: {ok_bg}; color: {ok_fg}; border: 1.5px solid #059669; "
            "border-radius: 24px; font-size: 22px; font-weight: bold;"
        )
        self.heading_label.setText("Signed in successfully!")
        self.status_label.setText(f"Connected as {user_name}")
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setEnabled(False)
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        QTimer.singleShot(350, self.accept)

    @Slot(str)
    def on_auth_failed(self, err_msg: str):
        self.auth_error = err_msg
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.reject()

    @Slot()
    def on_cancel_clicked(self):
        self.is_cancelled = True
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.cancelled.emit()
        self.reject()

    def closeEvent(self, event):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().closeEvent(event)

    def accept(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().accept()

    def reject(self):
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        super().reject()


# ==============================================================================
# Custom Tree Widget with Multi-Selection & Shift-Range Support
# ==============================================================================
class FileTreeWidget(QTreeWidget):
    """
    Enhanced QTreeWidget supporting:
    - Extended multi-selection (Shift + Click, Ctrl + Click, Shift + Arrow keys)
    - Shift-click range selection & batch checking
    - Space key shortcut to toggle check states of selected items
    """
    shiftRangeRequested = Signal(object, object, bool)  # (anchor_item, target_item, is_checkbox)
    spacePressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._anchor_item: QTreeWidgetItem | None = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.spacePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        is_ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

        if (
            event.button() == Qt.MouseButton.LeftButton
            and is_shift
            and item is not None
            and self._anchor_item is not None
            and self._anchor_item != item
            and self._anchor_item.treeWidget() is self
        ):
            rect = self.visualItemRect(item)
            is_checkbox = (pos.x() <= (rect.x() + 24))
            self.shiftRangeRequested.emit(self._anchor_item, item, is_checkbox)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if not is_shift and not is_ctrl:
                if item is not None:
                    self._anchor_item = item
            elif is_ctrl and item is not None:
                self._anchor_item = item

        super().mousePressEvent(event)

    def clear(self):
        self._anchor_item = None
        super().clear()
