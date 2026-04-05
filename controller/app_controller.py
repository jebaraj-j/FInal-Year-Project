"""
controller/app_controller.py
==============================
Connects MainWindow â†” GestureWorker â†” VoiceWorker.
Uses voice_assistant/speaker.py for offline audio confirmations.
"""

from PyQt5.QtCore import QObject, QTimer

from ui.main_window           import MainWindow
from controller.gesture_worker import GestureWorker
from controller.voice_worker   import VoiceWorker
from voice_assistant.speaker   import SPEAKER


class AppController(QObject):
    def __init__(self, window: MainWindow):
        super().__init__()
        self.window          = window
        self._gesture_worker = None
        self._voice_worker   = None
        self._current_mode   = "stopped"

        # Connect UI buttons
        window.gesture_mode_requested.connect(self.start_gesture_mode)
        window.voice_mode_requested.connect(self.start_voice_mode)
        window.stop_requested.connect(self.stop_all)

        # Auto-start gesture mode after window loads
        QTimer.singleShot(600, self.start_gesture_mode)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def start_gesture_mode(self):
        if self._current_mode == "gesture":
            return
        self._stop_workers()
        self._current_mode   = "gesture"
        self._gesture_worker = GestureWorker()
        self._connect_gesture_signals()
        self._gesture_worker.start()
        self.window.set_mode_gesture()
        self.window.log_action("Gesture Mode started.")
        SPEAKER.say("Gesture Mode activated")

    def start_voice_mode(self):
        if self._current_mode == "voice":
            return
        self._stop_workers()
        self._current_mode = "voice"
        self._voice_worker = VoiceWorker()
        self._connect_voice_signals()
        self._voice_worker.start()
        self.window.set_mode_voice()
        self.window.log_action("Voice Mode started â€” say a wake word.")
        self.window.notify("Voice Mode", "ðŸŽ™")
        SPEAKER.say("Voice Mode activated. Say hey nora to begin.")

    def stop_all(self):
        self._stop_workers()
        self._current_mode = "stopped"
        self.window.set_mode_stopped()
        self.window.update_gesture_info("Stopped", "", 0)
        self.window.update_hand_status(False)
        self.window.log_action("All modes stopped.")
        self.window.notify("System Stopped", "â¹")
        SPEAKER.say("System stopped")

    # â”€â”€ Signal wiring â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _connect_gesture_signals(self):
        w = self._gesture_worker
        w.frame_ready.connect(self.window.update_camera_frame)
        w.gesture_detected.connect(self._on_gesture_detected)
        w.hand_present.connect(self.window.update_hand_status)
        w.fps_updated.connect(self.window.update_fps)
        w.action_logged.connect(self.window.log_action)
        w.gesture_triggered.connect(self._on_gesture_triggered)
        w.switch_to_voice.connect(self._on_switch_to_voice)

    def _connect_voice_signals(self):
        w = self._voice_worker
        w.action_logged.connect(self.window.log_action)
        w.switch_to_gesture.connect(self._on_switch_to_gesture)
        w.error_occurred.connect(lambda e: self.window.log_action(f"âš  Voice error: {e}"))

    # â”€â”€ Handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _on_gesture_detected(self, gesture: str, subtitle: str, confidence: int):
        self.window.update_gesture_info(gesture, subtitle, confidence)

    def _on_gesture_triggered(self, label: str, icon: str):
        """Show notification + speak action."""
        self.window.notify(label, icon)
        SPEAKER.say(label)

    def _on_switch_to_voice(self):
        self.window.log_action("ðŸ”„ Switching to Voice Mode via gesture.")
        self.start_voice_mode()

    def _on_switch_to_gesture(self):
        self.window.log_action("ðŸ”„ Switching to Gesture Mode via voice.")
        self.start_gesture_mode()

    # â”€â”€ Cleanup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _stop_workers(self):
        if self._gesture_worker and self._gesture_worker.isRunning():
            self._gesture_worker.stop()
            self._gesture_worker = None
        if self._voice_worker and self._voice_worker.isRunning():
            self._voice_worker.stop()
            self._voice_worker = None

