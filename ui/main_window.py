"""
ui/main_window.py — Professional PyQt5 main window.
White / Blue / Black palette. Live camera + gesture info + controls.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QVBoxLayout, QFrame, QStatusBar, QProgressBar,
    QSizePolicy,
)
from PyQt5.QtCore  import Qt, pyqtSignal, QSize
from PyQt5.QtGui   import QImage, QPixmap, QFont, QIcon, QColor

from ui.styles       import MAIN_STYLE
from ui.notification import NotificationWidget


class MainWindow(QMainWindow):
    """Main application window."""

    gesture_mode_requested = pyqtSignal()
    voice_mode_requested   = pyqtSignal()
    stop_requested         = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GestureVox — Intelligent Control System")
        self.setMinimumSize(1100, 680)
        self.setStyleSheet(MAIN_STYLE)
        self._build_ui()

    # ──────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(12)
        body.addWidget(self._build_camera_panel(), 3)
        body.addWidget(self._build_right_panel(), 2)
        root.addLayout(body)

        # Status bar
        self._status = QStatusBar()
        self._status.showMessage("  ✅  Ready — Gesture Mode will start automatically")
        self.setStatusBar(self._status)

    # ── Header ────────────────────────────────────────────────────
    def _build_header(self):
        hdr = QWidget()
        hdr.setObjectName("header")
        hdr.setFixedHeight(64)
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel("🖐  GestureVox")
        title.setObjectName("app_title")
        sub   = QLabel("Intelligent Gesture & Voice Control System")
        sub.setObjectName("app_subtitle")

        self.mode_badge = QLabel("● GESTURE MODE")
        self.mode_badge.setObjectName("mode_badge")

        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addStretch()
        lay.addWidget(self.mode_badge)
        return hdr

    # ── Camera panel ──────────────────────────────────────────────
    def _build_camera_panel(self):
        card = QFrame()
        card.setObjectName("card")
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        t = QLabel("📷  Live Camera Feed")
        t.setObjectName("card_title")
        lay.addWidget(t)

        self.camera_label = QLabel("Camera initialising…")
        self.camera_label.setObjectName("camera_label")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.camera_label)

        # FPS
        fps_row = QHBoxLayout()
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color:#546E7A; font-size:11px;")
        self.hand_label = QLabel("● No Hand")
        self.hand_label.setStyleSheet("color:#EF5350; font-size:11px; font-weight:bold;")
        fps_row.addWidget(self.fps_label)
        fps_row.addStretch()
        fps_row.addWidget(self.hand_label)
        lay.addLayout(fps_row)
        return card

    # ── Right panel ───────────────────────────────────────────────
    def _build_right_panel(self):
        panel = QWidget()
        lay   = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(self._build_gesture_card())
        lay.addWidget(self._build_controls_card())
        lay.addWidget(self._build_log_card())
        return panel

    def _build_gesture_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        t = QLabel("🤚  Detected Gesture")
        t.setObjectName("card_title")
        lay.addWidget(t)

        self.gesture_name = QLabel("—")
        self.gesture_name.setObjectName("gesture_name")
        self.gesture_name.setAlignment(Qt.AlignCenter)

        self.gesture_sub = QLabel("Waiting for gesture…")
        self.gesture_sub.setObjectName("gesture_sub")
        self.gesture_sub.setAlignment(Qt.AlignCenter)

        self.confidence_lbl = QLabel("Confidence: --")
        self.confidence_lbl.setObjectName("confidence_lbl")
        self.confidence_lbl.setAlignment(Qt.AlignCenter)

        self.hold_bar = QProgressBar()
        self.hold_bar.setRange(0, 100)
        self.hold_bar.setValue(0)
        self.hold_bar.setFixedHeight(8)
        self.hold_bar.setTextVisible(False)

        lay.addWidget(self.gesture_name)
        lay.addWidget(self.gesture_sub)
        lay.addWidget(self.confidence_lbl)
        lay.addWidget(self.hold_bar)
        return card

    def _build_controls_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        t = QLabel("🎮  Controls")
        t.setObjectName("card_title")
        lay.addWidget(t)

        self.btn_gesture = QPushButton("✋  Gesture Mode")
        self.btn_gesture.setObjectName("btn_gesture")
        self.btn_gesture.setFixedHeight(38)
        self.btn_gesture.clicked.connect(self.gesture_mode_requested)

        self.btn_voice = QPushButton("🎙  Voice Mode")
        self.btn_voice.setObjectName("btn_voice")
        self.btn_voice.setFixedHeight(38)
        self.btn_voice.clicked.connect(self.voice_mode_requested)

        self.btn_stop = QPushButton("⏹  Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(38)
        self.btn_stop.clicked.connect(self.stop_requested)

        self.btn_help = QPushButton("❓  Help")
        self.btn_help.setObjectName("btn_help")
        self.btn_help.setFixedHeight(38)
        self.btn_help.clicked.connect(self._open_help)

        row1 = QHBoxLayout()
        row1.addWidget(self.btn_gesture)
        row1.addWidget(self.btn_voice)
        row2 = QHBoxLayout()
        row2.addWidget(self.btn_stop)
        row2.addWidget(self.btn_help)

        lay.addLayout(row1)
        lay.addLayout(row2)
        return card

    def _build_log_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        t = QLabel("📋  Action Log")
        t.setObjectName("card_title")
        lay.addWidget(t)

        self.action_log = QTextEdit()
        self.action_log.setObjectName("action_log")
        self.action_log.setReadOnly(True)
        self.action_log.setMaximumHeight(180)
        lay.addWidget(self.action_log)
        return card

    # ──────────────────────────────────────────────────────────────
    # Public Slots (called by controller)
    # ──────────────────────────────────────────────────────────────
    def update_camera_frame(self, q_img: QImage):
        pix = QPixmap.fromImage(q_img)
        self.camera_label.setPixmap(
            pix.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def update_gesture_info(self, gesture: str, subtitle: str, confidence: int):
        self.gesture_name.setText(gesture or "—")
        self.gesture_sub.setText(subtitle or "")
        self.confidence_lbl.setText(f"Confidence: {confidence}%" if confidence else "")

    def update_hand_status(self, present: bool):
        if present:
            self.hand_label.setText("● Hand Detected")
            self.hand_label.setStyleSheet("color:#43A047; font-size:11px; font-weight:bold;")
        else:
            self.hand_label.setText("● No Hand")
            self.hand_label.setStyleSheet("color:#EF5350; font-size:11px; font-weight:bold;")

    def update_fps(self, fps: float):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    def update_hold_progress(self, progress: float):
        """0.0–1.0 hold progress for Copy/Paste/Minimize/Maximize."""
        self.hold_bar.setValue(int(progress * 100))

    def log_action(self, text: str):
        import time
        ts = time.strftime("%H:%M:%S")
        self.action_log.append(f"[{ts}] {text}")
        sb = self.action_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def notify(self, message: str, icon: str = "✅"):
        n = NotificationWidget(self, message, icon)
        n.show()

    def set_mode_gesture(self):
        self.mode_badge.setText("● GESTURE MODE")
        self.mode_badge.setStyleSheet(
            "background:#0D47A1; color:#FFFFFF; border:2px solid #42A5F5;"
            "border-radius:12px; padding:4px 14px; font-size:11px; font-weight:bold;"
        )
        self._status.showMessage("  ✋  Gesture Mode Active")

    def set_mode_voice(self):
        self.mode_badge.setText("● VOICE MODE")
        self.mode_badge.setStyleSheet(
            "background:#212121; color:#FFFFFF; border:2px solid #616161;"
            "border-radius:12px; padding:4px 14px; font-size:11px; font-weight:bold;"
        )
        self._status.showMessage("  🎙  Voice Mode Active — Say a wake word")
        self.camera_label.setText(
            "🎙  Voice Mode Active\n\n"
            "Say a wake word to begin:\n"
            "\"Hey Assistant\" | \"Ok Assistant\" | \"Hello System\""
        )

    def set_mode_stopped(self):
        self.mode_badge.setText("● STOPPED")
        self.mode_badge.setStyleSheet(
            "background:#C62828; color:#FFFFFF; border:2px solid #EF5350;"
            "border-radius:12px; padding:4px 14px; font-size:11px; font-weight:bold;"
        )
        self._status.showMessage("  ⏹  Stopped")

    def _open_help(self):
        from ui.help_dialog import HelpDialog
        dlg = HelpDialog(self)
        dlg.exec_()
