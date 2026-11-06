import re

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QFrame

from .styles import get_theme_stylesheet


class _ClickBackdrop(QFrame):
    """Semi-transparent click-catcher backdrop for the slide-over Settings drawer."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(15, 23, 42, 125); border: none;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class _RecentLinkRow(QFrame):
    """Clickable two-line recent folder row matching the Guided Wizard design."""

    clicked = Signal()

    def __init__(self, title_text: str, url_text: str, show_top_border: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("class", "recent-row")
        if not show_top_border:
            self.setProperty("first", "true")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(8, 9, 8, 9)
        row_layout.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        lbl_title = QLabel(title_text)
        lbl_title.setProperty("class", "recent-row-title")
        lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        lbl_url = QLabel(url_text)
        lbl_url.setProperty("class", "recent-row-url")
        lbl_url.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        text_col.addWidget(lbl_title)
        text_col.addWidget(lbl_url)
        row_layout.addLayout(text_col, 1)

        lbl_open = QLabel("Open →")
        lbl_open.setProperty("class", "recent-row-open")
        lbl_open.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_open.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row_layout.addWidget(lbl_open, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class _ThemeBadgesMixin:
    def _repolish(self, widget: QWidget | None):
        if widget is None:
            return
        st = widget.style()
        if st is not None:
            st.unpolish(widget)
            st.polish(widget)
        widget.update()

    def apply_theme(self, mode: str, save: bool = True):
        self.theme_mode = "dark" if str(mode).strip().lower() == "dark" else "light"
        self.setStyleSheet(get_theme_stylesheet(self.theme_mode))
        if hasattr(self, "btn_theme_toggle"):
            self.btn_theme_toggle.setText("🌗  Switch Light / Dark Mode")

        # Re-apply dynamic badges & colors
        if hasattr(self, "auth_badge"):
            self.set_auth_badge(
                self.auth_badge.text() or ("● Connected" if self.is_logged_in() else "○ Not Logged In"),
                "connected" if self.is_logged_in() else "neutral",
            )
        if hasattr(self, "status_badge"):
            self.set_status_badge(
                self.status_badge.text() or "● Ready",
                getattr(self, "_last_status_state", "ready"),
            )
        if hasattr(self, "transfer_notice_banner"):
            self._apply_transfer_notice_style()
        self._refresh_all_queue_item_styles()
        if save:
            self.settings.setValue("theme_mode", self.theme_mode)
            self.settings.sync()

    def toggle_theme(self):
        next_mode = "dark" if self.theme_mode == "light" else "light"
        self.apply_theme(next_mode, save=True)

    def set_status_badge(self, text: str, state: str = "ready"):
        self._last_status_state = state
        if not hasattr(self, "status_badge"):
            return
        is_light = self.theme_mode == "light"
        if is_light:
            styles = {
                "ready": "background-color: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd;",
                "running": "background-color: #eff6ff; color: #0061ff; border: 1px solid #93c5fd;",
                "verifying": "background-color: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe;",
                "success": "background-color: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;",
                "warning": "background-color: #fffbeb; color: #d97706; border: 1px solid #fde68a;",
                "error": "background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca;",
                "neutral": "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;",
            }
        else:
            styles = {
                "ready": "background-color: #1e293b; color: #38bdf8; border: 1px solid #334155;",
                "running": "background-color: #0c2e59; color: #60a5fa; border: 1px solid #1d4ed8;",
                "verifying": "background-color: #2e1065; color: #c084fc; border: 1px solid #7e22ce;",
                "success": "background-color: #064e3b; color: #34d399; border: 1px solid #059669;",
                "warning": "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706;",
                "error": "background-color: #450a0a; color: #f87171; border: 1px solid #b91c1c;",
                "neutral": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;",
            }
        style_str = styles.get(state, styles["ready"])
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(
            f"{style_str} border-radius: 11px; padding: 3px 11px; font-weight: 600; font-size: 11px;"
        )

    def set_auth_badge(self, text: str, state: str = "neutral"):
        if not hasattr(self, "auth_badge"):
            return
        is_light = self.theme_mode == "light"
        if is_light:
            styles = {
                "connected": "background-color: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;",
                "neutral": "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;",
            }
        else:
            styles = {
                "connected": "background-color: #064e3b; color: #34d399; border: 1px solid #059669;",
                "neutral": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155;",
            }
        style_str = styles.get(state, styles["neutral"])
        self.auth_badge.setText(text)
        self.auth_badge.setStyleSheet(
            f"{style_str} border-radius: 11px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )

    def set_selection_summary(self, text: str, state: str = "neutral"):
        is_light = self.theme_mode == "light"
        if is_light:
            colors = {
                "neutral": ("#f1f5f9", "#64748b"),
                "active": ("#eff6ff", "#0061ff"),
                "success": ("#ecfdf5", "#059669"),
                "error": ("#fef2f2", "#dc2626"),
            }
        else:
            colors = {
                "neutral": ("#0b1120", "#94a3b8"),
                "active": ("#0c2e59", "#38bdf8"),
                "success": ("#064e3b", "#34d399"),
                "error": ("#450a0a", "#f87171"),
            }
        bg, fg = colors.get(state, colors["neutral"])
        self.selection_summary_label.setText(text)
        self.selection_summary_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )

    def _apply_transfer_notice_style(self, state: str | None = None):
        if state is not None:
            self._transfer_notice_state = state
        cur_state = getattr(self, "_transfer_notice_state", "success")
        if not hasattr(self, "transfer_notice_banner"):
            return
        is_light = self.theme_mode == "light"
        if is_light:
            themes = {
                "success": ("#ecfdf5", "#a7f3d0", "#d1fae5", "#059669", "#6ee7b7", "#065f46", "#047857"),
                "warning": ("#fffbeb", "#fde68a", "#fef3c7", "#d97706", "#fcd34d", "#92400e", "#b45309"),
                "neutral": ("#f1f5f9", "#cbd5e1", "#e2e8f0", "#475569", "#cbd5e1", "#0f172a", "#475569"),
            }
        else:
            themes = {
                "success": ("#064e3b", "#059669", "#065f46", "#34d399", "#10b981", "#ecfdf5", "#a7f3d0"),
                "warning": ("#451a03", "#d97706", "#78350f", "#fbbf24", "#f59e0b", "#fef3c7", "#fde68a"),
                "neutral": ("#1e293b", "#334155", "#0f172a", "#94a3b8", "#334155", "#f8fafc", "#cbd5e1"),
            }
        bg, bd, icon_bg, icon_fg, icon_bd, title_fg, detail_fg = themes.get(cur_state, themes["success"])
        self.transfer_notice_banner.setStyleSheet(
            f"QFrame#transferNoticeBanner {{ background-color: {bg}; border: 1px solid {bd}; border-radius: 14px; }}"
        )
        self.transfer_notice_icon.setStyleSheet(
            f"background-color: {icon_bg}; color: {icon_fg}; border: 1px solid {icon_bd}; "
            "border-radius: 17px; font-size: 15px; font-weight: 700;"
        )
        self.transfer_notice_title.setStyleSheet(
            f"color: {title_fg}; font-size: 13px; font-weight: 700; background-color: transparent;"
        )
        self.transfer_notice_detail.setStyleSheet(
            f"color: {detail_fg}; font-size: 12px; background-color: transparent;"
        )

    def show_transfer_notice(self, default_title: str, message: str, state: str = "success"):
        if not hasattr(self, "transfer_notice_banner"):
            return
        lines = [ln.strip() for ln in (message or "").strip().splitlines() if ln.strip()]
        if len(lines) > 1:
            heading = re.sub(r"^[✓✔⚠⚠️⏹\ufe0f]+\s*", "", lines[0]).strip() or default_title
            detail_parts = []
            for ln in lines[1:]:
                if ln.startswith("Output Directory:"):
                    out_path = ln.split(":", 1)[1].strip()
                    short_out = out_path if len(out_path) <= 46 else ("…" + out_path[-44:])
                    detail_parts.append(f"Saved to: {short_out}")
                else:
                    detail_parts.append(ln)
            detail = "  •  ".join(detail_parts)
        elif len(lines) == 1:
            heading = default_title
            detail = lines[0]
        else:
            heading = default_title
            detail = ""

        icons = {"success": "✓", "warning": "⚠", "neutral": "⏹"}
        self.transfer_notice_icon.setText(icons.get(state, "✓"))
        self.transfer_notice_title.setText(heading)
        self.transfer_notice_detail.setText(detail)
        self.transfer_notice_detail.setVisible(bool(detail))
        self.transfer_notice_banner.setToolTip((message or "").strip())
        self._apply_transfer_notice_style(state)
        self.transfer_notice_banner.setVisible(True)

    def hide_transfer_notice(self):
        if hasattr(self, "transfer_notice_banner"):
            self.transfer_notice_banner.setVisible(False)

