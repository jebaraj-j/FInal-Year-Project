"""ui/styles.py - Industrial visual system for the GestureVox desktop UI."""

MAIN_STYLE = """
QMainWindow, QWidget#central {
    background: qradialgradient(cx:0.18, cy:0.04, radius:1.2,
        fx:0.18, fy:0.05,
        stop:0 #F7FAFF, stop:0.58 #EEF3FB, stop:1 #DDE6F2);
    color: #162339;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI";
}

QWidget#body_wrap {
    background: transparent;
}

/* Header */
QWidget#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #071C3A, stop:0.52 #0A2E57, stop:1 #0E3C72);
    border-bottom: 1px solid #2B5E98;
}
QLabel#app_title {
    color: #F3F9FF;
    font-size: 29px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
QLabel#app_subtitle {
    color: #A6C2E3;
    font-size: 12px;
    font-weight: 500;
}
QLabel#system_state {
    color: #C9DEFA;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(196, 219, 244, 0.38);
    border-radius: 14px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#mode_badge {
    border-radius: 14px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.4px;
}
QLabel#mode_badge[mode="gesture"] {
    color: #E6F4FF;
    background: #0E5FA8;
    border: 1px solid #7EC0F4;
}
QLabel#mode_badge[mode="voice"] {
    color: #F2F7FF;
    background: #2A4060;
    border: 1px solid #9EB6D6;
}
QLabel#mode_badge[mode="stopped"] {
    color: #FFEFF0;
    background: #8A1D2E;
    border: 1px solid #F28A98;
}

/* Generic panel cards */
QFrame#camera_card, QFrame#controls_card, QFrame#recognition_card, QFrame#log_card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #F8FBFF);
    border: 1px solid #C9D8EA;
    border-radius: 14px;
}

QLabel#section_bar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1E4D8A, stop:1 #2D67AF);
    color: #F7FBFF;
    border: 1px solid #3E77BC;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 21px;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QLabel#card_title {
    color: #1E4C87;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

/* Camera */
QLabel#camera_label {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0B1526, stop:1 #1A2E4A);
    border: 2px solid #2D5D93;
    border-radius: 12px;
    color: #D8E9FA;
    font-size: 16px;
    padding: 10px;
}
QLabel#meta_label {
    color: #466081;
    font-size: 11px;
    font-weight: 700;
}
QLabel#meta_value {
    color: #1A2942;
    font-size: 11px;
    font-weight: 600;
}
QLabel#status_ok {
    background: #E7F8EC;
    color: #1D7A45;
    border: 1px solid #8CD3A7;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#status_bad {
    background: #FFF0F0;
    color: #AE2C3E;
    border: 1px solid #E6A4AE;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}

/* Mode tiles */
QPushButton#tile_gesture, QPushButton#tile_voice {
    border-radius: 12px;
    padding: 10px;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 0.4px;
}
QPushButton#tile_gesture {
    color: #F4FAFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1A5AA0, stop:1 #3073BD);
    border: 1px solid #528ECF;
}
QPushButton#tile_gesture:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2168B4, stop:1 #3A82CE);
}
QPushButton#tile_gesture:checked {
    border: 2px solid #A7D5FF;
}

QPushButton#tile_voice {
    color: #F8FBFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2B4C73, stop:1 #3C638F);
    border: 1px solid #6E8FB6;
}
QPushButton#tile_voice:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #335A87, stop:1 #4875A7);
}
QPushButton#tile_voice:checked {
    border: 2px solid #B8D2EE;
}

QPushButton#btn_stop, QPushButton#btn_help, QPushButton#btn_clear, QPushButton#btn_help_header {
    border-radius: 9px;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 12px;
}
QPushButton#btn_stop {
    color: #FFFFFF;
    background: #B7394F;
    border: 1px solid #CB5D70;
}
QPushButton#btn_stop:hover {
    background: #C6465D;
}
QPushButton#btn_help, QPushButton#btn_help_header {
    color: #204774;
    background: #EEF5FE;
    border: 1px solid #8CB3DE;
}
QPushButton#btn_help:hover, QPushButton#btn_help_header:hover {
    background: #DFEEFD;
}
QPushButton#btn_clear {
    color: #284C77;
    background: #ECF2FA;
    border: 1px solid #A5BDD8;
}
QPushButton#btn_clear:hover {
    background: #DDEAF8;
}

/* Recognition panel */
QLabel#gesture_name {
    color: #163761;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 0.3px;
}
QLabel#gesture_sub {
    color: #4B6281;
    font-size: 12px;
    font-weight: 500;
}
QLabel#confidence_lbl {
    color: #243D5D;
    font-size: 12px;
    font-weight: 700;
}
QProgressBar {
    border: 1px solid #9BB6D3;
    border-radius: 5px;
    background: #EAF1FB;
}
QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2E6BB1, stop:1 #57A1EA);
}

/* Log */
QTextEdit#action_log {
    background: #FBFDFF;
    color: #182640;
    border: 1px solid #BED0E6;
    border-radius: 12px;
    padding: 8px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 11px;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #A8BDD7;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status bar */
QStatusBar {
    background: #133864;
    color: #EEF6FF;
    border-top: 1px solid #2A5A8E;
    font-size: 11px;
    font-weight: 600;
}

/* Help dialog fallback styling */
QDialog {
    background: #F2F6FC;
}
QTabWidget::pane {
    border: 1px solid #CBD9EB;
    border-radius: 8px;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #E8F0FA;
    color: #244A76;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 2px;
    font-size: 11px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #2C5F98;
    color: #F5FAFF;
}
"""
