import os
import sys
import json
import subprocess
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QHeaderView, QMessageBox, QLabel, QFrame,
    QSizePolicy, QSystemTrayIcon, QMenu, QStackedWidget,
    QScrollArea, QGridLayout, QAbstractItemView
)
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QIcon, QPixmap, QAction

if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('unigrab.multimedia.workstation.1.0')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

from ui.styles import MODERN_NEON_DARK_THEME
from ui.pre_download_dialog import PreDownloadDialog
from core.downloader import DownloadWorker
from core.direct_downloader import DirectDownloadWorker
from core.url_sniffer import is_direct_download
from core.os_notifier import SystemNotifier
from core.ipc_server import IPCServer
from core.app_updater import AppUpdateChecker, CURRENT_APP_VERSION

def find_logo():
    for p in [os.path.join(BASE_DIR, "assets", "logo_crisp.png"), os.path.join(BASE_DIR, "assets", "logo.ico"), os.path.join(BASE_DIR, "assets", "logo.png")]:
        if os.path.exists(p):
            return p
    return None

def format_speed(bps):
    if not bps or bps <= 0:
        return "0 KB/s"
    if bps >= 1048576:
        return f"{bps / 1048576.0:.2f} MB/s"
    return f"{bps / 1024.0:.1f} KB/s"

def format_seconds(sec):
    if not sec or sec < 0:
        return ""
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"ETA {h:02d}:{m:02d}:{s:02d}" if h > 0 else f"ETA {m:02d}:{s:02d}"

class DownloadCardWidget(QFrame):
    def __init__(self, task, on_pause, on_stop, on_folder, on_delete):
        super().__init__()
        self.task = task
        self.setProperty("class", "downloadCard")
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.banner = QFrame()
        self.banner.setFixedHeight(120)
        self.banner.setStyleSheet("background-color: #1E293B; border-radius: 8px;")
        b_layout = QVBoxLayout(self.banner)
        b_icon = QLabel("🎬" if not task["cfg"].get("is_audio_only") else "🎵")
        b_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_icon.setStyleSheet("font-size: 38px; color: #94A3B8;")
        b_layout.addWidget(b_icon)
        layout.addWidget(self.banner)

        title_text = task["cfg"].get("title") or task["cfg"].get("url", "")
        self.lbl_title = QLabel(title_text)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(self.lbl_title)

        row_prog = QHBoxLayout()
        self.lbl_percent = QLabel(f"{int(task['cfg'].get('progress', 0))}%")
        self.lbl_percent.setStyleSheet("font-weight: 700; color: #10B981;")
        self.lbl_size = QLabel(task["cfg"].get("size_display", "Connecting..."))
        self.lbl_size.setStyleSheet("font-size: 11px; color: #94A3B8;")
        row_prog.addWidget(self.lbl_percent)
        row_prog.addStretch()
        row_prog.addWidget(self.lbl_size)
        layout.addLayout(row_prog)

        self.pb = QProgressBar()
        self.pb.setRange(0, 100)
        self.pb.setValue(int(task["cfg"].get("progress", 0)))
        self.pb.setFixedHeight(8)
        self.pb.setTextVisible(False)
        layout.addWidget(self.pb)

        self.lbl_meta = QLabel("Connecting...")
        self.lbl_meta.setStyleSheet("font-size: 11px; color: #64748B;")
        layout.addWidget(self.lbl_meta)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_pause = QPushButton("Pause")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btnStop")
        self.btn_folder = QPushButton("Folder")
        self.btn_folder.setObjectName("btnFolder")
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("btnStop")

        for b in [self.btn_pause, self.btn_stop, self.btn_folder, self.btn_delete]:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_layout.addWidget(b)

        layout.addLayout(btn_layout)

        self.btn_pause.clicked.connect(lambda: on_pause(self.task))
        self.btn_stop.clicked.connect(lambda: on_stop(self.task))
        self.btn_folder.clicked.connect(lambda: on_folder(self.task))
        self.btn_delete.clicked.connect(lambda: on_delete(self.task))

    def update_metrics(self, pct, size_str, speed_str, status_str):
        self.pb.setValue(int(pct))
        self.lbl_percent.setText(f"{int(pct)}%")
        self.lbl_size.setText(size_str)
        self.lbl_meta.setText(f"{speed_str} • {status_str}")

