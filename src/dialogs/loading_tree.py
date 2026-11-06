from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QFont, QCursor, QColor, QKeyEvent, QMouseEvent, QPainter, QBrush, QPen
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QWidget,
    QFrame,
    QTreeWidget,
    QTreeWidgetItem,
    QGraphicsOpacityEffect,
)

from ..styles import DARK_STYLESHEET


def _is_light_parent(parent: QWidget | None) -> bool:
    if parent is not None and hasattr(parent, "theme_mode"):
        return str(getattr(parent, "theme_mode", "light")).lower() == "light"
    return False

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
