"""ui/help_dialog.py - Help dialog with gesture reference and section-wise voice command browser."""

from pathlib import Path
import json
from collections import OrderedDict
from typing import List, Tuple, Dict

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QScrollArea,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QToolBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.styles import MAIN_STYLE


RIGHT_HAND_GESTURES = [
    ("Index finger only extended", "Green line", "Move cursor"),
    ("Mild pinch: thumb + index", "Orange line", "Single click"),
    ("Quick tight pinch release (<0.25s)", "Red line", "Double click"),
    ("Hold tight pinch (>0.35s)", "Red line", "Drag and drop"),
    (
        "Thumb + middle pinch (hold 0.7s) with index/ring/pinky extended",
        "Gesture confirm",
        "Right click",
    ),
    ("Index + middle extended, move hand up", "Scroll mode", "Scroll up"),
    ("Index + middle extended, move hand down", "Scroll mode", "Scroll down"),
]

LEFT_HAND_GESTURES = [
    (
        "Thumb-index pinch + middle/ring/pinky extended (hold 1s)",
        "1s hold",
        "Alt+Tab switch",
    ),
    ("Pinky only extended (hold 1s)", "1s hold", "Copy (Ctrl+C)"),
    ("Ring + pinky extended (hold 1s)", "1s hold", "Paste (Ctrl+V)"),
    ("Thumb only extended (hold 1s)", "1s hold", "Minimize window"),
    ("Open palm (all fingers extended, hold 1s)", "1s hold", "Maximize window"),
    (
        "Ring + pinky extended, thumb/index/middle closed (hold 1.5s)",
        "1.5s hold",
        "Switch to voice mode",
    ),
    (
        "Both left and right fists closed (hold 3s)",
        "3s hold",
        "Exit G-Vox",
    ),
]


def _load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _pretty_category(name: str) -> str:
    mapping = {
        "brightness": "Brightness",
        "volume": "Volume",
        "app_launcher": "Applications",
        "system_control": "System",
        "help": "Help",
        "wake_word": "Wake Words",
        "mode": "Mode",
        "shortcut": "Shortcuts",
    }
    return mapping.get(name, name.replace("_", " ").title())


def _shortcut_result(phrase: str) -> str:
    p = phrase.strip().lower()

    if p in {"open", "enter", "open selected", "open selected item"}:
        return "Press Enter"
    if p == "screenshot":
        return "Capture full screenshot"
    if p == "open file":
        return "Open file dialog"
    if p == "close file":
        return "Close current file/tab"
    if p == "close":
        return "Close current window"
    if p == "minimize":
        return "Minimize window"
    if p == "maximize":
        return "Maximize window"
    if p == "zoom in":
        return "Zoom in"
    if p == "zoom out":
        return "Zoom out"
    if p in {"next image", "next page", "next"}:
        return "Navigate forward"
    if p in {"previous image", "previous page", "previous"}:
        return "Navigate backward"
    if p in {"up", "down", "left", "right"}:
        return "Arrow key navigation"
    if p in {"scroll up", "scroll down"}:
        return "Scrolling"
    if p in {"play", "pause", "play video", "pause video"}:
        return "Play or pause media"
    if p == "next track":
        return "Next media track"
    if p == "previous track":
        return "Previous media track"
    if p == "go back":
        return "Navigate back (Alt+Left / Backspace)"
    if p == "copy":
        return "Copy (Ctrl+C)"
    if p == "paste":
        return "Paste (Ctrl+V)"
    if p in {"exit gvox", "exit g vox"}:
        return "Close G-Vox"

    return "Execute shortcut"


def _load_voice_commands() -> List[Tuple[str, str, str]]:
    root = Path(__file__).resolve().parent.parent
    commands_cfg = _load_json(root / "voice_assistant" / "config" / "commands.json")
    settings_cfg = _load_json(root / "voice_assistant" / "config" / "voice_settings.json")

    rows: List[Tuple[str, str, str]] = []
    seen = set()

    def add_row(category: str, phrase: str, result: str) -> None:
        phrase = (phrase or "").strip().lower()
        result = (result or "").strip()
        if not phrase:
            return
        key = (category, phrase, result)
        if key in seen:
            return
        seen.add(key)
        rows.append((category, phrase, result))

    for ww in settings_cfg.get("wake_words", []):
        add_row("Wake Words", str(ww), "Activate voice assistant")

    for cat_name, cat_cfg in commands_cfg.items():
        actions = cat_cfg.get("actions", {}) if isinstance(cat_cfg, dict) else {}
        category = _pretty_category(cat_name)

        for _, action_cfg in actions.items():
            desc = str(action_cfg.get("description", "Execute action"))
            for phrase in action_cfg.get("patterns", []):
                add_row(category, str(phrase), desc)

    add_row("Mode", "switch to gesture", "Switch to gesture mode")
    add_row("Mode", "switch gesture", "Switch to gesture mode")
    add_row("Mode", "switch mode", "Switch to gesture mode")

    try:
        from extensions.voice_shortcut_commands import ADDITIONAL_PHRASES
    except Exception:
        ADDITIONAL_PHRASES = []

    for phrase in ADDITIONAL_PHRASES:
        add_row("Shortcuts", str(phrase), _shortcut_result(str(phrase)))

    return rows


