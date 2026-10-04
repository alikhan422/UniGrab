import os
import re
import yt_dlp
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from ui.styles import MODERN_NEON_DARK_THEME

class QuickInfoWorker(QThread):
    info_fetched = pyqtSignal(dict)
    fetch_failed = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': True,       # Super fast playlist & video metadata
            'socket_timeout': 5,
            'extractor_args': {
                'youtube': {'player_client': ['android']}
            }
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                self.info_fetched.emit(info or {})
        except Exception:
            try:
                # Fast fallback without extra clients
                opts['extract_flat'] = 'in_playlist'
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                    self.info_fetched.emit(info or {})
            except Exception as e:
                self.fetch_failed.emit(str(e))

class PreDownloadDialog(QDialog):
    def __init__(self, parent=None, default_url=""):
        super().__init__(parent)
        self.setWindowTitle("Configure Job — UniGrab Studio")
        self.resize(520, 420)
        self.setStyleSheet(MODERN_NEON_DARK_THEME)

        self.fetch_worker = None
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(400)
        self.debounce_timer.timeout.connect(self._trigger_fast_fetch)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Media URL
        layout.addWidget(QLabel("Media URL / Direct Link:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        self.url_input.textChanged.connect(self._on_url_input_changed)
        layout.addWidget(self.url_input)

        # Status text
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #10B981; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # 2. Playlist Selection
        layout.addWidget(QLabel("Playlist Selection (Optional — e.g. 1-5, 1-10, or 1,6,2,9):"))
        self.playlist_input = QLineEdit()
        self.playlist_input.setPlaceholderText("Leave empty for all videos, or specify: 1-5, 8, 11-15")
        layout.addWidget(self.playlist_input)

        # 3. Save Title
        layout.addWidget(QLabel("Save Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter or auto-fetching title...")
        layout.addWidget(self.title_input)

        # 4. Format & Resolution
        row_fmt = QHBoxLayout()
        vbox_fmt = QVBoxLayout()
        vbox_fmt.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "MKV", "MP3", "M4A", "AUTO"])
        vbox_fmt.addWidget(self.format_combo)

        vbox_res = QVBoxLayout()
        vbox_res.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Source Best", "1080p", "720p", "480p", "360p"])
        vbox_res.addWidget(self.resolution_combo)

        row_fmt.addLayout(vbox_fmt)
        row_fmt.addLayout(vbox_res)
        layout.addLayout(row_fmt)

        # 5. Save Location
        layout.addWidget(QLabel("Save Location:"))
        dest_row = QHBoxLayout()
        self.dest_input = QLineEdit()
        default_dir = os.path.normpath(os.path.expanduser("~/Downloads"))
        self.dest_input.setText(default_dir)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_folder)
        dest_row.addWidget(self.dest_input)
        dest_row.addWidget(btn_browse)
        layout.addLayout(dest_row)

        layout.addStretch()

        # 6. Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_start = QPushButton("Start Download")
        self.btn_start.setObjectName("btnNew")
        self.btn_start.clicked.connect(self.accept)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_start)
        layout.addLayout(btn_row)

        if default_url:
            self.url_input.setText(default_url)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Location", self.dest_input.text())
        if folder:
            self.dest_input.setText(os.path.normpath(folder))

    def _on_url_input_changed(self):
        self.debounce_timer.start()

    def _trigger_fast_fetch(self):
        url = self.url_input.text().strip()
        if url.startswith("http://") or url.startswith("https://"):
            self.lbl_status.setText("Fetching...")
            if self.fetch_worker and self.fetch_worker.isRunning():
                self.fetch_worker.terminate()
            self.fetch_worker = QuickInfoWorker(url)
            self.fetch_worker.info_fetched.connect(self._on_info_fetched)
            self.fetch_worker.fetch_failed.connect(self._on_fetch_failed)
            self.fetch_worker.start()

    def _on_info_fetched(self, info):
        self.lbl_status.setText("Ready")
        title = info.get("title") or ""
        # Check if playlist
        if not title and "entries" in info and info["entries"]:
            title = info.get("playlist_title") or info["entries"][0].get("title", "")
        if title:
            self.title_input.setText(title)

    def _on_fetch_failed(self, err):
        self.lbl_status.setText("Done (Default naming)")

    def get_configuration(self):
        url = self.url_input.text().strip()
        playlist = self.playlist_input.text().strip()
        raw_title = self.title_input.text().strip() or "download"
        base_dest = self.dest_input.text().strip() or os.path.expanduser("~/Downloads")

        safe_folder = "".join(c for c in raw_title if c not in r'\/:*?"<>|').strip()
        final_dest = os.path.normpath(os.path.join(base_dest, safe_folder)) if safe_folder else os.path.normpath(base_dest)
        try:
            os.makedirs(final_dest, exist_ok=True)
        except Exception:
            final_dest = base_dest

        return {
            "url": url,
            "playlist_items": playlist,
            "title": raw_title,
            "format": self.format_combo.currentText().lower(),
            "resolution": self.resolution_combo.currentText(),
            "destination": final_dest
        }
