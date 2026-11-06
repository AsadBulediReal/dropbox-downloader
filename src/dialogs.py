from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QFrame,
)

from .dialogs_loading_tree import _is_light_parent, ModernLoadingDialog, FileTreeWidget


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
        title_lbl.setStyleSheet(
            f"color: {title_fg}; font-size: 14px; font-weight: 700; background-color: transparent;"
        )
        text_layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_lbl.setStyleSheet(
            f"color: {msg_fg}; font-size: 12px; line-height: 1.45; background-color: transparent;"
        )
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
        title_lbl.setStyleSheet(
            f"color: {title_fg}; font-size: 14px; font-weight: 700; background-color: transparent;"
        )
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
            msg_lbl.setStyleSheet(
                f"color: {msg_fg}; font-size: 12px; line-height: 1.5; background-color: transparent;"
            )
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
