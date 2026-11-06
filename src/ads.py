"""
Lightweight Native / Banner Ad System for Dropbox Downloader Public Release.

Supports:
- Curated built-in fallback sponsor/affiliate slots (zero offline breakage).
- Optional remote JSON feed via `DROPBOX_AD_FEED_URL` environment variable
  so live sponsors and affiliate campaigns can be updated remotely without
  rebuilding the desktop executable.
- Automatic timed rotation and safe browser click-through handling.
"""

import os
import webbrowser
from typing import Any
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


DEFAULT_ADS: list[dict[str, str]] = [
    {
        "badge": "Sponsored",
        "title": "pCloud 2TB Lifetime Storage",
        "description": "Save 65% on encrypted cloud storage. One payment, forever.",
        "cta": "Claim Offer →",
        "url": "https://www.pcloud.com/",
    },
    {
        "badge": "Partner",
        "title": "NordVPN Threat Protection Pro",
        "description": "Fast, encrypted large-file transfers on any network.",
        "cta": "Get Deal →",
        "url": "https://nordvpn.com/",
    },
    {
        "badge": "Sponsored",
        "title": "Backblaze Unlimited PC Backup",
        "description": "Automatically back up every downloaded folder without size limits.",
        "cta": "Try Free →",
        "url": "https://www.backblaze.com/",
    },
]


def is_safe_http_url(url: str) -> bool:
    """Validate that a target ad URL uses standard http/https schemes."""
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def sanitize_ad_entries(raw_items: Any) -> list[dict[str, str]]:
    """Validate and normalize remote or custom ad JSON entries."""
    if not isinstance(raw_items, list):
        return []

    valid: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not is_safe_http_url(url):
            continue
        badge = str(item.get("badge") or "Sponsored").strip()[:20]
        cta = str(item.get("cta") or "Learn More →").strip()[:28]
        valid.append(
            {
                "badge": badge,
                "title": title[:90],
                "description": description[:160],
                "cta": cta,
                "url": url,
            }
        )
    return valid


class AdFeedWorker(QObject):
    """Background worker to fetch live ad slots from a remote JSON endpoint."""

    ads_loaded = Signal(list)
    finished = Signal()

    def __init__(self, feed_url: str):
        super().__init__()
        self.feed_url = feed_url.strip()

    @Slot()
    def run(self):
        try:
            if is_safe_http_url(self.feed_url):
                resp = requests.get(self.feed_url, timeout=4)
                if resp.status_code == 200:
                    payload = resp.json()
                    items = payload.get("ads") if isinstance(payload, dict) else payload
                    cleaned = sanitize_ad_entries(items)
                    if cleaned:
                        self.ads_loaded.emit(cleaned)
        except Exception:
            pass
        finally:
            self.finished.emit()


class AdBannerWidget(QFrame):
    """Persistent, unobtrusive bottom sponsor banner widget."""

    def __init__(self, parent: QWidget | None = None, ads: list[dict[str, str]] | None = None):
        super().__init__(parent)
        self.setProperty("class", "ad-banner")
        self._ads: list[dict[str, str]] = list(ads) if ads else list(DEFAULT_ADS)
        self._current_index: int = 0
        self._feed_thread: QThread | None = None
        self._feed_worker: AdFeedWorker | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(12)

        self.badge_label = QLabel("Sponsored")
        self.badge_label.setProperty("class", "ad-badge")
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge_label)

        self.text_label = QLabel()
        self.text_label.setProperty("class", "ad-text")
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.text_label, 1)

        self.cta_button = QPushButton("Claim Offer →")
        self.cta_button.setProperty("class", "ad-cta")
        self.cta_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cta_button.clicked.connect(self.open_current_ad)
        layout.addWidget(self.cta_button)

        self.rotation_timer = QTimer(self)
        self.rotation_timer.setInterval(45000)
        self.rotation_timer.timeout.connect(self.next_ad)
        if len(self._ads) > 1:
            self.rotation_timer.start()

        self._render_current_ad()

        feed_url = os.getenv("DROPBOX_AD_FEED_URL", "").strip()
        if feed_url and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QTimer.singleShot(600, lambda: self.fetch_remote_ads(feed_url))

    @property
    def current_ad(self) -> dict[str, str]:
        if not self._ads:
            return DEFAULT_ADS[0]
        return self._ads[self._current_index % len(self._ads)]

    def set_ads(self, ads: list[dict[str, str]]):
        cleaned = sanitize_ad_entries(ads)
        if cleaned:
            self._ads = cleaned
            self._current_index = 0
            self._render_current_ad()
            if len(self._ads) > 1 and not self.rotation_timer.isActive():
                self.rotation_timer.start()

    def next_ad(self):
        if len(self._ads) > 1:
            self._current_index = (self._current_index + 1) % len(self._ads)
            self._render_current_ad()

    def _render_current_ad(self):
        ad = self.current_ad
        self.badge_label.setText(ad.get("badge", "Sponsored"))
        title = ad.get("title", "")
        desc = ad.get("description", "")
        if desc:
            self.text_label.setText(f"<b>{title}</b> — {desc}")
        else:
            self.text_label.setText(f"<b>{title}</b>")
        self.cta_button.setText(ad.get("cta", "Learn More →"))
        self.cta_button.setToolTip(f"Open sponsor offer: {ad.get('url', '')}")

    def open_current_ad(self):
        url = self.current_ad.get("url", "")
        if is_safe_http_url(url):
            webbrowser.open(url)

    def fetch_remote_ads(self, feed_url: str):
        if not is_safe_http_url(feed_url):
            return
        self.cleanup_feed_thread()
        t = QThread()
        w = AdFeedWorker(feed_url)
        w.moveToThread(t)
        w.ads_loaded.connect(self.set_ads)
        w.finished.connect(t.quit, Qt.ConnectionType.DirectConnection)
        t.finished.connect(w.deleteLater)
        t.finished.connect(t.deleteLater)

        def _clear_refs():
            self._feed_thread = None
            self._feed_worker = None

        t.finished.connect(_clear_refs)
        self._feed_thread = t
        self._feed_worker = w
        t.started.connect(w.run)
        t.start()

    def cleanup_feed_thread(self):
        if self._feed_thread is not None:
            try:
                if self._feed_thread.isRunning():
                    self._feed_thread.quit()
                    self._feed_thread.wait(150)
            except Exception:
                pass
            self._feed_thread = None
            self._feed_worker = None

