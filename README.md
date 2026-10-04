# UniGrab Studio 🚀
### Universal Multimedia Workstation & High-Speed Downloader

UniGrab Studio is a modern, high-performance desktop media manager engineered in Python and PyQt6. Designed with dual-view ergonomics, real-time chunk streaming, background persistence, and Chromium Manifest V3 browser integration.

---

## 🌟 Features

* **Universal Media Engine:** High-speed extraction for YouTube, TikTok, Instagram, Facebook, Vimeo, and 1,000+ streaming sites via yt-dlp.
* **Direct File Sniffing:** Multithreaded chunk downloads for direct binary assets (.exe, .zip, .tar.gz, .iso, .mp4, etc.).
* **Dual-View Ergonomics:** Switch seamlessly between a clean **Table Rows View** and a modern **Card Grid View**.
* **Accurate Size Breakdown:** Real-time metrics showing downloaded size, total size, speed, ETA, and remaining volume.
* **Top-Pinned Queue:** Newly added downloads automatically appear at the very top of your queue.
* **Bot-Detection Mitigation:** Client failovers (android, web) to prevent speed throttling and bot blocks.
* **Windows Path Sanitizer:** Prevents Windows MAX_PATH limitations by sanitizing illegal file characters.
* **Background Tray Mode:** Minimizes to the Windows System Tray to keep downloads running in the background.

---

## 🏗️ Architecture & Directory Overview

```text
UniGrab/
├── assets/
│   ├── logo.ico                # Desktop application icon
│   └── logo.png                # Window & branding graphics
├── core/
│   ├── app_updater.py          # GitHub raw version schema inspector
│   ├── direct_downloader.py    # Direct chunked file streaming worker
│   ├── downloader.py           # Adaptive yt-dlp QThread worker engine
│   ├── ipc_server.py           # Local HTTP endpoint (127.0.0.1:49814)
│   ├── os_notifier.py          # Native Windows desktop notifications
│   └── url_sniffer.py          # Direct link & MIME-type detection
├── extension/
│   ├── background.js           # Chromium context menu handler & IPC dispatcher
│   └── manifest.json           # Manifest V3 configuration
├── ui/
│   ├── pre_download_dialog.py  # Format selection & metadata dialog
│   └── styles.py               # Modern neon dark QSS styling
├── main.py                     # Workstation entry point & UI controller
├── setup_script.iss            # Inno Setup installation script
├── version.json                # Remote update tracking schema
└── requirements.txt            # Python runtime dependencies
```

---

## ⚡ Getting Started

### Prerequisites
* Windows 10 / 11 (64-bit recommended)
* Python 3.10+
* FFmpeg configured in your system PATH

### 1. Clone the Repository
```bash
git clone https://github.com/alikhan422/UniGrab.git
cd UniGrab
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Application
```bash
python main.py
```

---

## 🧩 Browser Extension Setup

1. Open your browser and go to `chrome://extensions/` (or `edge://extensions/`).
2. Toggle on **Developer mode** in the top-right corner.
3. Click **Load unpacked**.
4. Select the `extension` folder inside the UniGrab repository.
5. Right-click any media or link on the web and select **"Download with UniGrab"**.

---

## 📦 Building the Standalone Installer

```powershell
# 1. Compile bundle with PyInstaller
pyinstaller --noconfirm --onedir --windowed --name "UniGrab" --icon "assets/logo.ico" --add-data "assets;assets" --add-data "ui;ui" --add-data "core;core" main.py

# 2. Build setup installer (.exe) with Inno Setup
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "setup_script.iss"
```

---

## ⚖️ License
Distributed under the **MIT License**.