def _group_voice_commands(rows: List[Tuple[str, str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    grouped: OrderedDict[str, List[Tuple[str, str]]] = OrderedDict()
    for category, phrase, result in rows:
        grouped.setdefault(category, []).append((phrase, result))
    return grouped


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.voice_commands = _load_voice_commands()
        self.setWindowTitle("G-Vox - Help and Reference")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(MAIN_STYLE)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 12)
        lay.setSpacing(10)

        title = QLabel("G-Vox - Gesture and Voice Reference")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color:#1565C0;")
        lay.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._right_hand_tab(), "Right Hand")
        tabs.addTab(self._left_hand_tab(), "Left Hand")
        tabs.addTab(self._voice_tab(), "Voice Commands")
        tabs.addTab(self._tips_tab(), "Tips")
        lay.addWidget(tabs, 1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("btn_stop")
        close_btn.setFixedWidth(140)
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        lay.addLayout(row)

    def _right_hand_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(8)

        intro = QLabel(
            "Right hand drives pointer and click control. Keep hand visible and steady for best recognition."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        lay.addWidget(
            self._make_table(
                ["Gesture / Hand Shape", "Indicator", "Action"],
                RIGHT_HAND_GESTURES,
            )
        )
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
            "Left hand controls system actions. Hold gestures for required duration to confirm actions."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        lay.addWidget(
            self._make_table(
                ["Gesture / Hand Shape", "Hold Time", "Action"],
                LEFT_HAND_GESTURES,
            )
        )

        lay.addStretch()
        w.setWidget(inner)
        return w

    def _voice_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        total = len(self.voice_commands)
        intro = QLabel(
            f"Voice commands are grouped section-wise. Total available phrases: {total}."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#37474F; font-size:12px; padding:4px;")
        lay.addWidget(intro)

        grouped = _group_voice_commands(self.voice_commands)

        toolbox = QToolBox()
        toolbox.setObjectName("voice_toolbox")
        for category, items in grouped.items():
            section = QWidget()
            sec_lay = QVBoxLayout(section)
            sec_lay.setContentsMargins(6, 6, 6, 6)
            sec_lay.setSpacing(6)

            tbl = QTableWidget(len(items), 2)
            tbl.setHorizontalHeaderLabels(["Say This", "Result"])
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tbl.verticalHeader().setVisible(False)
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.setAlternatingRowColors(True)
            tbl.setStyleSheet(
                """
                QTableWidget {
                    border:1px solid #E0E0E0;
                    border-radius:6px;
                    font-family:'Segoe UI',Arial;
                    font-size:11px;
                    color:#212121;
                    gridline-color:#F0F0F0;
                }
                QHeaderView::section {
                    background:#1565C0;
                    color:#FFFFFF;
                    font-weight:bold;
                    font-size:11px;
                    padding:6px;
                    border:none;
                }
                QTableWidget::item:alternate { background:#F3F8FE; }
                QTableWidget::item:selected  { background:#BBDEFB; color:#0D47A1; }
                """
            )

            for r, (phrase, result) in enumerate(items):
                p_item = QTableWidgetItem(phrase)
                p_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                tbl.setItem(r, 0, p_item)

                r_item = QTableWidgetItem(result)
                r_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                tbl.setItem(r, 1, r_item)

            tbl.resizeRowsToContents()
            sec_lay.addWidget(tbl)
            toolbox.addItem(section, f"{category} ({len(items)})")

        lay.addWidget(toolbox, 1)
        return page

    def _tips_tab(self):
        w = QScrollArea()
        w.setWidgetResizable(True)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)

        tips = [
            ("Lighting", "Use stable lighting so finger shapes are visible."),
            ("Distance", "Keep hands around 30 to 60 cm from camera."),
            ("Steadiness", "For hold gestures (1s/1.5s), keep hand still until action confirms."),
            ("Voice", "Say wake word first, then command clearly."),
            ("Mode switch", "Use left-hand switch gesture or voice phrase 'switch to gesture'."),
        ]

        for title, desc in tips:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(
                "QFrame#card{background:#FFFFFF; border:1px solid #E0E0E0; border-radius:8px; padding:4px;}"
            )
            row = QVBoxLayout(card)
            row.setContentsMargins(12, 8, 12, 8)
            row.setSpacing(4)

            tl = QLabel(f"<b>{title}</b>")
            tl.setStyleSheet("color:#1565C0; font-size:12px;")
            dl = QLabel(desc)
            dl.setWordWrap(True)
            dl.setStyleSheet("color:#37474F; font-size:11px;")
            row.addWidget(tl)
            row.addWidget(dl)

            lay.addWidget(card)

        lay.addStretch()
        w.setWidget(inner)
        return w

    def _make_table(self, headers, rows):
        tbl = QTableWidget(len(rows), len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            """
            QTableWidget {
                border:1px solid #E0E0E0;
                border-radius:6px;
                font-family:'Segoe UI',Arial;
                font-size:11px;
                color:#212121;
                gridline-color:#F0F0F0;
            }
            QHeaderView::section {
                background:#1565C0;
                color:#FFFFFF;
                font-weight:bold;
                font-size:11px;
                padding:6px;
                border:none;
            }
            QTableWidget::item:alternate { background:#F3F8FE; }
            QTableWidget::item:selected  { background:#BBDEFB; color:#0D47A1; }
            """
        )

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                tbl.setItem(r, c, item)

        tbl.resizeRowsToContents()
        return tbl
