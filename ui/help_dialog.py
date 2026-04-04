"""
ui/help_dialog.py — Professional Help dialog with gesture reference and voice commands.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui  import QFont, QColor

from ui.styles import MAIN_STYLE


# ── Gesture data ─────────────────────────────────────────────────
RIGHT_HAND_GESTURES = [
    ("Index finger only extended",        "🟢 Green line",  "Move cursor"),
    ("Mild pinch: Thumb + Index (small gap)", "🟠 Orange line", "Single Click"),
    ("Quick tight pinch + release (<0.25s)", "🔴 Red line",   "Double Click"),
    ("Hold tight pinch (>0.35s)",         "🔴 Red line",   "Drag & Drop"),
    ("Thumb + Middle finger pinch",        "—",             "Right Click"),
    ("Index + Middle extended, move up",   "—",             "Scroll Up"),
    ("Index + Middle extended, move down", "—",             "Scroll Down"),
]

LEFT_HAND_GESTURES = [
    ("Thumb + Index pinch",                     "Immediate", "Alt+Tab (Task Switch)"),
    ("Index finger only — hold 1s",             "1 s hold",  "Copy  (Ctrl+C)"),
    ("Index + Middle fingers — hold 1s",        "1 s hold",  "Paste (Ctrl+V)"),
    ("Closed Fist (all fingers folded) — hold 1s", "1 s hold", "Minimize Window"),
    ("Open Palm (all fingers spread) — hold 1s",   "1 s hold", "Maximize Window"),
    ("Thumb + Index + Middle — hold 1.5s",      "1.5 s hold","Switch to Voice Mode"),
]

VOICE_COMMANDS = [
    # Wake words
    ("Wake Words", "hey assistant / ok assistant / hello system", "Activate voice mode"),
    # Brightness
    ("Brightness", "brightness up / brightness down",         "Adjust screen brightness"),
    ("Brightness", "set brightness 70",                       "Set to specific value"),
    ("Brightness", "max brightness / min brightness",         "Max / Min brightness"),
    # Volume
    ("Volume",     "volume up / volume down",                 "Adjust volume"),
    ("Volume",     "set volume 50",                           "Set to specific value"),
    ("Volume",     "mute / max volume",                       "Mute / Max volume"),
    # Apps — open
    ("Open Apps",  "open chrome / open browser",              "Launch Chrome"),
    ("Open Apps",  "open notepad / open text editor",         "Launch Notepad"),
    ("Open Apps",  "open code / open vscode",                 "Launch VS Code"),
    ("Open Apps",  "open settings / open explorer",           "Launch Settings / Explorer"),
    # Apps — close (NEW)
    ("Close Apps ✨", "chrome closing",                       "Close Google Chrome"),
    ("Close Apps ✨", "vscode closing / visual studio closing","Close VS Code"),
    ("Close Apps ✨", "file explorer closing / explorer closing","Close File Explorer"),
    ("Close Apps ✨", "notepad closing",                       "Close Notepad"),
    # System
    ("System",     "shutdown / power off",                    "Shut down PC"),
    ("System",     "restart / reboot",                        "Restart PC"),
    ("System",     "sleep / hibernate",                       "Sleep mode"),
    ("System",     "lock / lock screen",                      "Lock screen"),
    # Mode switch
    ("Mode",       "switch to gesture / switch mode",         "Return to Gesture Mode"),
]


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GestureVox — Help & Reference")
        self.setMinimumSize(820, 600)
        self.setStyleSheet(MAIN_STYLE)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)

        # Title
        title = QLabel("📖  GestureVox — Gesture & Voice Reference")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color:#1565C0;")
        lay.addWidget(title)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._right_hand_tab(), "✋  Right Hand")
        tabs.addTab(self._left_hand_tab(),  "🤚  Left Hand")
        tabs.addTab(self._voice_tab(),      "🎙  Voice Commands")
        tabs.addTab(self._tips_tab(),       "💡  Tips")
        lay.addWidget(tabs)

        # Close button
        close_btn = QPushButton("✕  Close")
        close_btn.setObjectName("btn_stop")
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        lay.addLayout(row)

    # ── Tab builders ─────────────────────────────────────────────
    def _right_hand_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(8)

        intro = QLabel(
            "Right hand controls the <b>mouse cursor</b>. "
            "Extend only your <b>index finger</b> to enter cursor mode.\n"
            "The line between thumb and index finger changes colour to show pinch state."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        # Visual pinch guide
        lay.addWidget(self._pinch_guide())

        lay.addWidget(self._make_table(
            ["Gesture / Hand Shape", "Visual Indicator", "Action"],
            RIGHT_HAND_GESTURES,
        ))
        lay.addStretch()
        w.setWidget(inner)
        return w

    def _left_hand_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(8)

        intro = QLabel(
            "Left hand controls <b>system actions</b>. "
            "Hold gestures steady for the required time — a progress bar will appear at the top of the app.\n"
            "New gestures (Copy, Paste, Minimize, Maximize) require a <b>1-second hold</b> to prevent accidental triggers."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        lay.addWidget(self._make_table(
            ["Gesture / Hand Shape", "Hold Time", "Action"],
            LEFT_HAND_GESTURES,
        ))

        note = QLabel(
            "⚠  During Alt+Tab (pinch), Copy/Paste/Minimize/Maximize are disabled to prevent conflicts."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background:#FFF3E0; color:#E65100; border:1px solid #FFCC02;"
            "border-radius:6px; padding:8px; font-size:11px;"
        )
        lay.addWidget(note)
        lay.addStretch()
        w.setWidget(inner)
        return w

    def _voice_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(8)

        intro = QLabel(
            "Voice mode uses a fully <b>offline</b> speech engine (VOSK). "
            "First say a <b>wake word</b>, then speak your command clearly.\n"
            "Commands marked ✨ are new additions."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        lay.addWidget(self._make_table(
            ["Category", "Say This", "Result"],
            VOICE_COMMANDS,
        ))
        lay.addStretch()
        w.setWidget(inner)
        return w

    def _tips_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)

        tips = [
            ("💡", "Lighting",
             "Ensure your hand is well-lit. The system works best in normal room lighting."),
            ("📏", "Distance",
             "Keep your hand 30–60 cm from the camera for best detection accuracy."),
            ("🖱️", "Single Click",
             "Bring thumb and index CLOSE (orange line appears) then release. Don't squeeze too tight."),
            ("👆", "Double Click",
             "Make the RED line appear (very close thumb+index), then QUICKLY open your fingers (<0.25s)."),
            ("📂", "Drag & Drop",
             "Make RED line appear and HOLD for 0.35+ seconds. Move your hand to drag, then release pinch."),
            ("🔇", "Minimize/Maximize",
             "Hold your fist or open palm STILL for 1 full second. A progress bar shows hold time."),
            ("📋", "Copy & Paste",
             "Point only your index finger (Copy) or index+middle (Paste) and hold steady for 1 second."),
            ("🔄", "Switch to Voice",
             "On LEFT hand: extend Thumb + Index + Middle (3 fingers), keep Ring and Pinky folded. Hold 1.5s."),
            ("🎙️", "Voice Commands",
             "Say wake word FIRST, wait for the beep, THEN say your command clearly and slowly."),
            ("⚡", "Sensitivity",
             "Cursor sensitivity matches the original vision_working.py (cfg.sensitivity). Edit gesture/config.py to tune."),
        ]

        for icon, title, desc in tips:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet("QFrame#card{background:#FFFFFF; border:1px solid #E0E0E0; border-radius:8px; padding:4px;}")
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 8, 12, 8)
            row.setSpacing(12)

            ic = QLabel(icon)
            ic.setFont(QFont("Segoe UI Emoji", 18))
            ic.setFixedWidth(36)

            text_col = QVBoxLayout()
            tl = QLabel(f"<b>{title}</b>")
            tl.setStyleSheet("color:#1565C0; font-size:12px;")
            dl = QLabel(desc)
            dl.setWordWrap(True)
            dl.setStyleSheet("color:#37474F; font-size:11px;")
            text_col.addWidget(tl)
            text_col.addWidget(dl)

            row.addWidget(ic)
            row.addLayout(text_col)
            lay.addWidget(card)

        lay.addStretch()
        w.setWidget(inner)
        return w

    # ── Helpers ───────────────────────────────────────────────────
    def _make_table(self, headers, rows):
        tbl = QTableWidget(len(rows), len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet("""
            QTableWidget {
                border:1px solid #E0E0E0; border-radius:6px;
                font-family:'Segoe UI',Arial; font-size:11px; color:#212121;
                gridline-color:#F0F0F0;
            }
            QHeaderView::section {
                background:#1565C0; color:#FFFFFF;
                font-weight:bold; font-size:11px;
                padding:6px; border:none;
            }
            QTableWidget::item:alternate { background:#F3F8FE; }
            QTableWidget::item:selected  { background:#BBDEFB; color:#0D47A1; }
        """)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                tbl.setItem(r, c, item)
        tbl.resizeRowsToContents()
        return tbl

    def _pinch_guide(self):
        frame = QFrame()
        frame.setStyleSheet(
            "background:#E3F2FD; border:1px solid #90CAF9; border-radius:8px;"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(24)

        for color, label, action in [
            ("#4CAF50", "🟢  Green",  "Move cursor freely"),
            ("#FF9800", "🟠  Orange", "Single Click"),
            ("#F44336", "🔴  Red",    "Double Click / Drag"),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI Emoji", 13))
            lbl.setAlignment(Qt.AlignCenter)
            act = QLabel(action)
            act.setStyleSheet(f"color:{color}; font-weight:bold; font-size:11px;")
            act.setAlignment(Qt.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(act)
            lay.addLayout(col)

        return frame
