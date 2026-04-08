"""Industrial-grade PyQt5 main window for G-Vox."""

import math
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
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


class VoiceWaveWidget(QWidget):
    """Animated sound-wave bars shown in voice mode recognition panel."""

    BARS = 9
    BAR_W = 6
    GAP = 5
    MAX_H = 38
    MIN_H = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        total_w = self.BARS * (self.BAR_W + self.GAP) - self.GAP
        self.setFixedSize(total_w, self.MAX_H + 4)

    def start(self):
        self._active = True
        self._timer.start(45)

    def stop(self):
        self._active = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._phase += 0.38
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        for i in range(self.BARS):
            x = i * (self.BAR_W + self.GAP)
            if self._active:
                ratio = (math.sin(self._phase + i * 0.72) + 1) / 2
                bar_h = int(self.MIN_H + ratio * (self.MAX_H - self.MIN_H))
                alpha = 180 + int(ratio * 75)
                color = QColor(46, 107, 177, alpha)
            else:
                bar_h = self.MIN_H
                color = QColor(160, 185, 215, 120)
            y = (h - bar_h) // 2
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(x, y, self.BAR_W, bar_h, 3, 3)
        p.end()

from ui.notification import NotificationWidget
from ui.styles import MAIN_STYLE
from storage.sqlite_logger import SQLiteLogger