class MainWindow(QMainWindow):

    def _update_task_title(self, task, new_title):
        try:
            if not new_title or str(new_title).startswith("http"):
                return
            task["title"] = new_title
            target_url = task.get("url", "")
            
            # Update Table View
            if hasattr(self, "table"):
                for r in range(self.table.rowCount()):
                    item = self.table.item(r, 0)
                    if item:
                        current_text = item.text().strip()
                        # Agar current cell me URL likha ho ya is task ka URL ho
                        if current_text == target_url or current_text.startswith("http"):
                            item.setText(new_title)
                            break

            # Update Cards View
            if hasattr(self, "cards_layout"):
                for i in range(self.cards_layout.count()):
                    w = self.cards_layout.itemAt(i).widget()
                    if w and hasattr(w, "lbl_title"):
                        if w.lbl_title.text().strip() == target_url or w.lbl_title.text().startswith("http"):
                            w.lbl_title.setText(new_title)
                            break
        except Exception:
            pass

    def __init__(self):
        super().__init__()
        self.is_really_quitting = False
        self.logo_path = find_logo()
        if self.logo_path:
            self.setWindowIcon(QIcon(self.logo_path))

        self.setWindowTitle(f"UniGrab Studio v{CURRENT_APP_VERSION} – Universal Multimedia Workstation")
        self.resize(1280, 740)
        self.setMinimumSize(900, 550)
        self.setStyleSheet(MODERN_NEON_DARK_THEME)
        self.notifier = SystemNotifier(self)
        self.tasks = []

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        top_card = QFrame()
        top_card.setObjectName("topCard")
        card_layout = QHBoxLayout(top_card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(12)

        if self.logo_path:
            logo_label = QLabel()
            pix = QPixmap(self.logo_path)
            if not pix.isNull():
                logo_label.setPixmap(pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                card_layout.addWidget(logo_label)

        title_label = QLabel(f"UniGrab Studio v{CURRENT_APP_VERSION}")
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #10B981;")
        card_layout.addWidget(title_label)
        card_layout.addStretch()

        self.btn_toggle_view = QPushButton("⊞ Switch to Cards View")
        self.btn_toggle_view.setObjectName("btnToggleView")
        self.btn_toggle_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_view.clicked.connect(self._toggle_view_mode)
        card_layout.addWidget(self.btn_toggle_view)

        self.btn_new = QPushButton("+ New Download")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(lambda: self._prompt_new_task(""))
        card_layout.addWidget(self.btn_new)

        self.btn_check_updates = QPushButton("Check for Updates")
        self.btn_check_updates.setObjectName("btnFolder")
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_updates.clicked.connect(self._check_for_updates_interactive)
        card_layout.addWidget(self.btn_check_updates)

        main_layout.addWidget(top_card)

        self.view_stack = QStackedWidget()

        # VIEW 1: Table Rows
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Resource Title", "Profile", "Progress", "Size & Speed", "Actions"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setWordWrap(True)

        h_header = self.table.horizontalHeader()
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 240)
        self.table.setColumnWidth(4, 340)

        v_header = self.table.verticalHeader()
        v_header.setDefaultSectionSize(54)
        self.view_stack.addWidget(self.table)

        # VIEW 2: Grid Cards
        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_container = QWidget()
        self.grid_layout = QGridLayout(self.card_container)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.card_scroll.setWidget(self.card_container)
        self.view_stack.addWidget(self.card_scroll)

        main_layout.addWidget(self.view_stack)

        self._init_system_tray()
        self._load_history()
        self._init_ipc_service()

    def _toggle_view_mode(self):
        if self.view_stack.currentIndex() == 0:
            self.view_stack.setCurrentIndex(1)
            self.btn_toggle_view.setText("☰ Switch to Rows View")
        else:
            self.view_stack.setCurrentIndex(0)
            self.btn_toggle_view.setText("⊞ Switch to Cards View")

    def _init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.logo_path) if self.logo_path else self.windowIcon())
        tray_menu = QMenu()
        tray_menu.addAction("Open UniGrab", self.restore_window)
        tray_menu.addAction("+ New Download", lambda: self._prompt_new_task(""))
        tray_menu.addSeparator()
        tray_menu.addAction("Exit Completely", self.exit_application)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(lambda r: self.restore_window() if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray_icon.show()

    def restore_window(self):
        self.showNormal()
        self.activateWindow()

    def exit_application(self):
        self.is_really_quitting = True
        self.close()

    def closeEvent(self, event):
        if not self.is_really_quitting:
            event.ignore()
            self.hide()
            return
        self._save_history()
        self.tray_icon.hide()
        super().closeEvent(event)

    def _init_ipc_service(self):
        self.ipc_thread = QThread()
        self.ipc_server = IPCServer()
        self.ipc_server.moveToThread(self.ipc_thread)
        self.ipc_thread.started.connect(self.ipc_server.start_listening)
        self.ipc_server.url_received.connect(self._prompt_new_task)
        self.ipc_thread.start()

    def _check_for_updates_interactive(self):
        self.btn_check_updates.setText("Checking...")
        self.btn_check_updates.setEnabled(False)
        self.update_checker = AppUpdateChecker()
        self.update_checker.update_available.connect(self._on_update_found)
        self.update_checker.no_update.connect(lambda: self._reset_update_btn("Already latest version."))
        self.update_checker.check_failed.connect(lambda e: self._reset_update_btn("Check failed."))
        self.update_checker.start()

    def _reset_update_btn(self, msg):
        self.btn_check_updates.setText("Check for Updates")
        self.btn_check_updates.setEnabled(True)
        QMessageBox.information(self, "UniGrab Updates", msg)

    def _on_update_found(self, payload):
        self.btn_check_updates.setText("Check for Updates")
        self.btn_check_updates.setEnabled(True)
        new_ver = payload.get("version", "Latest")
        if QMessageBox.question(self, "Update Available", f"Version {new_ver} available for UniGrab.\nDo you want to update now?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            dl_url = payload.get("download_url", "")
            if dl_url:
                self._dispatch_task({"url": dl_url, "title": f"UniGrab_Setup_v{new_ver}", "destination": os.path.expanduser("~/Downloads"), "format": "exe", "is_direct": True})

    def _prompt_new_task(self, url=""):
        self.restore_window()
        dlg = PreDownloadDialog(self, default_url=url)
        if dlg.exec():
            cfg = dlg.get_configuration()
            if cfg.get("url"):
                is_dir, f_type = is_direct_download(cfg["url"])
                cfg["is_direct"] = is_dir
                if is_dir and not cfg.get("format"):
                    cfg["format"] = f_type
                self._dispatch_task(cfg)

    def _dispatch_task(self, cfg, is_restored=False):
        target_row = self.table.rowCount() if is_restored else 0
        self.table.insertRow(target_row)

        display_name = cfg.get("title") or cfg.get("url", "")
        item_title = QTableWidgetItem(display_name)
        item_title.setToolTip(display_name)
        self.table.setItem(target_row, 0, item_title)

        fmt_spec = f"Direct — {cfg.get('format', 'FILE').upper()}" if cfg.get("is_direct") else f"{cfg.get('resolution', 'Best')} - {cfg.get('format', 'MP4').upper()}"
        item_fmt = QTableWidgetItem(fmt_spec)
        item_fmt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(target_row, 1, item_fmt)

        pb_container = QWidget()
        pb_layout = QHBoxLayout(pb_container)
        pb_layout.setContentsMargins(10, 0, 10, 0)
        pb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(int(cfg.get("progress", 0)))
        pb.setFixedSize(140, 22)
        pb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pb_layout.addWidget(pb)

        self.table.setCellWidget(target_row, 2, pb_container)

        status_item = QTableWidgetItem(cfg.get("size_display", "Queued"))
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(target_row, 3, status_item)

        act_widget = QWidget()
        act_layout = QHBoxLayout(act_widget)
        act_layout.setContentsMargins(4, 2, 4, 2)
        act_layout.setSpacing(4)

        btn_pause_resume = QPushButton("Pause")
        btn_stop = QPushButton("Stop")
        btn_stop.setObjectName("btnStop")
        btn_open_folder = QPushButton("Folder")
        btn_open_folder.setObjectName("btnFolder")
        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("btnStop")

        for b in [btn_pause_resume, btn_stop, btn_open_folder, btn_delete]:
            b.setMinimumWidth(64)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            act_layout.addWidget(b)

        self.table.setCellWidget(target_row, 4, act_widget)

        task = {
            "worker": None,
            "cfg": cfg,
            "status_item": status_item,
            "pb": pb,
            "btn_pause_resume": btn_pause_resume,
            "btn_stop": btn_stop,
            "btn_open_folder": btn_open_folder,
            "btn_delete": btn_delete,
            "card_widget": None,
            "final_path": cfg.get("final_path", None),
            "is_paused": False
        }

        if is_restored:
            self.tasks.append(task)
        else:
            self.tasks.insert(0, task)

        card = DownloadCardWidget(task, self._toggle_pause_resume, self._stop_task, self._open_file_folder, self._confirm_and_delete_task)
        task["card_widget"] = card
        self._reposition_cards()

        btn_pause_resume.clicked.connect(lambda checked, t=task: self._toggle_pause_resume(t))
        btn_stop.clicked.connect(lambda checked, t=task: self._stop_task(t))
        btn_open_folder.clicked.connect(lambda checked, t=task: self._open_file_folder(t))
        btn_delete.clicked.connect(lambda checked, t=task: self._confirm_and_delete_task(t))

        if is_restored:
            if cfg.get("status") == "Complete":
                btn_pause_resume.setEnabled(False)
                btn_stop.setEnabled(False)
                card.btn_pause.setEnabled(False)
                card.btn_stop.setEnabled(False)
                return
            btn_pause_resume.setText("Resume")
            card.btn_pause.setText("Resume")
            btn_stop.setEnabled(False)
            card.btn_stop.setEnabled(False)
            return

        # Naya task hamesha direct start hoga
        self._start_worker(task)

    def _reposition_cards(self):
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                self.grid_layout.removeWidget(item.widget())

        cols = 2
        for idx, t in enumerate(self.tasks):
            r = idx // cols
            c = idx % cols
            if t.get("card_widget"):
                self.grid_layout.addWidget(t["card_widget"], r, c)

    def _start_worker(self, task):
        cfg = task["cfg"]
        self._safely_terminate_task(task)

        if cfg.get("is_direct"):
            worker = DirectDownloadWorker(cfg["url"], cfg["destination"], custom_filename=cfg.get("title", ""))
            # direct downloader thread wrapper
            thread = QThread()
            worker.moveToThread(thread)
            task["thread"] = thread
            thread.started.connect(worker.run)
        else:
            fmt = cfg.get("resolution", "")
            if not fmt or "best" in fmt.lower():
                fmt = "bestvideo+bestaudio/best"
            worker = DownloadWorker(
                cfg["url"], cfg["destination"], fmt,
                target_format=cfg.get("format", "mp4"),
                custom_filename=cfg.get("title", ""),
                playlist_items=cfg.get("playlist_items", "")
            )
            task["thread"] = None

        task["worker"] = worker
        task["is_paused"] = False

        task["btn_pause_resume"].setText("Pause")
        task["btn_pause_resume"].setEnabled(True)
        task["btn_stop"].setEnabled(True)
        if task.get("card_widget"):
            task["card_widget"].btn_pause.setText("Pause")
            task["card_widget"].btn_pause.setEnabled(True)
            task["card_widget"].btn_stop.setEnabled(True)

        worker.title_resolved.connect(lambda t, tk=task: self._update_task_title(tk, t))
        worker.progress_changed.connect(lambda d, t=task: self._on_progress_update(t, d))
        worker.status_changed.connect(lambda st, t=task: self._on_status_update(t, st))
        worker.finished.connect(lambda p, t=task: self._handle_download_completed(t, p))
        worker.error_occurred.connect(lambda err, t=task: self._handle_task_error(t, err))

        if task.get("thread"):
            task["thread"].start()
        else:
            worker.start()

        self._save_history()

    def _safely_terminate_task(self, task):
        w = task.get("worker")
        th = task.get("thread")
        if w:
            w.cancel()
            try:
                w.progress_changed.disconnect()
                w.status_changed.disconnect()
                w.finished.disconnect()
                w.error_occurred.disconnect()
            except Exception:
                pass
            if isinstance(w, QThread) and w.isRunning():
                w.quit()
                w.wait(200)
            w.deleteLater()
            task["worker"] = None
        if th:
            if th.isRunning():
                th.quit()
                th.wait(200)
            th.deleteLater()
            task["thread"] = None

    def _on_progress_update(self, task, d):
        pct = int(d.get("percent", 0))
        speed = format_speed(d.get("speed", 0))
        done = d.get("downloaded_str", "")
        total = d.get("total_str", "")
        left = d.get("remaining_str", "")
        eta = format_seconds(d.get("eta", 0))

        if total != "Unknown":
            size_summary = f"{done} / {total} (Left: {left})"
        else:
            size_summary = f"{done} downloaded"

        task["pb"].setValue(pct)
        task["status_item"].setText(f"{size_summary} • {speed} {f'({eta})' if eta else ''}")
        task["cfg"]["progress"] = pct
        task["cfg"]["size_display"] = size_summary

        if task.get("card_widget"):
            task["card_widget"].update_metrics(pct, size_summary, speed, eta or "Downloading")

    def _on_status_update(self, task, st):
        task["status_item"].setText(st)
        task["cfg"]["status"] = st

    def _toggle_pause_resume(self, task):
        w = task.get("worker")
        is_running = w and w.isRunning() if isinstance(w, QThread) else (task.get("thread") and task["thread"].isRunning())

        if is_running and not task["is_paused"]:
            if w:
                w.pause()
            task["is_paused"] = True
            task["btn_pause_resume"].setText("Resume")
            if task.get("card_widget"):
                task["card_widget"].btn_pause.setText("Resume")
            task["status_item"].setText("Paused")
            task["cfg"]["status"] = "Paused"
        elif is_running and task["is_paused"]:
            if w:
                w.resume()
            task["is_paused"] = False
            task["btn_pause_resume"].setText("Pause")
            if task.get("card_widget"):
                task["card_widget"].btn_pause.setText("Pause")
            task["status_item"].setText("Downloading")
            task["cfg"]["status"] = "Downloading"
        else:
            self._start_worker(task)
        self._save_history()

    def _stop_task(self, task):
        w = task.get("worker")
        if w:
            w.cancel()
        task["is_paused"] = False
        task["status_item"].setText("Stopped")
        task["cfg"]["status"] = "Stopped"
        task["btn_pause_resume"].setText("Resume")
        task["btn_pause_resume"].setEnabled(True)
        task["btn_stop"].setEnabled(False)
        if task.get("card_widget"):
            task["card_widget"].btn_pause.setText("Resume")
            task["card_widget"].btn_pause.setEnabled(True)
            task["card_widget"].btn_stop.setEnabled(False)
        self._save_history()

    def _open_file_folder(self, task):
        fp = task.get("final_path")
        dest = os.path.dirname(fp) if fp and os.path.exists(fp) else task["cfg"].get("destination", os.path.expanduser("~/Downloads"))
        os.makedirs(dest, exist_ok=True)
        if sys.platform == "win32":
            if fp and os.path.exists(fp):
                subprocess.run(["explorer", "/select,", os.path.normpath(fp)])
            else:
                os.startfile(os.path.normpath(dest))

    def _confirm_and_delete_task(self, task):
        reply = QMessageBox.question(self, "Delete Task", "Remove this task from UniGrab?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._safely_terminate_task(task)
            for row in range(self.table.rowCount()):
                if self.table.item(row, 3) == task["status_item"]:
                    self.table.removeRow(row)
                    break
            if task.get("card_widget"):
                task["card_widget"].deleteLater()
            if task in self.tasks:
                self.tasks.remove(task)
            self._reposition_cards()
            self._save_history()

    def _handle_download_completed(self, task, final_path):
        self._safely_terminate_task(task)
        task["final_path"] = final_path
        task["status_item"].setText("Complete")
        task["cfg"]["status"] = "Complete"
        task["cfg"]["final_path"] = final_path
        task["cfg"]["progress"] = 100
        task["pb"].setValue(100)
        task["btn_pause_resume"].setEnabled(False)
        task["btn_stop"].setEnabled(False)
        if task.get("card_widget"):
            task["card_widget"].update_metrics(100, "Download Finished", "0 KB/s", "Complete")
            task["card_widget"].btn_pause.setEnabled(False)
            task["card_widget"].btn_stop.setEnabled(False)
        self._save_history()
        self.notifier.trigger_completion("Download Complete", f"Saved: {os.path.basename(final_path)}")

    def _handle_task_error(self, task, err):
        if "TASK_CANCELLED_BY_USER" in err:
            return
        self._safely_terminate_task(task)
        task["status_item"].setText("Failed")
        task["cfg"]["status"] = "Failed"
        task["btn_pause_resume"].setText("Resume")
        task["btn_pause_resume"].setEnabled(True)
        task["btn_stop"].setEnabled(False)
        if task.get("card_widget"):
            task["card_widget"].btn_pause.setText("Resume")
            task["card_widget"].btn_pause.setEnabled(True)
            task["card_widget"].btn_stop.setEnabled(False)
        self._save_history()

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([t["cfg"] for t in self.tasks], f, indent=2)
        except Exception:
            pass

    def _load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history_list = json.load(f)
            for item in history_list:
                if item.get("status") in ["Downloading", "Connecting...", "Queued"]:
                    item["status"] = "Interrupted"
                self._dispatch_task(item, is_restored=True)
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    logo = find_logo()
    if logo:
        app.setWindowIcon(QIcon(logo))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
