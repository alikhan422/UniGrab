import os
import re
import sys
import time
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|｜]', " ", name)
    clean = re.sub(r'\s+', " ", clean).strip()
    return clean[:120].strip() or "Media_Download"

def format_bytes(b):
    if not b or b <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"

class DownloadWorker(QThread):
    progress_changed = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, destination, format_selector="best", target_format="mp4", custom_filename="", playlist_items=""):
        super().__init__()
        self.url = url
        self.destination = destination
        self.format_selector = format_selector
        self.target_format = target_format
        self.custom_filename = custom_filename
        self.playlist_items = str(playlist_items).strip() if playlist_items else ""
        self._is_paused = False
        self._is_cancelled = False
        self.final_file_path = ""

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

    def _progress_hook(self, d):
        if self._is_cancelled:
            raise Exception("TASK_CANCELLED_BY_USER")

        while self._is_paused and not self._is_cancelled:
            self.status_changed.emit("Paused")
            time.sleep(0.5)

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            remaining = max(0, total - downloaded) if total > 0 else 0

            percent = 0.0
            if total > 0:
                percent = (downloaded / total) * 100.0

            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            filename = os.path.basename(d.get("filename", ""))

            self.progress_changed.emit({
                "percent": percent,
                "speed": speed,
                "eta": eta,
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "remaining_bytes": remaining,
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total) if total > 0 else "Unknown",
                "remaining_str": format_bytes(remaining) if total > 0 else "Calculating...",
                "filename": filename
            })
        elif d.get("status") == "finished":
            self.final_file_path = d.get("filename", "")

    def run(self):
        try:
            self.status_changed.emit("Connecting stream...")
            os.makedirs(self.destination, exist_ok=True)

            is_playlist = bool(self.playlist_items or "list=" in self.url.lower())

            # Agar playlist hai to har video ka apna original title aur index uthaye
            # Koi custom ajeeb naam force nahi hoga
            if is_playlist:
                out_tmpl = os.path.join(self.destination, "%(playlist_index|00)s - %(title).120s.%(ext)s")
            elif self.custom_filename:
                clean_name = sanitize_filename(self.custom_filename)
                out_tmpl = os.path.join(self.destination, f"{clean_name}.%(ext)s")
            else:
                out_tmpl = os.path.join(self.destination, "%(title).120s.%(ext)s")

            req_height = None
            if self.format_selector:
                m = re.search(r'(\d{3,4})p?', str(self.format_selector))
                if m:
                    req_height = m.group(1)

            if self.target_format == "mp3":
                fmt = "bestaudio/best"
            elif req_height:
                fmt = f"bestvideo[height<={req_height}]+bestaudio/best[height<={req_height}]/best"
            else:
                fmt = "bv*+ba/b"

            ydl_opts = {
                "format": fmt,
                "outtmpl": out_tmpl,
                "windowsfilenames": True,
                "restrictfilenames": False,
                "progress_hooks": [self._progress_hook],
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "socket_timeout": 30,
                "retries": 10,
                "fragment_retries": 10,
                "ignoreerrors": True,  # Agar playlist me koi 1 video unavailable ho to ruko mat, aagli download karo
            }

            # Playlist handling rules
            if is_playlist:
                ydl_opts["noplaylist"] = False
                ydl_opts["extract_flat"] = False
                if self.playlist_items:
                    # Clean playlist items e.g. "16-43"
                    cleaned_range = self.playlist_items.replace(" ", "")
                    ydl_opts["playlist_items"] = cleaned_range
            else:
                ydl_opts["noplaylist"] = True

            ffmpeg_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ffmpeg.exe")
            if os.path.exists(ffmpeg_local):
                ydl_opts["ffmpeg_location"] = ffmpeg_local

            if self.target_format == "mp3":
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status_changed.emit("Starting download...")
                info = ydl.extract_info(self.url, download=True)
                if not self.final_file_path:
                    self.final_file_path = self.destination

            if not self._is_cancelled:
                self.finished.emit(self.final_file_path)

        except Exception as e:
            err_msg = str(e)
            print(f"\n[DOWNLOAD ERROR DETECTED]: {err_msg}\n")
            if "TASK_CANCELLED_BY_USER" not in err_msg:
                self.error_occurred.emit(err_msg)
