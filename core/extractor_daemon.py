import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal


class ExtractorDaemon(QObject):
    """Analyzes stream formats and metadata asynchronously with cancel hooks."""
    metadata_ready = pyqtSignal(dict)
    extraction_failed = pyqtSignal(str)

    def __init__(self, target_url: str):
        super().__init__()
        self.target_url = target_url
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return

        ydl_opts = {
            "skip_download": True,
            "extract_flat": False,
            "no_warnings": True,
            "quiet": True,
            "socket_timeout": 10,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.target_url, download=False)

                if self._is_cancelled:
                    return

                available_resolutions = set()
                has_audio = False

                for f in info.get("formats", []):
                    height = f.get("height")
                    if height:
                        available_resolutions.add(f"{height}p")
                    if f.get("acodec") != "none":
                        has_audio = True

                parsed_metadata = {
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader", "Unknown Uploader"),
                    "resolutions": sorted(
                        list(available_resolutions),
                        key=lambda x: int(x.replace("p", "")),
                        reverse=True
                    ),
                    "has_audio": has_audio
                }

                if not self._is_cancelled:
                    self.metadata_ready.emit(parsed_metadata)
        except Exception as e:
            if not self._is_cancelled:
                self.extraction_failed.emit(str(e))