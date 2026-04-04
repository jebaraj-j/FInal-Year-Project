"""ui/styles.py — Professional QSS stylesheet (white/blue/black palette)."""

MAIN_STYLE = """
QMainWindow, QWidget#central {
    background: #F5F7FA;
}

/* ── Header ── */
QWidget#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1565C0, stop:1 #0D47A1);
    border-radius: 0px;
}
QLabel#app_title {
    color: #FFFFFF;
    font-size: 20px;
    font-weight: bold;
    font-family: 'Segoe UI', Arial;
}
QLabel#app_subtitle {
    color: #90CAF9;
    font-size: 11px;
    font-family: 'Segoe UI', Arial;
}

/* ── Mode Badge ── */
QLabel#mode_badge {
    background: #0D47A1;
    color: #FFFFFF;
    border: 2px solid #42A5F5;
    border-radius: 12px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: bold;
    font-family: 'Segoe UI', Arial;
}

/* ── Cards ── */
QFrame#card {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 10px;
}
QLabel#card_title {
    color: #1565C0;
    font-size: 12px;
    font-weight: bold;
    font-family: 'Segoe UI', Arial;
    border-bottom: 2px solid #E3F2FD;
    padding-bottom: 4px;
}

/* ── Camera ── */
QLabel#camera_label {
    background: #0A0A1A;
    border: 2px solid #1565C0;
    border-radius: 8px;
    color: #90CAF9;
    font-size: 13px;
    font-family: 'Segoe UI', Arial;
}

/* ── Gesture Info ── */
QLabel#gesture_name {
    color: #0D47A1;
    font-size: 22px;
    font-weight: bold;
    font-family: 'Segoe UI', Arial;
}
QLabel#gesture_sub {
    color: #546E7A;
    font-size: 12px;
    font-family: 'Segoe UI', Arial;
}
QLabel#confidence_lbl {
    color: #37474F;
    font-size: 11px;
    font-family: 'Segoe UI', Arial;
}

/* ── Buttons ── */
QPushButton {
    font-family: 'Segoe UI', Arial;
    font-size: 12px;
    font-weight: bold;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}
QPushButton#btn_gesture {
    background: #1565C0;
    color: #FFFFFF;
}
QPushButton#btn_gesture:hover  { background: #1976D2; }
QPushButton#btn_gesture:pressed { background: #0D47A1; }

QPushButton#btn_voice {
    background: #212121;
    color: #FFFFFF;
}
QPushButton#btn_voice:hover  { background: #424242; }
QPushButton#btn_voice:pressed { background: #000000; }

QPushButton#btn_stop {
    background: #C62828;
    color: #FFFFFF;
}
QPushButton#btn_stop:hover  { background: #D32F2F; }
QPushButton#btn_stop:pressed { background: #B71C1C; }

QPushButton#btn_help {
    background: #F5F5F5;
    color: #1565C0;
    border: 2px solid #1565C0;
}
QPushButton#btn_help:hover  { background: #E3F2FD; }
QPushButton#btn_help:pressed { background: #BBDEFB; }

/* ── Action Log ── */
QTextEdit#action_log {
    background: #0A0A1A;
    color: #64FFDA;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    border: 1px solid #1565C0;
    border-radius: 6px;
    padding: 4px;
}

/* ── Status bar ── */
QStatusBar {
    background: #1565C0;
    color: #FFFFFF;
    font-family: 'Segoe UI', Arial;
    font-size: 11px;
}

/* ── Help Dialog ── */
QDialog {
    background: #F5F7FA;
}
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #E3F2FD;
    color: #1565C0;
    font-family: 'Segoe UI', Arial;
    font-size: 11px;
    font-weight: bold;
    padding: 8px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1565C0;
    color: #FFFFFF;
}
QScrollBar:vertical {
    background: #F5F7FA;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #1565C0;
    border-radius: 4px;
}
QProgressBar {
    border: 1px solid #1565C0;
    border-radius: 4px;
    background: #E3F2FD;
    text-align: center;
    color: #1565C0;
    font-size: 10px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1565C0, stop:1 #42A5F5);
    border-radius: 4px;
}
"""
