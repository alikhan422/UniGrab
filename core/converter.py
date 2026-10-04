import os
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal

class TranscodeWorker(QObject):
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, input_file, target_format, audio_only=False):
        super().__init__()
        self.input_file = input_file
        self.target_format = target_format.lower()
        self.audio_only = audio_only
        self.process = None

    def run(self):
        try:
            if not os.path.exists(self.input_file):
                self.error_occurred.emit("Input file not found on disk.")
                return

            base_dir = os.path.dirname(self.input_file)
            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            
            output_file = os.path.join(base_dir, f"{base_name}_converted.{self.target_format}")

            # FFmpeg Command Formulation
            cmd = ["ffmpeg", "-y", "-i", self.input_file]

            if self.audio_only:
                if self.target_format == "mp3":
                    cmd.extend(["-vn", "-acodec", "libmp3lame", "-q:a", "2", output_file])
                elif self.target_format == "m4a":
                    cmd.extend(["-vn", "-c:a", "aac", "-b:a", "192k", output_file])
                else:
                    cmd.extend(["-vn", output_file])
            else:
                if self.target_format == "mp4":
                    cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-strict", "experimental", output_file])
                elif self.target_format == "mkv":
                    cmd.extend(["-c:v", "copy", "-c:a", "copy", output_file])
                elif self.target_format == "3gp":
                    cmd.extend(["-r", "20", "-s", "352x288", "-c:v", "h263", "-b:v", "250k", "-c:a", "aac", "-b:a", "32k", output_file])
                else:
                    cmd.extend([output_file])

            # Hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            # Wait for completion
            stdout, _ = self.process.communicate()

            if self.process.returncode == 0:
                self.progress_changed.emit(100)
                self.finished.emit(output_file)
            else:
                self.error_occurred.emit(f"Conversion failed. Check if FFmpeg is installed.\nError Log: {stdout[-300:] if stdout else 'Unknown error'}")

        except Exception as e:
            self.error_occurred.emit(f"Conversion process error: {str(e)}")
