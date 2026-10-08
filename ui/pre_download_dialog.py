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
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            content = resp.read(65536).decode('utf-8', errors='ignore')
            m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if m:
                t = m.group(1).strip()
                t = re.sub(r'(\s*-\s*YouTube.*|\s*\|\s*YouTube.*)', '', t, flags=re.IGNORECASE)
                return t.strip()
    except Exception:
        pass
    return ""

class MetadataFetcherThread(QThread):
    metadata_ready = pyqtSignal(dict)
    metadata_error = pyqtSignal(dict)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "socket_timeout": 10
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    raise Exception("No metadata")

                raw_title = str(info.get("title", "")).strip()
                if not raw_title or raw_title.lower() in ["show", "video", "playlist"]:
                    raw_title = (
                        info.get("playlist_title") 
                        or info.get("playlist") 
                        or fetch_html_title(self.url)
                        or info.get("uploader") 
                        or "Media_Download"
                    )

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
                    sorted_res = ["1080p", "720p", "480p", "360p", "240p", "144p"]

                is_playlist = (
                    "entries" in info 
                    or "list=" in self.url.lower() 
                    or "season=" in self.url.lower()
                )

                self.metadata_ready.emit({
                    "title": raw_title,
                    "resolutions": sorted_res,
                    "is_playlist": is_playlist
                })
                return
        except Exception:
            pass

        fallback_title = fetch_html_title(self.url) or "Direct Stream"
        self.metadata_error.emit({
            "title": fallback_title,
            "resolutions": ["1080p", "720p", "480p", "360p", "240p"],
            "is_playlist": ("list=" in self.url.lower() or "season=" in self.url.lower())
        })

class PreDownloadDialog(QDialog):
    def __init__(self, parent=None, default_url="", default_path=""):
        super().__init__(parent)
        self.setWindowTitle("UniGrab - Download Options")
        self.resize(540, 420)
        self.save_dir = default_path or os.path.expanduser("~/Downloads")
        self.fetcher = None
        self.custom_filename = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.lbl_title = QLabel("Detecting media stream...")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #00d2ff; font-size: 13px;")
        layout.addWidget(self.lbl_title)

        layout.addWidget(QLabel("Media URL:"))
        self.txt_url = QLineEdit(default_url)
        self.txt_url.setPlaceholderText("Paste URL here...")
        self.txt_url.textChanged.connect(self._on_url_input_changed)
        layout.addWidget(self.txt_url)

        layout.addWidget(QLabel("Output Format / Container:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["MP4 (Universal Video)", "MP3 (Audio Only)", "3GP (Mobile Format)"])
        self.cmb_type.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.cmb_type)

        layout.addWidget(QLabel("Available Resolutions:"))
        self.cmb_resolution = QComboBox()
        self.cmb_resolution.addItems(["1080p", "720p", "480p", "360p", "240p"])
        self.cmb_resolution.setCurrentText("720p")
        layout.addWidget(self.cmb_resolution)

        self.lbl_playlist = QLabel("Playlist Range / Selection (Optional e.g. 1-5, 5-10, 1,5,9):")
        layout.addWidget(self.lbl_playlist)
        self.txt_playlist = QLineEdit()
        self.txt_playlist.setPlaceholderText("Leave empty for complete playlist")
        layout.addWidget(self.txt_playlist)

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
        if idx == 1: # MP3
            self.cmb_resolution.setEnabled(False)
        elif idx == 2: # 3GP
            self.cmb_resolution.setEnabled(True)
            if "240p" in [self.cmb_resolution.itemText(i) for i in range(self.cmb_resolution.count())]:
                self.cmb_resolution.setCurrentText("240p")
        else: # MP4
            self.cmb_resolution.setEnabled(True)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.txt_dir.text())
        if folder:
            self.txt_dir.setText(folder)

    def _on_metadata_loaded(self, data):
        self.lbl_title.setText(f"Target: {data['title'][:70]}")
        self.custom_filename = data["title"]
        self.cmb_resolution.clear()
        for res in data["resolutions"]:
            self.cmb_resolution.addItem(res)

        if self.cmb_type.currentIndex() == 2: # 3GP
            if "240p" in data["resolutions"]:
                self.cmb_resolution.setCurrentText("240p")
            elif "360p" in data["resolutions"]:
                self.cmb_resolution.setCurrentText("360p")
        else:
            if "720p" in data["resolutions"]:
                self.cmb_resolution.setCurrentText("720p")
            elif "360p" in data["resolutions"]:
                self.cmb_resolution.setCurrentText("360p")
        self.btn_download.setEnabled(True)

    def _on_metadata_fallback(self, data):
        self.lbl_title.setText(f"Target: {data['title'][:70]}")
        self.custom_filename = data["title"]
        self.cmb_resolution.clear()
        for res in data["resolutions"]:
            self.cmb_resolution.addItem(res)
        self.btn_download.setEnabled(True)

    def _start_download(self):
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter or paste a valid download link.")
            return
        self.save_dir = self.txt_dir.text().strip()
        self.accept()

    def get_configuration(self):
        idx = self.cmb_type.currentIndex()
        if idx == 1:
            t_format = "mp3"
            f_selector = "bestaudio"
        elif idx == 2:
            t_format = "3gp"
            f_selector = self.cmb_resolution.currentText()
        else:
            t_format = "mp4"
            f_selector = self.cmb_resolution.currentText()

        return {
            "url": self.txt_url.text().strip(),
            "destination": self.save_dir,
            "format_selector": f_selector,
            "target_format": t_format,
            "custom_filename": self.custom_filename,
            "playlist_items": self.txt_playlist.text().strip()
        }
