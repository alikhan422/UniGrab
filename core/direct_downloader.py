import os
import time
import urllib.parse
import requests
from PyQt6.QtCore import QObject, pyqtSignal

class DirectDownloadWorker(QObject):
    progress_changed = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, destination, custom_filename=""):
        super().__init__()
        self.url = url
        self.destination = destination
        self.custom_filename = custom_filename
        self.is_paused = False
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def run(self):
        try:
            self.status_changed.emit("Connecting...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.head(self.url, headers=headers, allow_redirects=True, timeout=15)
            final_url = response.url

            filename = self.custom_filename
            if not filename:
                content_disp = response.headers.get("content-disposition", "")
                if "filename=" in content_disp:
                    filename = content_disp.split("filename=")[-1].strip("\"' ")
                else:
                    path_part = urllib.parse.urlparse(final_url).path
                    filename = os.path.basename(path_part)
            
            if not filename:
                filename = "downloaded_file.bin"

            os.makedirs(self.destination, exist_ok=True)
            output_filepath = os.path.join(self.destination, filename)

            existing_size = 0
            if os.path.exists(output_filepath):
                existing_size = os.path.getsize(output_filepath)

            server_len = int(response.headers.get("content-length", 0))
            total_size = server_len + existing_size if server_len > 0 else 0

            if existing_size > 0 and server_len > 0:
                headers["Range"] = f"bytes={existing_size}-"

            req = requests.get(self.url, headers=headers, stream=True, allow_redirects=True, timeout=20)
            
            if req.status_code == 206:
                mode = "ab"
                downloaded = existing_size
            elif req.status_code == 200:
                mode = "wb"
                downloaded = 0
                total_size = int(req.headers.get("content-length", total_size))
            else:
                mode = "wb"
                downloaded = 0

            self.status_changed.emit("Downloading")

            last_time = time.time()
            bytes_since_last = 0
            chunk_size = 1024 * 64

            with open(output_filepath, mode) as f:
                for chunk in req.iter_content(chunk_size=chunk_size):
                    if self.is_cancelled:
                        self.error_occurred.emit("TASK_CANCELLED_BY_USER")
                        return

                    while self.is_paused:
                        time.sleep(0.3)
                        if self.is_cancelled:
                            self.error_occurred.emit("TASK_CANCELLED_BY_USER")
                            return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        bytes_since_last += len(chunk)

                        now = time.time()
                        time_diff = now - last_time
                        if time_diff >= 0.5:
                            speed = bytes_since_last / time_diff
                            percent = int((downloaded / total_size) * 100) if total_size > 0 else 0
                            eta = int((total_size - downloaded) / speed) if speed > 0 and total_size > 0 else 0

                            self.progress_changed.emit({
                                "percent": percent,
                                "speed": speed,
                                "eta": eta,
                                "downloaded": downloaded,
                                "total": total_size
                            })
                            last_time = now
                            bytes_since_last = 0

            # Strict verification: agar internet beech me toot jaye to complete na kahe
            if total_size > 0 and downloaded < total_size:
                raise ConnectionError(f"Connection lost. Only received {downloaded}/{total_size} bytes.")

            self.progress_changed.emit({
                "percent": 100,
                "speed": 0,
                "eta": 0,
                "downloaded": total_size if total_size > 0 else downloaded,
                "total": total_size if total_size > 0 else downloaded
            })
            self.finished.emit(output_filepath)

        except requests.exceptions.RequestException as net_err:
            if not self.is_cancelled:
                self.error_occurred.emit(f"Network error: {str(net_err)}")
        except Exception as e:
            if not self.is_cancelled:
                self.error_occurred.emit(str(e))
