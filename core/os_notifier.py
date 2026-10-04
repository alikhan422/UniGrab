import os
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect
from plyer import notification

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("hwnd", wintypes.HWND),
            ("dwFlags", wintypes.DWORD),
            ("uCount", wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        ]

    FLASHW_STOP = 0
    FLASHW_ALL = 3
    FLASHW_TIMERNOFG = 12


class SystemNotifier:
    """Handles audio alerts, desktop toasts, and taskbar flashing."""

    def __init__(self, main_window=None):
        self.main_window = main_window
        self.sound_effect = QSoundEffect()
        sound_path = os.path.join(os.path.dirname(__file__), "..", "assets", "notify.wav")
        if os.path.exists(sound_path):
            self.sound_effect.setSource(QUrl.fromLocalFile(os.path.abspath(sound_path)))
            self.sound_effect.setVolume(0.85)

    def trigger_completion(self, title: str, message: str):
        if self.sound_effect.isLoaded():
            self.sound_effect.play()
        elif sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)

        try:
            notification.notify(
                title=title,
                message=message,
                app_name="UniGrab Studio",
                timeout=5
            )
        except Exception as e:
            print(f"[Notifier] Notification error: {e}")

        if sys.platform == "win32" and self.main_window and self.main_window.winId():
            try:
                hwnd = int(self.main_window.winId())
                info = FLASHWINFO(
                    cbSize=ctypes.sizeof(FLASHWINFO),
                    hwnd=hwnd,
                    dwFlags=FLASHW_ALL | FLASHW_TIMERNOFG,
                    uCount=5,
                    dwTimeout=0,
                )
                ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
            except Exception as e:
                print(f"[Notifier] Win32 flash error: {e}")

    def clear_taskbar_flash(self):
        if sys.platform == "win32" and self.main_window and self.main_window.winId():
            try:
                hwnd = int(self.main_window.winId())
                info = FLASHWINFO(
                    cbSize=ctypes.sizeof(FLASHWINFO),
                    hwnd=hwnd,
                    dwFlags=FLASHW_STOP,
                    uCount=0,
                    dwTimeout=0,
                )
                ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
            except Exception:
                pass