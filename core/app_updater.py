import json
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_APP_VERSION = "1.0.0"
# Aap apna GitHub Releases ya Raw JSON link yahan replace kar sakte hain:
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/alikhan422/UniGrab/main/version.json"

class AppUpdateChecker(QThread):
    update_available = pyqtSignal(dict)      # agar new version mil jaye
    no_update = pyqtSignal()                 # agar already latest ho
    check_failed = pyqtSignal(str)           # agar network ya URL error aaye

    def __init__(self, check_url=UPDATE_CHECK_URL):
        super().__init__()
        self.check_url = check_url

    def _parse_version(self, ver_str):
        try:
            return [int(x) for x in ver_str.strip().lstrip("v").split(".")]
        except Exception:
            return [0, 0, 0]

    def run(self):
        try:
            req = urllib.request.Request(
                self.check_url,
                headers={"User-Agent": "UniGrab-Client/1.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

            remote_ver = payload.get("version", "1.0.0")
            cur_parts = self._parse_version(CURRENT_APP_VERSION)
            rem_parts = self._parse_version(remote_ver)

            if rem_parts > cur_parts:
                payload["current_version"] = CURRENT_APP_VERSION
                self.update_available.emit(payload)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_failed.emit(str(e))
