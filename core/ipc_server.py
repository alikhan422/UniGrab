import json
import socket
from PyQt6.QtCore import QObject, pyqtSignal


class IPCServer(QObject):
    """Listens on loopback port 49152 for links pushed from browser extensions."""
    url_received = pyqtSignal(str)

    def __init__(self, host="127.0.0.1", port=49152):
        super().__init__()
        self.host = host
        self.port = port
        self.running = False
        self._server_sock = None

    def start_listening(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        self.running = True

        while self.running:
            try:
                client, _ = self._server_sock.accept()
                raw = client.recv(4096)
                if raw:
                    payload = json.loads(raw.decode("utf-8"))
                    if "url" in payload:
                        self.url_received.emit(payload["url"])
                client.close()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[IPC Exception] {e}")

    def stop(self):
        self.running = False
        if self._server_sock:
            self._server_sock.close()