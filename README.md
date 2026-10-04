# UniGrab Studio 🚀
### Universal Multimedia Workstation & High-Speed Downloader

UniGrab Studio is a full-featured desktop download management workstation built with Python and PyQt6. Designed as a modern, extensible alternative to traditional download managers, it provides high-throughput media streaming extraction via `yt-dlp`, direct file sniffing, real-time metadata pre-fetching, system tray persistence, and seamless browser integration via Manifest V3.

✨ Features
Universal Media Engine: Native support for YouTube, TikTok, Instagram, Facebook, Vimeo, and over 1,000+ supported streaming platforms via yt-dlp.

Direct File Sniffing: Automatic detection and multithreaded chunk downloads for direct binary assets (.exe, .zip, .tar.gz, .iso, .mp4, etc.).

Sub-Second Fast Pre-Fetch: Optimized flat-extraction pipeline with a 400ms debounce timer to instantly populate media titles and resolution profiles upon pasting URLs.

Bot-Detection Mitigation: Built-in player client failovers (android, ios, web) and automatic browser cookie authentication (chrome) to bypass rate-limiting and sign-in verification screens.

Automated Directory Organization: Cleanses and sanitizes video/audio titles to create dedicated subdirectories per job inside the target download path.

System Tray Integration: Background execution support ("Minimize to Tray") ensuring background downloads remain uninterrupted when closing the main window.

Manifest V3 Browser Integration: Companion Chromium extension enabling right-click context menu downloads and active-tab transfers over a local IPC server (127.0.0.1:49814).

Interactive In-App Updates: Integrated update checker that inspects hosted remote version schemas (version.json) and dispatches new setup binaries directly into the internal download queue.

Modern Neon Dark Interface: Ergonomic, responsive PyQt6 graphical user interface with per-task progress tracking, real-time speed calculation, and responsive controls.

🏗️ Architecture & Directory Overview
UniGrab/
├── assets/                     # Graphical branding, icons, and logo assets
├── core/
│   ├── app_updater.py          # Remote version verification and update dispatcher
│   ├── direct_downloader.py    # Direct chunked HTTP/HTTPS streaming engine
│   ├── downloader.py           # yt-dlp media extraction worker with bot bypass
│   ├── engine_updater.py       # Core binary and runtime dependency manager
│   ├── ipc_server.py           # Local HTTP endpoint listening on port 49814
│   ├── os_notifier.py          # Native Windows desktop notification hooks
│   └── url_sniffer.py          # MIME-type and direct link detection module
├── extension/                  # Chromium Manifest V3 browser integration
│   ├── background.js           # Background service worker & context menu actions
│   └── manifest.json           # Extension configuration and permission manifest
├── ui/
│   ├── pre_download_dialog.py  # Modal dialog for job configuration & metadata pre-fetch
│   └── styles.py               # Custom QSS stylesheet definitions
├── history.json                # Persistent task and job state store
├── main.py                     # Workstation entry point and main event loop
├── setup_script.iss            # Inno Setup installation wizard configuration
└── README.md
⚡ Getting Started
Prerequisites
Python 3.10+ (64-bit recommended)

FFmpeg installed and configured in your system PATH

Google Chrome or any Chromium-based browser (for extension integration)

Installation
1. Clone the repository:
git clone [https://github.com/alikhan422/UniGrab.git](https://github.com/alikhan422/UniGrab.git)
cd UniGrab
2. Create and activate a virtual environment (optional but recommended):
python -m venv venv
.\venv\Scripts\activate
3. Install dependencies:
pip install PyQt6 yt-dlp requests pyinstaller
4. Launch the application:
python main.py

🔌 Browser Extension Setup
Open your Chromium-based browser and navigate to chrome://extensions/.

Enable the Developer mode toggle in the top-right corner.

Click the Load unpacked button.

Select the extension/ directory located inside your local UniGrab project folder.

Right-click any video, audio, or download link on the web and select "Download with UniGrab" to transfer the task directly to the workstation.

📦 Distribution & Installer Compilation
To generate a standalone Windows installer with a complete 4-step wizard (Welcome, EULA, Desktop Shortcut, and 1%–100% Extraction Progress):

Step 1: Bundle with PyInstaller
pyinstaller --noconfirm --onedir --windowed `
  --name "UniGrab" `
  --icon "assets/logo.ico" `
  --add-data "assets;assets" `
  --add-data "ui;ui" `
  --add-data "core;core" `
  main.py

Step 2: Compile with Inno Setup
PowerShell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup_script.iss
The compiled setup package will be located at Installer_Output/UniGrab_Setup_v1.0.exe.

⚖️ License & Disclaimer
This project is licensed under the MIT License. UniGrab Studio is intended strictly for personal archiving and fair use. Users are responsible for complying with the terms of service of any third-party website or content provider.
