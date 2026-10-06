import os
import re
import urllib.request
import ssl
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import yt_dlp

def fetch_html_title(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
            content = resp.read(65536).decode('utf-8', errors='ignore')
            m = re.search(r'<title>(.*?)', content, re.IGNORECASE | re.DOTALL)
            if m:
                t = m.group(1).strip()
                t = re.sub(r'(\s*-\s*HubCloud.*|\s*\|\s*HubCloud.*|Download.*HubCloud.*)', '', t, flags=re.IGNORECASE)
                return t.strip()
    except Exception:
        pass
    
    # Fallback to URL segment
    base = os.path.basename(url.split('?')[0])
    return base if base else "Direct_Media_Download"

class MetadataFetcherThread(QThread):
    metadata_ready = pyqtSignal(dict)
    metadata_error = pyqtSignal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        # 1. Pehle yt-dlp se check karein
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "socket_timeout": 8
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if info:
                    title = info.get("title") or fetch_html_title(self.url)
                    formats = info.get("formats", [])
                    resolutions = set()
                    for f in formats:
                        h = f.get("height")
                        if h and isinstance(h, int) and h >= 144:
                            resolutions.add(f"{h}p")

                    def sort_key(res):
                        digits = re.findall(r'\d+', res)
                        return int(digits[0]) if digits else 0

                    sorted_res = sorted(list(resolutions), key=sort_key, reverse=True)
                    if not sorted_res:
                        sorted_res = ["1080p", "720p", "480p", "360p"]

                    self.metadata_ready.emit({
                        "title": title,
                        "resolutions": sorted_res,
                        "is_playlist": "entries" in info or "list=" in self.url.lower(),
                        "is_direct": False
                    })
                    return
        except Exception:
            pass

        # 2. Agar yt-dlp fail ho jaye (jaise HubCloud, Google Drive, Mediafire pages), to webpage se movie title nikaalein
        real_title = fetch_html_title(self.url)
        self.metadata_error.emit({
            "title": real_title,
            "resolutions": ["Direct Stream (Original Quality)", "720p", "480p", "360p"],
            "is_direct": True
        })

class PreDownloadDialog(QDialog):
    def __init__(self, parent=None, default_url="", default_path=""):
        super().__init__(parent)
        self.setWindowTitle("UniGrab - Download Options")
        self.resize(520, 390)
        self.selected_format = "720p"
        self.selected_type = "mp4"
        self.playlist_items = ""
        self.custom_filename = ""
        self.save_dir = default_path or os.path.expanduser("~/Downloads")
        self.fetcher = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.lbl_title = QLabel("Paste link below to auto-detect resolutions:")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #00d2ff;")
        layout.addWidget(self.lbl_title)

        layout.addWidget(QLabel("Media URL:"))
        self.txt_url = QLineEdit(default_url)
        self.txt_url.setReadOnly(False)
        self.txt_url.setFocus()
        self.txt_url.setPlaceholderText("Paste URL here...")
        self.txt_url.textChanged.connect(self._on_url_input_changed)
        layout.addWidget(self.txt_url)

        layout.addWidget(QLabel("Available Resolutions / Stream:"))
        self.cmb_resolution = QComboBox()
        self.cmb_resolution.addItems(["1080p", "720p", "480p", "360p"])
        self.cmb_resolution.setCurrentText("720p")
        layout.addWidget(self.cmb_resolution)

        layout.addWidget(QLabel("Output Type:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Video (MP4 - Universal H.264/AAC)", "Audio Only (MP3)"])
        self.cmb_type.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.cmb_type)

        self.lbl_playlist = QLabel("Playlist Range / Selection (Optional e.g. 1-5, 5-10, 1,5,9):")
        self.txt_playlist = QLineEdit()
        self.txt_playlist.setPlaceholderText("Leave empty for complete playlist")
        layout.addWidget(self.lbl_playlist)

        layout.addWidget(QLabel("Save Directory:"))
        dir_box = QHBoxLayout()
        self.txt_dir = QLineEdit(self.save_dir)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_dir)
        dir_box.addWidget(self.txt_dir)
        dir_box.addWidget(btn_browse)
        layout.addLayout(dir_box)

        btn_box = QHBoxLayout()
        self.btn_download = QPushButton("Start Download")
        self.btn_download.clicked.connect(self._start_download)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_download)
        layout.addLayout(btn_box)

        if default_url:
            self._trigger_fetch(default_url)

    def _on_url_input_changed(self, url):
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            self._trigger_fetch(url)

    def _trigger_fetch(self, url):
        self.lbl_title.setText("Detecting media stream & available resolutions...")
        self.cmb_resolution.clear()
        self.cmb_resolution.addItem("Detecting...")
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.terminate()
        self.fetcher = MetadataFetcherThread(url)
        self.fetcher.metadata_ready.connect(self._on_metadata_loaded)
        self.fetcher.metadata_error.connect(self._on_metadata_fallback)
        self.fetcher.start()

    def _on_type_changed(self, idx):
        self.cmb_resolution.setEnabled(idx == 0)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.txt_dir.text())
        if folder:
            self.txt_dir.setText(folder)

    def _on_metadata_loaded(self, data):
        self.lbl_title.setText(f"Target: {data['title'][:65]}")
        self.custom_filename = data["title"]
        self.cmb_resolution.clear()
        for res in data["resolutions"]:
            self.cmb_resolution.addItem(res)

        if "720p" in data["resolutions"]:
            self.cmb_resolution.setCurrentText("720p")
        elif "1080p" in data["resolutions"]:
            self.cmb_resolution.setCurrentText("1080p")

        if data.get("is_playlist"):
            self.lbl_playlist.show()
            self.txt_playlist.show()
        else:
            self.lbl_playlist.hide()
            self.txt_playlist.hide()
        self.btn_download.setEnabled(True)

    def _on_metadata_fallback(self, data):
        self.lbl_title.setText(f"Target: {data['title'][:65]}")
        self.custom_filename = data["title"]
        self.cmb_resolution.clear()
        for res in data["resolutions"]:
            self.cmb_resolution.addItem(res)
        self.lbl_playlist.hide()
        self.txt_playlist.hide()
        self.btn_download.setEnabled(True)

    def _start_download(self):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter or paste a valid download link.")
            return
        self.selected_format = self.cmb_resolution.currentText()
        self.selected_type = "mp3" if self.cmb_type.currentIndex() == 1 else "mp4"
        self.playlist_items = self.txt_playlist.text().strip()
        self.save_dir = self.txt_dir.text().strip()
        self.accept()

    def get_configuration(self):
        return {
            "url": self.txt_url.text().strip(),
            "destination": self.save_dir,
            "format_selector": self.selected_format,
            "target_format": self.selected_type,
            "custom_filename": self.custom_filename,
            "playlist_items": self.playlist_items
        }
