"""
controller/voice_worker.py
===========================
QThread wrapper around the existing VoiceAssistant logic.
Adds a modular shortcut-command layer before forwarding to original voice_assistant/main.py.
Original voice_assistant/main.py is NOT modified.
"""

import sys
import signal
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

# Prevent signal errors when running in Qt thread
_signal_module = __import__("signal")
_REAL_SIGNAL_FN = _signal_module.signal

# Offline Audio Response
from voice_assistant.speaker import SPEAKER
from extensions.voice_shortcut_commands import check_and_execute as shortcut_check


ADDITIONAL_VOICE_PHRASES = [
    "screenshot",
    "open file",
    "close file",
    "close",
    "minimize",
    "maximize",
    "zoom in",
    "zoom out",
    "next image",
    "previous image",
    "scroll up",
    "scroll down",
    "next page",
    "previous page",
    "up",
    "down",
    "left",
    "right",
    "next",
    "previous",
]


class VoiceWorker(QThread):
    """
    Runs VoiceAssistant in a background thread.
    Intercepts shortcut commands and mode switch before forwarding to original logic.
    """

    action_logged = pyqtSignal(str)
    switch_to_gesture = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._assistant = None

    def stop(self):
        self._running = False
        if self._assistant:
            try:
                self._assistant.shutdown()
            except Exception:
                pass
        self.wait(3000)

    def run(self):
        """Start the voice assistant in this thread."""
        self._running = True

        # Patch signal() to be a no-op so VoiceAssistant doesn't break in a Qt thread
        def _noop_signal(sig, handler):
            pass

        _signal_module.signal = _noop_signal

        try:
            # Add voice_assistant dir to path
            va_dir = Path(__file__).parent.parent / "voice_assistant"
            if str(va_dir) not in sys.path:
                sys.path.insert(0, str(va_dir))

            from voice_assistant.main import VoiceAssistant

            self._assistant = VoiceAssistant()
            # Ensure VOSK model path resolves correctly in UI mode.
            model_path = self._assistant.config.get("recognition", {}).get("model_path", "")
            if model_path and not Path(model_path).is_absolute():
                abs_model_path = (va_dir / model_path).resolve()
                self._assistant.config["recognition"]["model_path"] = str(abs_model_path)
                self._assistant.voice_listener.config["recognition"]["model_path"] = str(abs_model_path)

            self.action_logged.emit("Voice Mode started - say a wake word.")

            # Extend grammar at runtime with additional shortcut phrases.
            original_get_grammar = self._assistant._get_compiled_grammar

            def patched_get_grammar():
                base = original_get_grammar()
                merged = set(base)
                for phrase in ADDITIONAL_VOICE_PHRASES:
                    p = phrase.lower().strip()
                    if p:
                        merged.add(p)
                        for word in p.split():
                            merged.add(word)
                return sorted(merged)

            self._assistant._get_compiled_grammar = patched_get_grammar

            # Patch _process_command to intercept additional shortcuts + switch signal
            original_process = self._assistant._process_command

            def patched_process(command_text: str):
                text = command_text.lower().strip()

                # 1. Additional shortcut command layer
                handled, msg = shortcut_check(text)
                if handled:
                    self.action_logged.emit(f"VOICE: {msg}")
                    return

                # 2. Mode switch -> emit Qt signal instead of sys.exit
                if ("switch" in text and "gesture" in text) or ("switch" in text and "mode" in text):
                    self.action_logged.emit("VOICE: Switching to Gesture Mode...")
                    SPEAKER.say("Switching to Gesture Mode")
                    self.switch_to_gesture.emit()
                    return

                # 3. Everything else -> original handler
                original_process(command_text)

            self._assistant._process_command = patched_process

            # Start listening
            self._assistant.start()
            if not getattr(self._assistant, "is_running", False):
                msg = "Voice listener failed to start. Check microphone device and audio settings."
                self.error_occurred.emit(msg)
                self.action_logged.emit(f"Voice Error: {msg}")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.action_logged.emit(f"Voice Error: {e}")
        finally:
            _signal_module.signal = _REAL_SIGNAL_FN
            self._running = False
