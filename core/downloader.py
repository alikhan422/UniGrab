import os
import re
import sys
import time
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import yt_dlp

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|｜]', " ", str(name))
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
        self.format_selector = str(format_selector or "best")
        self.target_format = str(target_format or "mp4").lower()
        self.custom_filename = custom_filename
        self.playlist_items = str(playlist_items).strip() if playlist_items else ""
        
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        self._is_paused = False
        self._is_cancelled = False
        self._has_completed_successfully = False
        self.final_file_path = ""

    def pause(self):
        self.mutex.lock()
        self._is_paused = True
        self.mutex.unlock()
        self.status_changed.emit("Paused")

    def resume(self):
        self.mutex.lock()
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        self.status_changed.emit("Downloading")

    def cancel(self):
        self.mutex.lock()
        self._is_cancelled = True
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        self.status_changed.emit("Cancelled")

    def _progress_hook(self, d):
        self.mutex.lock()
        if self._is_cancelled:
            self.mutex.unlock()
            raise Exception("TASK_CANCELLED_BY_USER")

        while self._is_paused:
            self.pause_condition.wait(self.mutex)
            if self._is_cancelled:
                self.mutex.unlock()
                raise Exception("TASK_CANCELLED_BY_USER")
        self.mutex.unlock()

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
            self._has_completed_successfully = True

    def run(self):
        try:
            self.status_changed.emit("Connecting stream...")
            os.makedirs(self.destination, exist_ok=True)

            is_playlist_url = bool("list=" in self.url.lower())
            has_specific_items = bool(self.playlist_items)

            # Accurate Playlist Folder Naming (Fixes "show" or broken names)
            if is_playlist_url and not has_specific_items:
                # %(playlist_title|%(playlist|Playlist))s ensures accurate original playlist name
                target_dir = os.path.join(self.destination, "%(playlist_title|%(playlist|Playlist))s")
                out_tmpl = os.path.join(target_dir, "%(playlist_index|00)s - %(title).120s.%(ext)s")
            elif is_playlist_url and has_specific_items:
                out_tmpl = os.path.join(self.destination, "%(playlist_index|00)s - %(title).120s.%(ext)s")
            elif self.custom_filename:
                clean_name = sanitize_filename(self.custom_filename)
                out_tmpl = os.path.join(self.destination, f"{clean_name}.%(ext)s")
            else:
                out_tmpl = os.path.join(self.destination, "%(title).120s.%(ext)s")

            req_height = None
            m = re.search(r'(\d{3,4})p?', self.format_selector)
            if m:
                req_height = m.group(1)

            if self.target_format == "mp3":
                fmt = "bestaudio/best"
            elif req_height:
                fmt = f"bestvideo[height<={req_height}][vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo[height<={req_height}]+bestaudio/best[height<={req_height}]/best"
            else:
                fmt = "bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best"

            ffmpeg_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ffmpeg.exe")

            ydl_opts = {
                "format": fmt,
                "outtmpl": out_tmpl,
                "merge_output_format": "mp4",
                "windowsfilenames": True,
                "restrictfilenames": False,
                "progress_hooks": [self._progress_hook],
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
                "socket_timeout": 20,
                "retries": 5,
                "fragment_retries": 5,
                "ignoreerrors": False,
            }

            if is_playlist_url:
                ydl_opts["noplaylist"] = False
                ydl_opts["extract_flat"] = False
                if has_specific_items:
                    ydl_opts["playlist_items"] = self.playlist_items.replace(" ", "")
            else:
                ydl_opts["noplaylist"] = True

            if os.path.exists(ffmpeg_local):
                ydl_opts["ffmpeg_location"] = ffmpeg_local

            if self.target_format == "mp3":
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            else:
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4"
                }]
                ydl_opts["postprocessor_args"] = {
                    "VideoRemuxer": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status_changed.emit("Downloading")
                ret_code = ydl.download([self.url])
                if not self.final_file_path:
                    self.final_file_path = self.destination

            if self._is_cancelled:
                return

            if ret_code != 0 or not self._has_completed_successfully:
                raise Exception("Download interrupted: Network connection dropped before completing.")

            self.finished.emit(self.final_file_path)

        except Exception as e:
            err_msg = str(e)
            if "TASK_CANCELLED_BY_USER" not in err_msg:
                self.status_changed.emit("Failed")
                self.error_occurred.emit(err_msg)
