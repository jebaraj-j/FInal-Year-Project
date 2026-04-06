"""Industrial-grade PyQt5 main window for G-Vox."""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.notification import NotificationWidget
from ui.styles import MAIN_STYLE
from storage.sqlite_logger import SQLiteLogger


class MainWindow(QMainWindow):
    """Main application window."""

    gesture_mode_requested = pyqtSignal()
    voice_mode_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Vox Control Center")
        self.setMinimumSize(1360, 840)
        self.setStyleSheet(MAIN_STYLE)
        self._animations = []
        self._tray_icon = None
        self._sqlite_logger = SQLiteLogger()
        self._build_ui()
        self._init_system_notifications()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body_wrap = QWidget()
        body_wrap.setObjectName("body_wrap")
        body = QHBoxLayout(body_wrap)
        body.setContentsMargins(16, 14, 16, 14)
        body.setSpacing(14)

        self.left_workspace = self._build_left_workspace()
        self.right_panel = self._build_right_panel()
        body.addWidget(self.left_workspace, 22)
        body.addWidget(self.right_panel, 10)
        root.addWidget(body_wrap)

        self._status = QStatusBar()
        self._status.showMessage(" Ready. Gesture mode starts automatically.")
        self.setStatusBar(self._status)

        QTimer.singleShot(120, self._run_startup_animation)

    def _build_header(self):
        hdr = QWidget()
        hdr.setObjectName("header")
        hdr.setFixedHeight(76)

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title = QLabel("G-Vox")
        title.setObjectName("app_title")
        subtitle = QLabel("Industrial Gesture and Voice Operations Console")
        subtitle.setObjectName("app_subtitle")
        self.system_state = QLabel("SYSTEM READY")
        self.system_state.setObjectName("system_state")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        lay.addLayout(title_col)
        lay.addStretch()
        lay.addWidget(self.system_state, 0, Qt.AlignVCenter)

        self.mode_badge = QLabel("GESTURE MODE")
        self.mode_badge.setObjectName("mode_badge")
        self.mode_badge.setProperty("mode", "gesture")
        lay.addWidget(self.mode_badge, 0, Qt.AlignVCenter)

        top_help = QPushButton("Help")
        top_help.setObjectName("btn_help_header")
        top_help.setFixedSize(96, 36)
        top_help.clicked.connect(self._open_help)
        lay.addWidget(top_help, 0, Qt.AlignVCenter)
        return hdr

    def _build_left_workspace(self):
        panel = QWidget()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(self._build_camera_panel(), 20)
        lay.addWidget(self._build_controls_panel(), 3)
        return panel

    def _build_camera_panel(self):
        card = QFrame()
        card.setObjectName("camera_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 10)
        lay.setSpacing(8)

        section = QLabel("LIVE CAMERA FEED")
        section.setObjectName("section_bar")
        section.setAlignment(Qt.AlignCenter)
        lay.addWidget(section)

        self.camera_label = QLabel("Camera initializing...")
        self.camera_label.setObjectName("camera_label")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(980, 620)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.camera_label, 1)

        meta = QHBoxLayout()
        meta.setSpacing(14)
        room_lbl = QLabel("Workspace")
        room_lbl.setObjectName("meta_label")
        room_val = QLabel("Primary Control Bay")
        room_val.setObjectName("meta_value")
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setObjectName("meta_value")
        self.hand_label = QLabel("No Hand")
        self.hand_label.setObjectName("status_bad")

        meta.addWidget(room_lbl)
        meta.addWidget(room_val)
        meta.addStretch()
        meta.addWidget(self.fps_label)
        meta.addWidget(self.hand_label)
        lay.addLayout(meta)
        return card

    def _build_controls_panel(self):
        card = QFrame()
        card.setObjectName("controls_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self.btn_gesture = QPushButton("GESTURE CONTROL")
        self.btn_gesture.setObjectName("tile_gesture")
        self.btn_gesture.setCheckable(True)
        self.btn_gesture.setChecked(True)
        self.btn_gesture.setMinimumHeight(96)
        self.btn_gesture.clicked.connect(self.gesture_mode_requested)

        self.btn_voice = QPushButton("VOICE CONTROL")
        self.btn_voice.setObjectName("tile_voice")
        self.btn_voice.setCheckable(True)
        self.btn_voice.setMinimumHeight(96)
        self.btn_voice.clicked.connect(self.voice_mode_requested)

        mode_row.addWidget(self.btn_gesture)
        mode_row.addWidget(self.btn_voice)

        op_row = QHBoxLayout()
        op_row.setSpacing(10)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self.stop_requested)

        self.btn_help = QPushButton("User Guide")
        self.btn_help.setObjectName("btn_help")
        self.btn_help.setMinimumHeight(40)
        self.btn_help.clicked.connect(self._open_help)

        op_row.addWidget(self.btn_stop)
        op_row.addWidget(self.btn_help)

        lay.addLayout(mode_row)
        lay.addLayout(op_row)
        return card

    def _build_recognition_panel(self):
        card = QFrame()
        card.setObjectName("recognition_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        title = QLabel("RECOGNITION STATUS")
        title.setObjectName("card_title")
        lay.addWidget(title)

        self.gesture_name = QLabel("--")
        self.gesture_name.setObjectName("gesture_name")
        self.gesture_name.setAlignment(Qt.AlignCenter)

        self.gesture_sub = QLabel("Waiting for gesture input...")
        self.gesture_sub.setObjectName("gesture_sub")
        self.gesture_sub.setAlignment(Qt.AlignCenter)

        self.confidence_lbl = QLabel("Confidence: --")
        self.confidence_lbl.setObjectName("confidence_lbl")
        self.confidence_lbl.setAlignment(Qt.AlignCenter)

        self.hold_bar = QProgressBar()
        self.hold_bar.setRange(0, 100)
        self.hold_bar.setValue(0)
        self.hold_bar.setFixedHeight(10)
        self.hold_bar.setTextVisible(False)

        lay.addWidget(self.gesture_name)
        lay.addWidget(self.gesture_sub)
        lay.addWidget(self.confidence_lbl)
        lay.addWidget(self.hold_bar)
        return card

    def _build_right_panel(self):
        panel = QWidget()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(self._build_recognition_panel(), 4)
        lay.addWidget(self._build_log_card(), 8)
        return panel

    def _build_log_card(self):
        card = QFrame()
        card.setObjectName("log_card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(8)

        title = QLabel("COMMANDS LOG")
        title.setObjectName("section_bar")
        title.setAlignment(Qt.AlignCenter)
        row.addWidget(title, 1)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btn_clear")
        clear_btn.setFixedHeight(34)
        clear_btn.clicked.connect(lambda: self.action_log.clear())
        row.addWidget(clear_btn)
        lay.addLayout(row)

        self.action_log = QTextEdit()
        self.action_log.setObjectName("action_log")
        self.action_log.setReadOnly(True)
        self.action_log.setPlaceholderText("System command timeline will appear here...")
        lay.addWidget(self.action_log, 1)
        return card

    def _run_startup_animation(self):
        self._fade_in_widget(self.left_workspace, duration=420, delay_ms=0)
        self._fade_in_widget(self.right_panel, duration=520, delay_ms=120)

    def _fade_in_widget(self, widget, duration: int, delay_ms: int):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._animations.append(anim)

        if delay_ms <= 0:
            anim.start()
            return

        QTimer.singleShot(delay_ms, anim.start)

    def _init_system_notifications(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        if not icon.isNull():
            tray.setIcon(icon)
        else:
            tray.setIcon(self.windowIcon())
        tray.setToolTip("G-Vox")
        tray.show()
        self._tray_icon = tray

    def update_camera_frame(self, q_img: QImage):
        pix = QPixmap.fromImage(q_img)
        self.camera_label.setPixmap(
            pix.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def update_gesture_info(self, gesture: str, subtitle: str, confidence: int):
        self.gesture_name.setText(gesture or "--")
        self.gesture_sub.setText(subtitle or "")
        self.confidence_lbl.setText(f"Confidence: {confidence}%" if confidence else "Confidence: --")

    def update_hand_status(self, present: bool):
        if present:
            self.hand_label.setText("Hand Detected")
            self.hand_label.setObjectName("status_ok")
        else:
            self.hand_label.setText("No Hand")
            self.hand_label.setObjectName("status_bad")
        self.hand_label.style().unpolish(self.hand_label)
        self.hand_label.style().polish(self.hand_label)

    def update_fps(self, fps: float):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    def update_hold_progress(self, progress: float):
        self.hold_bar.setValue(int(progress * 100))

    def log_action(self, text: str):
        import html
        import time

        ts = time.strftime("%H:%M:%S")
        safe_text = html.escape(text)
        line = (
            f"<div style='margin:2px 0; padding:6px 8px; border-radius:8px; "
            f"background:#F3F6FB; color:#17243C;'>"
            f"<span style='color:#3E5E8D; font-weight:700;'>{ts}</span> "
            f"<span style='color:#1C2C47;'>{safe_text}</span></div>"
        )
        self.action_log.append(line)
        sb = self.action_log.verticalScrollBar()
        sb.setValue(sb.maximum())
        try:
            self._sqlite_logger.log_event(source="ui", message=text, level="INFO")
        except Exception:
            # Never let logging persistence affect core app behavior.
            pass

    def notify(self, message: str, icon: str = "OK"):
        if self._tray_icon:
            self._tray_icon.showMessage("G-Vox", message, QSystemTrayIcon.Information, 2500)
        n = NotificationWidget(self, message, icon)
        n.show()

    def confirm_exit(self, context: str = "Exit requested.") -> bool:
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Question)
        dlg.setWindowTitle("Exit G-Vox")
        dlg.setText("Do you want to close G-Vox?")
        dlg.setInformativeText(context)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)
        return dlg.exec_() == QMessageBox.Yes

    def set_mode_gesture(self):
        self.mode_badge.setText("GESTURE MODE")
        self.mode_badge.setProperty("mode", "gesture")
        self.mode_badge.style().unpolish(self.mode_badge)
        self.mode_badge.style().polish(self.mode_badge)
        self.system_state.setText("TRACKING LIVE HAND INPUT")
        self.btn_gesture.setChecked(True)
        self.btn_voice.setChecked(False)
        self._status.showMessage(" Gesture mode active.")

    def set_mode_voice(self):
        self.mode_badge.setText("VOICE MODE")
        self.mode_badge.setProperty("mode", "voice")
        self.mode_badge.style().unpolish(self.mode_badge)
        self.mode_badge.style().polish(self.mode_badge)
        self.system_state.setText("LISTENING FOR WAKE WORD")
        self.btn_gesture.setChecked(False)
        self.btn_voice.setChecked(True)
        self._status.showMessage(" Voice mode active. Say a wake word.")
        self.camera_label.setText(
            "Voice mode active.\n\nSay one wake phrase:\n"
            "hey nora | ok nora | hi nora | hello nora | nora on"
        )

    def set_mode_stopped(self):
        self.mode_badge.setText("STOPPED")
        self.mode_badge.setProperty("mode", "stopped")
        self.mode_badge.style().unpolish(self.mode_badge)
        self.mode_badge.style().polish(self.mode_badge)
        self.system_state.setText("SYSTEM IDLE")
        self.btn_gesture.setChecked(False)
        self.btn_voice.setChecked(False)
        self._status.showMessage(" System stopped.")

    def _open_help(self):
        from ui.help_dialog import HelpDialog

        dlg = HelpDialog(self)
        dlg.exec_()
