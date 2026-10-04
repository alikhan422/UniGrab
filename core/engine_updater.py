import sys
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal


class EngineAutoUpdater(QObject):
    """Dynamic updater for the yt-dlp core engine."""
    update_checked = pyqtSignal(bool, str)

    def check_and_update(self):
        try:
            creation_flag = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flag
            )
            if res.returncode == 0:
                self.update_checked.emit(True, "Engine updated successfully.")
            else:
                self.update_checked.emit(False, f"Update failed: {res.stderr.strip()}")
        except Exception as e:
            self.update_checked.emit(False, str(e))