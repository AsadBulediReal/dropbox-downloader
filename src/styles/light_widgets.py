LIGHT_WIDGETS_QSS = """QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #334155;
    border-radius: 11px;
}
QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}
QPushButton.btn-ghost, QPushButton[class="btn-ghost"] {
    background-color: transparent;
    border: none;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton.btn-ghost:hover, QPushButton[class="btn-ghost"]:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QPushButton.btn-ghost:disabled, QPushButton[class="btn-ghost"]:disabled {
    background-color: transparent;
    border: none;
    color: #94a3b8;
}
QPushButton.btn-load-folders, QPushButton[class="btn-load-folders"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 9px 22px;
    border-radius: 12px;
}
QPushButton.btn-load-folders:hover, QPushButton[class="btn-load-folders"]:hover {
    background-color: #0052d9;
    border-color: #0052d9;
}
QPushButton.btn-load-folders:pressed, QPushButton[class="btn-load-folders"]:pressed {
    background-color: #0043b3;
}
QPushButton.btn-load-folders:disabled, QPushButton[class="btn-load-folders"]:disabled {
    background-color: #dbeafe;
    border: 1px solid #bfdbfe;
    color: #93c5fd;
}
QPushButton.btn-start, QPushButton[class="btn-start"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 11px;
}
QPushButton.btn-start:hover, QPushButton[class="btn-start"]:hover {
    background-color: #0052d9;
    border-color: #0052d9;
}
QPushButton.btn-start:disabled, QPushButton[class="btn-start"]:disabled {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    color: #94a3b8;
}
QPushButton.btn-stop, QPushButton[class="btn-stop"] {
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    color: #dc2626;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-stop:hover, QPushButton[class="btn-stop"]:hover {
    background-color: #dc2626;
    border-color: #dc2626;
    color: #ffffff;
}
QPushButton.btn-pause, QPushButton[class="btn-pause"] {
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    color: #b45309;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-pause:hover, QPushButton[class="btn-pause"]:hover {
    background-color: #fef3c7;
    border-color: #f59e0b;
}
QPushButton.btn-resume, QPushButton[class="btn-resume"] {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-resume:hover, QPushButton[class="btn-resume"]:hover {
    background-color: #047857;
}
QPushButton.qtab-btn, QPushButton[class="qtab-btn"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton.qtab-btn:hover, QPushButton[class="qtab-btn"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}
QPushButton.qtab-btn-active, QPushButton[class="qtab-btn-active"] {
    background-color: #0061ff;
    border: 1px solid #0061ff;
    border-radius: 10px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
}
QPushButton.recent-chip, QPushButton[class="recent-chip"] {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    color: #334155;
    font-weight: 600;
}
QPushButton.recent-chip:hover, QPushButton[class="recent-chip"]:hover {
    background-color: #eff6ff;
    border-color: #93c5fd;
    color: #0061ff;
}
QFrame.recent-row, QFrame[class="recent-row"] {
    background-color: transparent;
    border: none;
    border-top: 1px solid #f1f5f9;
    border-radius: 8px;
}
QFrame.recent-row[first="true"], QFrame[class="recent-row"][first="true"] {
    border-top: none;
}
QFrame.recent-row:hover, QFrame[class="recent-row"]:hover {
    background-color: #f8fafc;
}
QLabel.recent-row-title, QLabel[class="recent-row-title"] {
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
    background-color: transparent;
}
QLabel.recent-row-url, QLabel[class="recent-row-url"] {
    color: #64748b;
    font-size: 12px;
    background-color: transparent;
}
QLabel.recent-row-open, QLabel[class="recent-row-open"] {
    color: #0061ff;
    font-size: 12px;
    font-weight: 600;
    background-color: transparent;
}
QFrame.divider-line, QFrame[class="divider-line"] {
    background-color: #e2e8f0;
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QFrame.card QTreeWidget, QFrame[class="card"] QTreeWidget {
    background-color: transparent;
    border: none;
    padding: 0px;
}
QFrame.ad-banner, QFrame[class="ad-banner"] {
    background-color: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 12px;
}
QLabel.ad-badge, QLabel[class="ad-badge"] {
    background-color: #dbeafe;
    color: #1d4ed8;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel.ad-text, QLabel[class="ad-text"] {
    color: #1e293b;
    font-size: 12px;
    background-color: transparent;
}
QPushButton.ad-cta, QPushButton[class="ad-cta"] {
    background-color: transparent;
    border: none;
    color: #0061ff;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 8px;
}
QPushButton.ad-cta:hover, QPushButton[class="ad-cta"]:hover {
    color: #0043b3;
    text-decoration: underline;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px;
    color: #0f172a;
}
QMenu::item {
    padding: 8px 18px 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #334155;
}
QMenu::item:selected {
    background-color: #eff6ff;
    color: #0061ff;
}
QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 6px;
}
QProgressBar {
    background-color: #f1f5f9;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: transparent;
    font-size: 10px;
    height: 9px;
}
QProgressBar::chunk {
    background-color: #0ea5e9;
    border-radius: 5px;
}
QProgressBar.overall::chunk, QProgressBar[class="overall"]::chunk {
    background-color: #10b981;
    border-radius: 5px;
}
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #0f172a;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background-color: #f1f5f9;
}
QTreeWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-size: 11px;
    font-weight: 700;
}
QPlainTextEdit {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #475569;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    padding: 8px 10px;
}
QCheckBox {
    color: #0f172a;
    font-size: 12px;
    spacing: 10px;
}
QCheckBox:disabled {
    color: #94a3b8;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #0061ff;
    border-color: #0061ff;
    image: url("__CHECKMARK_SVG__");
}
QCheckBox::indicator:checked:disabled {
    background-color: #93c5fd;
    border-color: #93c5fd;
    image: url("__CHECKMARK_SVG__");
}
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