class VoiceConfirmDialog(QDialog):
    """Non-blocking voice confirmation dialog.
    Always stays attached to the main window, never opens as a separate app.
    """

    confirmed = pyqtSignal(bool)   # True=yes, False=no

    def __init__(self, parent, action_label: str):
        super().__init__(parent)
        self._action = action_label
        self.setObjectName("voice_confirm_dialog")
        self.setFixedSize(360, 180)
        # Keep dialog attached to parent window, no separate taskbar entry
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowModality(Qt.NonModal)
        self.setWindowTitle("Confirm Action")
        # Prevent dialog close from propagating to parent window
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self._build(action_label)
        self._center_on_parent()
        self.show()

    def _build(self, label: str):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        title = QLabel(f"⚠️  Confirm {label.title()}")
        title.setObjectName("confirm_title")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        msg = QLabel(f"Say \"Yes\" to confirm or \"No\" to cancel.")
        msg.setObjectName("confirm_msg")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        lay.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_yes = QPushButton("Yes")
        btn_yes.setObjectName("confirm_yes")
        btn_yes.setFixedHeight(36)
        btn_yes.clicked.connect(lambda: self._respond(True))
        btn_no = QPushButton("No")
        btn_no.setObjectName("confirm_no")
        btn_no.setFixedHeight(36)
        btn_no.clicked.connect(lambda: self._respond(False))
        btn_row.addWidget(btn_yes)
        btn_row.addWidget(btn_no)
        lay.addLayout(btn_row)

    def _center_on_parent(self):
        if self.parent():
            pr = self.parent().rect()
            x = (pr.width() - self.width()) // 2
            y = (pr.height() - self.height()) // 2
            self.move(x, y)

    def _respond(self, approved: bool):
        self.confirmed.emit(approved)
        if approved:
            self.accept()
        else:
            self.reject()

    def voice_answer(self, text: str):
        """Called from voice worker with recognized text to auto-close dialog."""
        t = text.lower().strip()
        if t in {"yes", "confirm", "yeah", "yep"}:
            self._respond(True)
        elif t in {"no", "cancel", "nope", "stop"}:
            self._respond(False)


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

        # ── Gesture section ──────────────────────────────────────────
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

        # ── Voice section (hidden in gesture mode) ───────────────────
        self._voice_section = QWidget()
        v_lay = QVBoxLayout(self._voice_section)
        v_lay.setContentsMargins(0, 8, 0, 0)
        v_lay.setSpacing(6)

        # Wave animation
        wave_row = QHBoxLayout()
        wave_row.setAlignment(Qt.AlignCenter)
        self._voice_wave = VoiceWaveWidget()
        wave_row.addWidget(self._voice_wave)
        v_lay.addLayout(wave_row)

        # Status label
        self._voice_status_lbl = QLabel('Say "Hi Nora" to start...')
        self._voice_status_lbl.setObjectName("voice_status_lbl")
        self._voice_status_lbl.setAlignment(Qt.AlignCenter)
        v_lay.addWidget(self._voice_status_lbl)

        # Last heard label
        self._voice_heard_lbl = QLabel("")
        self._voice_heard_lbl.setObjectName("voice_heard_lbl")
        self._voice_heard_lbl.setAlignment(Qt.AlignCenter)
        self._voice_heard_lbl.setWordWrap(True)
        v_lay.addWidget(self._voice_heard_lbl)

        lay.addWidget(self._voice_section)
        self._voice_section.setVisible(False)
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

    def update_voice_status(self, state: str):
        """Update voice recognition status panel. state: idle|listening|active|heard"""
        if state == "idle":
            self._voice_wave.stop()
            self._voice_status_lbl.setText('Say "Hi Nora" to start...')
            self._voice_status_lbl.setProperty("state", "idle")
        elif state == "listening":
            self._voice_wave.start()
            self._voice_status_lbl.setText("🎙  Listening...")
            self._voice_status_lbl.setProperty("state", "listening")
        elif state == "active":
            self._voice_wave.start()
            self._voice_status_lbl.setText("⚡  Processing command...")
            self._voice_status_lbl.setProperty("state", "active")
        self._voice_status_lbl.style().unpolish(self._voice_status_lbl)
        self._voice_status_lbl.style().polish(self._voice_status_lbl)

    def update_voice_heard(self, text: str):
        """Show last heard command in recognition panel."""
        if text:
            self._voice_heard_lbl.setText(f"Heard: \"{text}\"")
        else:
            self._voice_heard_lbl.setText("")

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
        try:
            from voice_assistant.speaker import SPEAKER
            SPEAKER.say(message)
        except Exception:
            pass

    def show_voice_confirm(self, action_label: str, callback):
        """Show non-blocking voice confirmation dialog. callback(bool) called on answer."""
        # Clear any stale reference from a previously deleted dialog
        self._active_confirm_dialog = None
        dlg = VoiceConfirmDialog(self, action_label)
        dlg.confirmed.connect(callback)
        self._active_confirm_dialog = dlg

    def voice_answer_confirm(self, text: str):
        """Forward voice text to active confirmation dialog if present."""
        dlg = getattr(self, "_active_confirm_dialog", None)
        if dlg is None:
            return
        try:
            # isVisible() will raise RuntimeError if C++ object already deleted
            if dlg.isVisible():
                dlg.voice_answer(text)
        except RuntimeError:
            # Dialog C++ object deleted - clear the stale reference
            self._active_confirm_dialog = None

    def confirm_critical_action(self, action_label: str) -> bool:
        """Legacy blocking dialog - kept for non-voice use."""
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Warning)
        dlg.setWindowTitle("Confirm Critical Action")
        dlg.setText(f"Are you sure you want to {action_label}?")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)
        return dlg.exec_() == QMessageBox.Yes

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
        self._voice_section.setVisible(False)
        self._voice_wave.stop()
        self.gesture_name.setVisible(True)
        self.gesture_sub.setVisible(True)
        self.confidence_lbl.setVisible(True)
        self.hold_bar.setVisible(True)

    def set_mode_voice(self):
        self.mode_badge.setText("VOICE MODE")
        self.mode_badge.setProperty("mode", "voice")
        self.mode_badge.style().unpolish(self.mode_badge)
        self.mode_badge.style().polish(self.mode_badge)
        self.system_state.setText("WAITING FOR WAKE WORD")
        self.btn_gesture.setChecked(False)
        self.btn_voice.setChecked(True)
        self._status.showMessage(" Voice mode active. Say a wake word.")
        self._voice_section.setVisible(True)
        self.gesture_name.setVisible(False)
        self.gesture_sub.setVisible(False)
        self.confidence_lbl.setVisible(False)
        self.hold_bar.setVisible(False)
        self.update_voice_status("idle")
        self.update_voice_heard("")
        self.camera_label.setPixmap(__import__("PyQt5.QtGui", fromlist=["QPixmap"]).QPixmap())
        self.camera_label.setText(
            "\n\n🎙️  VOICE MODE ACTIVE\n\n"
            "Say a wake word to begin:\n\n"
            "  \"Hey Nora\"\n"
            "  \"OK Nora\"\n"
            "  \"Hi Nora\"\n"
            "  \"Hello Nora\"\n"
            "  \"Nora On\"\n\n"
            "Camera is off in Voice Mode."
        )

    def set_mode_voice_active(self):
        """Called when wake word is detected - update UI to show listening state."""
        self.system_state.setText("LISTENING FOR COMMAND")
        self._status.showMessage(" Wake word detected - listening for command...")
        self.update_voice_status("listening")
        self.camera_label.setText(
            "\n\n🎙️  WAKE WORD DETECTED\n\n"
            "Listening for your command...\n\n"
            "Say a command or \"Switch to Gesture\" to go back."
        )

    def bring_to_front(self):
        """Minimize all other windows then maximize G-Vox."""
        import ctypes, time, threading
        def _do():
            try:
                user32 = ctypes.windll.user32
                hwnd = int(self.winId())
                # Step 1: minimize all windows (Win+D shows desktop)
                user32.keybd_event(0x5B, 0, 0, 0)   # VK_LWIN down
                user32.keybd_event(0x44, 0, 0, 0)   # D down
                user32.keybd_event(0x44, 0, 2, 0)   # D up
                user32.keybd_event(0x5B, 0, 2, 0)   # VK_LWIN up
                time.sleep(0.3)
                # Step 2: restore and maximize G-Vox
                user32.ShowWindow(hwnd, 9)    # SW_RESTORE
                user32.ShowWindow(hwnd, 3)    # SW_MAXIMIZE
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

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
        self._help_dialog = HelpDialog(self)
        self._help_dialog.exec_()
        self._help_dialog = None

    def close_help_dialog(self):
        dlg = getattr(self, "_help_dialog", None)
        if dlg is not None:
            try:
                dlg.accept()
            except RuntimeError:
                pass
            self._help_dialog = None

    def dismiss_confirm_dialog(self):
        dlg = getattr(self, "_active_confirm_dialog", None)
        if dlg is None:
            return
        try:
            if dlg.isVisible():
                dlg.blockSignals(True)
                dlg.reject()
                dlg.blockSignals(False)
        except RuntimeError:
            pass
        self._active_confirm_dialog = None
