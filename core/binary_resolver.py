import os
import sys
import shutil


def get_binary_path(binary_name: str) -> str:
    """
    Resolves the executable path for external binaries (ffmpeg, ffprobe).
    Priority:
      1. PyInstaller bundled temp folder (sys._MEIPASS/bin)
      2. Project local folder (../bin)
      3. System PATH
    """
    ext = ".exe" if sys.platform == "win32" else ""
    target_bin = f"{binary_name}{ext}"

    if hasattr(sys, "_MEIPASS"):
        bundle_path = os.path.join(sys._MEIPASS, "bin", target_bin)
        if os.path.exists(bundle_path):
            return bundle_path

    local_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", target_bin)
    if os.path.exists(local_bin):
        return os.path.abspath(local_bin)

    system_path = shutil.which(binary_name)
    if system_path:
        return system_path

    raise FileNotFoundError(
        f"Critical binary '{binary_name}' not found in bundle, local bin/, or system PATH."
    )