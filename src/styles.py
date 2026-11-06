"""
UI Stylesheet definitions for Dropbox Downloader GUI (Clean Light & Minimal Dark Themes).
"""

from pathlib import Path

from .styles_light_layout import LIGHT_LAYOUT_QSS
from .styles_light_widgets import LIGHT_WIDGETS_QSS
from .styles_dark_layout import DARK_LAYOUT_QSS
from .styles_dark_widgets import DARK_WIDGETS_QSS

_CHECKMARK_SVG = (Path(__file__).resolve().parent / "checkmark.svg").as_posix()

LIGHT_STYLESHEET = (LIGHT_LAYOUT_QSS + LIGHT_WIDGETS_QSS).replace("__CHECKMARK_SVG__", _CHECKMARK_SVG)
DARK_STYLESHEET = (DARK_LAYOUT_QSS + DARK_WIDGETS_QSS).replace("__CHECKMARK_SVG__", _CHECKMARK_SVG)


def get_theme_stylesheet(theme: str = "light") -> str:
    """Return the Qt stylesheet for 'light' or 'dark' theme mode."""
    return DARK_STYLESHEET if str(theme).strip().lower() == "dark" else LIGHT_STYLESHEET
