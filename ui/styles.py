MODERN_NEON_DARK_THEME = """
QMainWindow, QWidget#centralWidget {
    background-color: #0B0F19;
    color: #F8FAFC;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

QFrame#topCard {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
}

QPushButton {
    background-color: #10B981;
    color: #FFFFFF;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #059669;
}
QPushButton:pressed {
    background-color: #047857;
}

QPushButton#btnToggleView {
    background-color: #1F2937;
    color: #F3F4F6;
    border: 1px solid #374151;
}
QPushButton#btnToggleView:hover {
    background-color: #374151;
}

QPushButton#btnStop {
    background-color: #EF4444;
}
QPushButton#btnStop:hover {
    background-color: #DC2626;
}

QPushButton#btnFolder {
    background-color: #3B82F6;
}
QPushButton#btnFolder:hover {
    background-color: #2563EB;
}

QTableWidget {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    gridline-color: #1F2937;
    selection-background-color: #1E293B;
    selection-color: #F8FAFC;
    color: #E2E8F0;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 8px;
    font-weight: 700;
    border: none;
    border-bottom: 2px solid #1E293B;
}

QProgressBar {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #06B6D4);
    border-radius: 5px;
}

QFrame.downloadCard {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 14px;
}
QFrame.downloadCard:hover {
    border: 1px solid #374151;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
"""
