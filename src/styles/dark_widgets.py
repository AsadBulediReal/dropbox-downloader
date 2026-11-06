DARK_WIDGETS_QSS = """QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #0b1120;
    border: 1px solid #334155;
    color: #cbd5e1;
    border-radius: 11px;
}
QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #1e293b;
    border-color: #475569;
    color: #ffffff;
}
QPushButton.btn-ghost, QPushButton[class="btn-ghost"] {
    background-color: transparent;
    border: none;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 8px;
}
QPushButton.btn-ghost:hover, QPushButton[class="btn-ghost"]:hover {
    background-color: #0b1120;
    color: #f8fafc;
}
QPushButton.btn-ghost:disabled, QPushButton[class="btn-ghost"]:disabled {
    background-color: transparent;
    border: none;
    color: #475569;
}
QPushButton.btn-load-folders, QPushButton[class="btn-load-folders"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 9px 22px;
    border-radius: 12px;
}
QPushButton.btn-load-folders:hover, QPushButton[class="btn-load-folders"]:hover {
    background-color: #0284c7;
    border-color: #7dd3fc;
}
QPushButton.btn-load-folders:pressed, QPushButton[class="btn-load-folders"]:pressed {
    background-color: #0369a1;
}
QPushButton.btn-load-folders:disabled, QPushButton[class="btn-load-folders"]:disabled {
    background-color: #0b1c2e;
    border: 1px solid #162a42;
    color: #3b5270;
}
QPushButton.btn-start, QPushButton[class="btn-start"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 11px;
}
QPushButton.btn-start:hover, QPushButton[class="btn-start"]:hover {
    background-color: #0284c7;
    border-color: #7dd3fc;
}
QPushButton.btn-start:disabled, QPushButton[class="btn-start"]:disabled {
    background-color: #0d131f;
    border: 1px solid #1e293b;
    color: #475569;
}
QPushButton.btn-stop, QPushButton[class="btn-stop"] {
    background-color: #2d1215;
    border: 1px solid #7f1d1d;
    color: #f87171;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-stop:hover, QPushButton[class="btn-stop"]:hover {
    background-color: #dc2626;
    border-color: #ef4444;
    color: #ffffff;
}
QPushButton.btn-pause, QPushButton[class="btn-pause"] {
    background-color: #2e1d09;
    border: 1px solid #78350f;
    color: #fbbf24;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 10px;
}
QPushButton.btn-pause:hover, QPushButton[class="btn-pause"]:hover {
    background-color: #d97706;
    border-color: #f59e0b;
    color: #ffffff;
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
    background-color: #0b1120;
    border: 1px solid #334155;
    border-radius: 10px;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton.qtab-btn:hover, QPushButton[class="qtab-btn"]:hover {
    background-color: #1e293b;
    color: #f8fafc;
}
QPushButton.qtab-btn-active, QPushButton[class="qtab-btn-active"] {
    background-color: #0ea5e9;
    border: 1px solid #38bdf8;
    border-radius: 10px;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
}
QPushButton.recent-chip, QPushButton[class="recent-chip"] {
    background-color: #0b1120;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    color: #cbd5e1;
    font-weight: 600;
}
QPushButton.recent-chip:hover, QPushButton[class="recent-chip"]:hover {
    background-color: #1e293b;
    border-color: #38bdf8;
    color: #ffffff;
}
QFrame.recent-row, QFrame[class="recent-row"] {
    background-color: transparent;
    border: none;
    border-top: 1px solid #1e293b;
    border-radius: 8px;
}
QFrame.recent-row[first="true"], QFrame[class="recent-row"][first="true"] {
    border-top: none;
}
QFrame.recent-row:hover, QFrame[class="recent-row"]:hover {
    background-color: #0b1120;
}
QLabel.recent-row-title, QLabel[class="recent-row-title"] {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 600;
    background-color: transparent;
}
QLabel.recent-row-url, QLabel[class="recent-row-url"] {
    color: #94a3b8;
    font-size: 12px;
    background-color: transparent;
}
QLabel.recent-row-open, QLabel[class="recent-row-open"] {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 600;
    background-color: transparent;
}
QFrame.divider-line, QFrame[class="divider-line"] {
    background-color: #1e293b;
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
    background-color: #172554;
    border: 1px solid #3b82f6;
    border-radius: 12px;
}
QLabel.ad-badge, QLabel[class="ad-badge"] {
    background-color: #1e3a8a;
    color: #93c5fd;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel.ad-text, QLabel[class="ad-text"] {
    color: #f1f5f9;
    font-size: 12px;
    background-color: transparent;
}
QPushButton.ad-cta, QPushButton[class="ad-cta"] {
    background-color: transparent;
    border: none;
    color: #60a5fa;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 8px;
}
QPushButton.ad-cta:hover, QPushButton[class="ad-cta"]:hover {
    color: #93c5fd;
    text-decoration: underline;
}
QMenu {
    background-color: #0c1322;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 6px;
    color: #f1f5f9;
}
QMenu::item {
    padding: 8px 18px 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: #cbd5e1;
}
QMenu::item:selected {
    background-color: #1e293b;
    color: #38bdf8;
}
QMenu::separator {
    height: 1px;
    background-color: #334155;
    margin: 4px 6px;
}
QProgressBar {
    background-color: #0b1120;
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
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 12px;
    color: #f1f5f9;
    font-size: 13px;
    padding: 4px;
}
QTreeWidget:disabled {
    background-color: #080d18;
    color: #475569;
    border: 1px solid #141c2b;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 6px;
}
QTreeWidget::item:hover {
    background-color: #141e30;
}
QTreeWidget::item:selected {
    background-color: #163b6b;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-size: 11px;
    font-weight: 700;
}
QPlainTextEdit {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #94a3b8;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
    padding: 8px 10px;
}
QCheckBox {
    color: #f8fafc;
    font-size: 12px;
    spacing: 10px;
}
QCheckBox:disabled {
    color: #475569;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #0b1120;
}
QCheckBox::indicator:checked {
    background-color: #0ea5e9;
    border-color: #38bdf8;
    image: url("__CHECKMARK_SVG__");
}
QCheckBox::indicator:checked:disabled {
    background-color: #1e3a5f;
    border-color: #1e3a5f;
    image: url("__CHECKMARK_SVG__");
}
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

