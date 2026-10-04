import json
import urllib.request
import ssl
from PyQt6.QtCore import QThread, pyqtSignal

CURRENT_APP_VERSION = "2.0.1"
UPDATE_SCHEMA_URL = "https://raw.githubusercontent.com/alikhan422/UniGrab/main/version.json"

class AppUpdateChecker(QThread):
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                UPDATE_SCHEMA_URL,
                headers={"User-Agent": "UniGrab-Studio-Client/2.0.1"}
            )
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    remote_ver = data.get("version", "").strip()
                    
                    if remote_ver and remote_ver != CURRENT_APP_VERSION:
                        self.update_available.emit(data)
                    else:
                        self.no_update.emit()
                else:
                    self.check_failed.emit(f"Server returned status {response.status}")
        except Exception as e:
            self.check_failed.emit(str(e))
