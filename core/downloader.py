import os
import re
import sys
import time
import urllib.request
import urllib.parse
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

def clean_media_title(raw_title):
    if not raw_title:
        return ""
    t = str(raw_title).strip()
    # Strip web extensions or temp suffixes
    t = re.sub(r'\.(mp4|mkv|webm|mp3|3gp|part|ytdl)$', '', t, flags=re.IGNORECASE)
    # Strip token hashes or URL patterns
    if t.startswith("http://") or t.startswith("https://") or t.startswith("ADGPM"):
        return ""
    return sanitize_filename(t)

class DownloadWorker(QThread):
    progress_changed = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    title_resolved = pyqtSignal(str)

    def __init__(self, url, destination, format_selector="best", target_format="mp4", custom_filename="", playlist_items=""):
        super().__init__()
        self.url = url
        self.destination = destination
        self.format_selector = str(format_selector or "best").strip()
        self.target_format = str(target_format or "mp4").lower().strip()
        self.custom_filename = clean_media_title(custom_filename)
        self.playlist_items = str(playlist_items).strip() if playlist_items else ""
        
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        self._is_paused = False
        self._is_cancelled = False
        self.final_file_path = ""
        self._has_emitted_title = False
        self._last_percent = 0.0

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

        # Extract title from active yt-dlp download info
        if not self._has_emitted_title:
            info_dict = d.get("info_dict") or {}
            live_title = info_dict.get("title") or ""
            if not live_title:
                fname = d.get("filename", "")
                if fname:
                    bname = os.path.basename(fname)
                    live_title = re.sub(r'\.(mp4|mkv|webm|mp3|3gp|part|f\d+)$', '', bname, flags=re.IGNORECASE)

            clean_t = clean_media_title(live_title)
            if clean_t and clean_t.lower() not in ["show", "video", "media_download"]:
                self.title_resolved.emit(clean_t)
                self._has_emitted_title = True

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            remaining = max(0, total - downloaded) if total > 0 else 0

            percent = 0.0
            if total > 0:
                percent = (downloaded / total) * 100.0
            self._last_percent = percent

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
            self._last_percent = 100.0

    def run(self):
        try:
            self.status_changed.emit("Connecting stream...")
            os.makedirs(self.destination, exist_ok=True)

            is_playlist_url = bool("list=" in self.url.lower() or "season=" in self.url.lower())
            has_specific_items = bool(self.playlist_items)

            if self.custom_filename:
                self.title_resolved.emit(self.custom_filename)
                self._has_emitted_title = True

            if is_playlist_url and not has_specific_items:
                target_dir = os.path.join(self.destination, "%(playlist_title|%(playlist|Playlist))s")
                out_tmpl = os.path.join(target_dir, "%(playlist_index|00)s - %(title).120s.%(ext)s")
            elif is_playlist_url and has_specific_items:
                out_tmpl = os.path.join(self.destination, "%(playlist_index|00)s - %(title).120s.%(ext)s")
            elif self.custom_filename:
                out_tmpl = os.path.join(self.destination, f"{self.custom_filename}.%(ext)s")
            else:
                out_tmpl = os.path.join(self.destination, "%(title).120s.%(ext)s")

            req_height = None
            m = re.search(r'(\d{3,4})', self.format_selector)
            if m:
                req_height = m.group(1)

            if self.target_format == "mp3":
                fmt = "bestaudio/best"
                merge_fmt = None
            elif self.target_format == "3gp":
                h = req_height if req_height else "240"
                fmt = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
                merge_fmt = "3gp"
            elif req_height:
                fmt = f"bestvideo[height={req_height}][vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo[height<={req_height}][vcodec^=avc]+bestaudio/bestvideo[height<={req_height}]+bestaudio/best[height<={req_height}]"
                merge_fmt = "mp4"
            else:
                fmt = "bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best"
                merge_fmt = "mp4"

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ffmpeg_local = os.path.join(base_dir, "ffmpeg.exe")

            ydl_opts = {
                "format": fmt,
                "outtmpl": out_tmpl,
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

            if merge_fmt:
                ydl_opts["merge_output_format"] = merge_fmt

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
            elif self.target_format == "3gp":
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "3gp"
                }]
                ydl_opts["postprocessor_args"] = {
                    "VideoRemuxer": ["-c:v", "h263", "-s", "352x288", "-r", "15", "-c:a", "aac", "-b:a", "64k", "-ar", "16000"]
                }
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

            if ret_code != 0 and self._last_percent < 99.0:
                raise Exception("Download interrupted: Network connection dropped before completing.")

            self.status_changed.emit("Completed")
            self.finished.emit(self.final_file_path)

        except Exception as e:
            err_msg = str(e)
            if "TASK_CANCELLED_BY_USER" not in err_msg:
                self.status_changed.emit("Failed")
                self.error_occurred.emit(err_msg)
